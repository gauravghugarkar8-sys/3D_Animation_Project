"""
Tools available to the MindMesh agent.

Each tool is a plain Python function that takes simple arguments and
returns a JSON-serialisable dict. The agent (core_agent.py) decides which
tool to call based on the detected intent, then formats the result into a
spoken/typed reply plus an optional "visual" payload that the frontend
renders in the centre knowledge panel.
"""

import datetime
import random
import re

import psutil
import requests
from django.conf import settings
from django.utils import timezone


# --------------------------------------------------------------------------
# System stats — mirrors the CPU / RAM / Disk widget in the reference UI
# --------------------------------------------------------------------------

def get_system_stats():
    """Live host system stats using psutil (real data, not simulated)."""
    cpu_percent = psutil.cpu_percent(interval=0.2)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return {
        "cpu_percent": cpu_percent,
        "ram_percent": mem.percent,
        "ram_used_gb": round(mem.used / (1024 ** 3), 2),
        "ram_total_gb": round(mem.total / (1024 ** 3), 2),
        "disk_used_gb": round(disk.used / (1024 ** 3), 1),
        "disk_total_gb": round(disk.total / (1024 ** 3), 1),
        "disk_percent": disk.percent,
        "boot_time": datetime.datetime.fromtimestamp(psutil.boot_time()).isoformat(),
    }


# --------------------------------------------------------------------------
# Weather — real data via OpenWeatherMap if a key is configured, otherwise
# a believable simulated reading so the dashboard works out of the box.
# --------------------------------------------------------------------------

def get_weather(city=None):
    city = city or settings.DEFAULT_CITY
    api_key = settings.OPENWEATHER_API_KEY

    if api_key:
        try:
            resp = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": city, "appid": api_key, "units": "metric"},
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "city": data.get("name", city),
                "country": data.get("sys", {}).get("country", ""),
                "temp_c": round(data["main"]["temp"], 1),
                "feels_like_c": round(data["main"]["feels_like"], 1),
                "humidity": data["main"]["humidity"],
                "wind_ms": data["wind"]["speed"],
                "description": data["weather"][0]["description"],
                "simulated": False,
            }
        except (requests.RequestException, KeyError, IndexError):
            pass  # fall through to simulated data below

    return _simulated_weather(city)


def _simulated_weather(city):
    """Deterministic-ish placeholder weather so the UI is never empty."""
    rng = random.Random(datetime.date.today().toordinal() + hash(city) % 1000)
    conditions = ["clear sky", "few clouds", "scattered clouds", "overcast clouds", "light rain"]
    temp = round(rng.uniform(18, 34), 1)
    return {
        "city": city.split(",")[0],
        "country": city.split(",")[1] if "," in city else "",
        "temp_c": temp,
        "feels_like_c": round(temp + rng.uniform(-1, 2), 1),
        "humidity": rng.randint(40, 95),
        "wind_ms": round(rng.uniform(1, 7), 1),
        "description": rng.choice(conditions),
        "simulated": True,
    }


# --------------------------------------------------------------------------
# Knowledge lookups — drives the centre "knowledge graph" visual panel,
# analogous to the anatomy-model viewer in the reference UI. Uses the
# public Wikipedia REST summary endpoint (no key required).
# --------------------------------------------------------------------------

def wiki_lookup(topic):
    topic = topic.strip().strip("?.!").title()

    result = _wiki_summary(topic)
    if result:
        return result

    # Exact-title lookup failed (404) or landed on a disambiguation page —
    # try Wikipedia's title-suggestion (opensearch) first...
    suggestion = _wiki_search_suggestion(topic)
    if suggestion and suggestion.lower() != topic.lower():
        result = _wiki_summary(suggestion)
        if result:
            return result

    # ...and if that still didn't land, fall back to a full-text search.
    # This catches phrasing that doesn't match any article *title* but
    # whose *content* does — e.g. "Prime Minister of America" (not a
    # real title/role) can still surface "President of the United
    # States" this way, since that article's text covers the concept.
    suggestion = _wiki_fulltext_suggestion(topic)
    if suggestion and suggestion.lower() != topic.lower():
        return _wiki_summary(suggestion)

    return None


def _wiki_summary(title):
    try:
        resp = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(title)}",
            timeout=6,
            headers={"User-Agent": "MindMesh-Assistant/1.0"},
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        if data.get("type") == "disambiguation":
            return None
        return {
            "title": data.get("title", title),
            "summary": data.get("extract", "No summary available."),
            "image": (data.get("thumbnail") or {}).get("source"),
            "url": (data.get("content_urls") or {}).get("desktop", {}).get("page"),
        }
    except requests.RequestException:
        return None


def _wiki_search_suggestion(topic):
    """Best-guess real article title for a topic that didn't resolve directly."""
    try:
        resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "opensearch",
                "search": topic,
                "limit": 1,
                "namespace": 0,
                "format": "json",
            },
            timeout=6,
            headers={"User-Agent": "MindMesh-Assistant/1.0"},
        )
        resp.raise_for_status()
        data = resp.json()
        titles = data[1] if len(data) > 1 else []
        return titles[0] if titles else None
    except (requests.RequestException, IndexError, ValueError):
        return None


def _wiki_fulltext_suggestion(topic):
    """
    Full-text (content, not just title) search — catches concepts phrased
    in a way that matches no article *title* but is clearly discussed in
    some article's *body text*, e.g. a made-up role name for a real
    position ("Prime Minister of America" -> "President of the United
    States").
    """
    try:
        resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": topic,
                "srlimit": 1,
                "format": "json",
            },
            timeout=6,
            headers={"User-Agent": "MindMesh-Assistant/1.0"},
        )
        resp.raise_for_status()
        data = resp.json()
        hits = data.get("query", {}).get("search", [])
        return hits[0]["title"] if hits else None
    except (requests.RequestException, IndexError, KeyError, ValueError):
        return None


# --------------------------------------------------------------------------
# Live 3D model search — Sketchfab's public search API (no key required,
# confirmed via api.sketchfab.com/v3/search). This is what lets the agent
# find a real, embeddable 3D model for *any* topic, not just the small
# hand-curated set in models_3d.py. Used as a fallback when the curated
# table (models_3d.MODEL_3D_LIBRARY) has no entry for the topic.
# --------------------------------------------------------------------------

def search_3d_model(topic):
    """
    Searches Sketchfab for a free, downloadable/embeddable model matching
    `topic`. Returns {"title", "embed_url"} for the best result, or None
    if nothing suitable turns up.

    Sketchfab's relevance ranking can surface loosely-tagged results for
    abstract, non-physical topics (e.g. "deep learning" -> some unrelated
    "wall" model that merely shares a tag), so results are only accepted
    if the model's own name meaningfully overlaps with the search words —
    otherwise we'd rather show nothing than something misleading.
    """
    topic_words = {w for w in re.findall(r"[a-z0-9]+", topic.lower()) if len(w) > 2}
    if not topic_words:
        return None

    try:
        resp = requests.get(
            "https://api.sketchfab.com/v3/search",
            params={
                "type": "models",
                "q": topic,
                "downloadable": "true",
                "sort_by": "-relevance",
                "count": 8,
            },
            timeout=8,
            headers={"User-Agent": "MindMesh-Assistant/1.0"},
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        for item in results:
            uid = item.get("uid")
            name = item.get("name") or ""
            if not uid or not name:
                continue
            name_words = {w for w in re.findall(r"[a-z0-9]+", name.lower()) if len(w) > 2}
            if not (topic_words & name_words):
                continue  # no real word overlap — likely an irrelevant match, skip it
            return {
                "title": name,
                "embed_url": f"https://sketchfab.com/models/{uid}/embed?autostart=1&ui_theme=dark",
            }
    except (requests.RequestException, ValueError, KeyError):
        pass
    return None


# --------------------------------------------------------------------------
# Time / date
# --------------------------------------------------------------------------

def get_current_datetime():
    now = timezone.localtime()
    return {
        "iso": now.isoformat(),
        "date_label": now.strftime("%B %d, %Y"),
        "time_label": now.strftime("%I:%M:%S %p"),
    }
