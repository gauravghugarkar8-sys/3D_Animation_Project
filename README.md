# MindMesh — Django Edition

A JARVIS-style personal AI assistant dashboard, rebuilt on **Django**: a
live conversation panel, an animated central "knowledge graph" visual that
swaps in a real 3D model / image when you ask about a topic, real-time
system stats (CPU / RAM / Disk), a weather widget, and voice input/output —
all driven by a real **LLM tool-calling agent**, not hand-written rules.

This is a from-scratch Django rebuild of the "MindMesh" UI shown in the
reference recording (React + Python prototype), not a copy of its source.

## What the agent does — and why there's no rule-based routing

`assistant/agent/core_agent.py` is the agent. **There is no regex/keyword
intent classifier here on purpose.** Every message goes straight to a real
LLM (via LangChain's `ChatOpenAI`), which decides for itself — by actually
understanding what you said — whether to just answer directly, or to call
one of four tools:

| Tool                  | The model calls this when...                          |
|------------------------|---------------------------------------------------------|
| `get_weather`          | you're specifically asking about weather/temperature   |
| `get_system_stats`     | you're specifically asking about CPU/RAM/disk           |
| `get_current_datetime` | you're specifically asking what time/date it is         |
| `show_3d_visual`       | the current subject is something worth showing on screen |

That last one is the key piece: instead of me regex-capturing a "topic"
from your sentence (which is exactly what caused things like "deep
learning" pulling up an unrelated wall texture in earlier iterations),
**the model itself picks the precise search phrase** for whatever the
conversation is *currently* about and passes it to `show_3d_visual`,
which then finds a real 3D model (curated list → live Sketchfab search,
relevance-filtered) or Wikipedia image for exactly that.

Because the whole conversation history is passed to the model on every
turn, follow-ups ("what about the brain?", "tell me more") are resolved
by the model's own understanding of context — not a special-cased
regex path.

This means: **you need an LLM configured for the app to do anything
beyond show its dashboard shell.** There's no offline rule-based
fallback for answering — "answer literally anything, correctly" is an
LLM capability, and faking it with keyword rules is exactly the
wrong-answers-and-wrong-animations problem this design avoids. See
`.env.example` / Setup below.

## Project layout

```
mindmesh_django/
├── manage.py
├── requirements.txt
├── .env.example
├── mindmesh_project/        # Django project (settings, urls, wsgi/asgi)
└── assistant/                # the one app
    ├── models.py              # ConversationSession, Message
    ├── views.py                # dashboard + JSON API endpoints
    ├── urls.py
    ├── admin.py
    ├── agent/
    │   ├── core_agent.py       # the agent: LLM + tool-calling loop
    │   ├── langchain_tools.py  # tool definitions the LLM chooses from
    │   ├── models_3d.py        # curated topic -> Sketchfab 3D model
    │   └── tools.py            # underlying weather/stats/wiki/3D-search functions
    ├── templates/assistant/dashboard.html
    └── static/assistant/
        ├── css/style.css       # dark/cyan sci-fi dashboard theme
        └── js/
            ├── app.js           # wiring: chat, stats/weather polling, mic
            ├── knowledge_graph.js  # idle-state canvas radar animation
            └── speech.js          # Web Speech API (STT + TTS) wrapper
```

## API endpoints

| Endpoint            | Method | Purpose                                   |
|----------------------|--------|--------------------------------------------|
| `/`                  | GET    | Dashboard page                            |
| `/api/chat/`         | POST   | `{"message": "...", }` → agent reply + visual |
| `/api/stats/`        | GET    | Live CPU/RAM/disk stats                   |
| `/api/weather/`      | GET    | Weather for `?city=` (defaults to config) |
| `/api/clock/`        | GET    | Server date/time                          |
| `/api/history/`      | GET    | Full conversation history for the session |

## Setup

```bash
cd mindmesh_django
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows

pip install -r requirements.txt   # now includes langchain-openai / langchain-core

cp .env.example .env
```

Now edit `.env` and set your LLM credentials — **this step is required**,
not optional, for the assistant to answer anything:

```env
LLM_API_KEY=sk-...your real key...
LLM_MODEL=gpt-4o-mini          # any model your key has access to
LLM_BASE_URL=https://api.openai.com/v1   # or a local server's URL (Ollama, LM Studio, ...)
```

**Never paste an API key directly into a `.py` file.** `.env` is listed
in `.gitignore` specifically so a key never ends up committed or shared
by accident. If a key has ever been pasted somewhere public (a chat, a
forum, a committed file), treat it as compromised and regenerate it from
your provider's dashboard immediately.

Then:

```bash
python manage.py migrate
python manage.py createsuperuser  # optional, for /admin/
python manage.py runserver
```

Open **http://127.0.0.1:8000/**. If `LLM_API_KEY` isn't set, the page
shows a red banner telling you so instead of silently failing. Once
configured, try anything:

- "What's the weather?" / "Check CPU usage" / "What time is it?"
- "Tell me about the heart" / "Show me a 3D model of a guitar"
- "Who is the Prime Minister of America?" (correctly explains the US
  has a President, not a PM — a real LLM reasons this out; a keyword
  matcher can't)
- Literally anything else — opinions, math, comparisons, follow-ups

## Notes on parity with the reference recording

- **Wake word**: true always-on wake-word detection needs a native
  library (e.g. Porcupine) and a downloaded model — out of scope for a
  browser-based demo. The mic button gives you the same push-to-talk
  experience; `WAKE_WORD` in settings is wired through to the UI copy.
- **3D visuals**: the centre panel embeds a **real, interactive
  Sketchfab 3D model** (drag to rotate, scroll to zoom) for whatever the
  model decides is worth showing — not a fixed list and not a regex
  capture. It checks a small curated table
  (`assistant/agent/models_3d.py`) first for common topics (heart,
  brain, skull, skeleton, stomach, lungs, DNA, Earth, solar system) that
  have been hand-picked for quality, then falls back to a **live
  Sketchfab search** (`tools.search_3d_model`, relevance-filtered so it
  won't attach an unrelated result) for anything else, then to a
  Wikipedia image, so the panel is never empty when there's genuinely
  something to show.
- **System stats / weather**: real, live data (`psutil`, OpenWeatherMap),
  not mocked — same as the original.

## Extending the agent

Add a new tool by:

1. Writing a function in `agent/tools.py` (the actual logic).
2. Wrapping it with LangChain's `@tool` decorator in
   `agent/langchain_tools.py`, with a clear docstring — **the docstring
   is how the model decides when to call it**, so be specific about
   when it applies and what arguments to pass.
3. Adding it to `ALL_TOOLS` in that same file.

No other wiring needed — `core_agent.py`'s tool-calling loop, the view,
and the frontend all handle any tool call generically already.
