"""
Tools exposed to the LLM via LangChain's native tool-calling.

This is the key architectural difference from the old regex-based
routing: WHICH tool gets called (if any), and with WHAT arguments, is
decided entirely by the model itself — by actually understanding the
user's message — not by hand-written keyword/regex conditions. This
file only defines what each tool DOES; the model decides WHEN to call
it and what to pass in.
"""

import json

try:
    from langchain_core.tools import tool
    _LANGCHAIN_CORE_AVAILABLE = True
except ImportError:
    # langchain-core isn't installed yet (see requirements.txt). Provide a
    # minimal stand-in with the same .name/.invoke() shape as a real
    # LangChain tool, so this module — and core_agent.py's ALL_TOOLS
    # handling — still import and construct cleanly. core_agent.py checks
    # _LANGCHAIN_AVAILABLE before ever actually calling these, so the
    # server starts and shows a clear "please install/configure" message
    # instead of crashing at import time.
    _LANGCHAIN_CORE_AVAILABLE = False

    class _FallbackTool:
        def __init__(self, fn):
            self._fn = fn
            self.name = fn.__name__

        def invoke(self, args):
            return self._fn(**args)

    def tool(fn):
        return _FallbackTool(fn)

from . import tools as _tools
from .models_3d import find_3d_model


@tool
def get_weather(city: str = "") -> str:
    """Get the current live weather (temperature, conditions, humidity,
    wind) for a city. Only call this when the user is specifically
    asking about weather, temperature, or a forecast. Leave city empty
    to use the dashboard's configured default city."""
    return json.dumps(_tools.get_weather(city=city or None))


@tool
def get_system_stats() -> str:
    """Get live CPU, RAM, and disk usage for this machine. Only call
    this when the user is specifically asking about system performance,
    CPU, RAM, memory, or disk usage."""
    return json.dumps(_tools.get_system_stats())


@tool
def get_current_datetime() -> str:
    """Get the current date and time. Only call this when the user is
    specifically asking what time or date it is right now."""
    return json.dumps(_tools.get_current_datetime())


@tool
def show_3d_visual(topic: str) -> str:
    """
    Find and display a real, interactive 3D model (or, failing that, an
    image) on screen for a subject. Call this whenever the current
    message is about a real-world object, place, organism, structure,
    or anything else that would be usefully SEEN — not only when the
    user explicitly says "show me". Pass a short, precise search phrase
    for exactly what the conversation is currently about right now (for
    example "human heart", "Eiffel Tower", "DNA double helix") — not the
    user's whole sentence, and not a leftover topic from earlier in the
    conversation if the subject has since changed. Do not call this for
    abstract yes/no questions, math, opinions, or pure conversation with
    nothing concrete to visualize.
    """
    model3d = find_3d_model(topic) or _tools.search_3d_model(topic)
    if model3d:
        return json.dumps({
            "found": True,
            "kind": "model3d",
            "title": model3d["title"],
            "embed_url": model3d["embed_url"],
        })

    wiki = _tools.wiki_lookup(topic)
    if wiki and wiki.get("image"):
        return json.dumps({
            "found": True,
            "kind": "image",
            "title": wiki["title"],
            "image": wiki["image"],
            "url": wiki.get("url"),
        })

    return json.dumps({"found": False})


ALL_TOOLS = [get_weather, get_system_stats, get_current_datetime, show_3d_visual]
