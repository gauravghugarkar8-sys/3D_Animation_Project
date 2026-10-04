"""
The MindMesh agent — a LangChain tool-calling agent.

There is no hand-written keyword/regex routing layer here on purpose:
the model itself decides which tool (if any) to call and with what
arguments, based on actually understanding the message. That means it
can answer literally anything an LLM can answer — general knowledge,
opinions, follow-ups, comparisons, whatever — exactly like a normal
chatbot, while still reaching for live tools (weather, system stats, a
matching 3D visual) when the conversation calls for it, and picking the
right search term for the visual itself rather than a regex capture.

This REQUIRES an LLM to be configured (LLM_API_KEY in .env). There is
no offline/rule-based fallback: "answer anything, correctly" is
fundamentally an LLM capability, and pretending a keyword-matcher can do
that leads to exactly the wrong/missing answers this design avoids.
"""

import json
import logging

from django.conf import settings

from .langchain_tools import ALL_TOOLS

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
    _LANGCHAIN_AVAILABLE = True
except ImportError:
    _LANGCHAIN_AVAILABLE = False

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are MindMesh, a helpful, accurate personal AI assistant embedded in "
    "a live dashboard. Answer any question directly and correctly, the way a "
    "knowledgeable assistant would — general knowledge, opinions, "
    "explanations, follow-ups, comparisons, anything at all. If a question "
    "rests on a false premise, correct it briefly rather than going along "
    "with it.\n\n"
    "You have tools for live weather, live system stats, the current date/"
    "time, and showing a 3D model or image for whatever the conversation is "
    "currently about. Call show_3d_visual whenever there's something "
    "concrete worth putting on screen — not only when explicitly asked to "
    "'show' something — using a precise phrase for exactly that subject. "
    "Call the weather/stats/time tools only when the user is specifically "
    "asking about those live values, not for general knowledge questions "
    "about weather, computers, or time as concepts.\n\n"
    "Keep replies concise (2-5 sentences) unless the user asks for more."
)

_TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}
_llm_with_tools = None
_llm_plain = None


def _build_chat_model():
    model = settings.LLM_MODEL or ""
    temperature = getattr(settings, "LLM_TEMPERATURE", None)
    if temperature is None:
        # Gemini 3 models are tuned for temperature 1.0 (lower values can
        # cause looping / degraded output); everything else stays at 0.
        temperature = 1.0 if "gemini-3" in model.lower() else 0
    kwargs = {
        "model": model,
        "temperature": temperature,
        "api_key": settings.LLM_API_KEY,
    }
    if settings.LLM_BASE_URL and "api.openai.com" not in settings.LLM_BASE_URL:
        kwargs["base_url"] = settings.LLM_BASE_URL
    return ChatOpenAI(**kwargs)


def _get_llm():
    """Chat model with tools bound (first call: model decides on tools)."""
    global _llm_with_tools
    if _llm_with_tools is None:
        _llm_with_tools = _build_chat_model().bind_tools(ALL_TOOLS)
    return _llm_with_tools


def _get_plain_llm():
    """Same model, NO tools bound (used to phrase the final reply after
    the tools have already run on our side)."""
    global _llm_plain
    if _llm_plain is None:
        _llm_plain = _build_chat_model()
    return _llm_plain


def _message_text(msg):
    """Message content as plain text (some providers return a list of
    content parts instead of a string)."""
    content = getattr(msg, "content", "") or ""
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and part.get("type") == "text":
                parts.append(part.get("text", ""))
        content = "".join(parts)
    return content.strip()


class AgentResponse:
    def __init__(self, text, intent="agent", visual=None, topic=None):
        self.text = text
        self.intent = intent
        self.visual = visual  # dict or None
        self.topic = topic    # unused by this agent; kept for view compatibility

    def as_dict(self):
        return {"reply": self.text, "intent": self.intent, "visual": self.visual}


class MindMeshAgent:
    def is_configured(self):
        return _LANGCHAIN_AVAILABLE and bool(settings.LLM_API_KEY)

    def handle(self, user_text, history=None, last_topic=""):
        if not self.is_configured():
            return AgentResponse(self._setup_required_message(), "setup_required")

        llm = _get_llm()
        base_messages = [SystemMessage(content=SYSTEM_PROMPT)]
        for turn in (history or [])[-12:]:
            role = turn.get("role")
            if role == "user":
                base_messages.append(HumanMessage(content=turn["content"]))
            elif role == "assistant":
                base_messages.append(AIMessage(content=turn["content"]))
        messages = base_messages + [HumanMessage(content=user_text)]

        try:
            ai_msg = llm.invoke(messages)
        except Exception as exc:
            logger.exception("LLM call failed")
            reply = self._format_llm_error(exc)
            return AgentResponse(reply, "error")

        visual = None
        tool_calls = getattr(ai_msg, "tool_calls", None) or []

        if tool_calls:
            tool_results = []  # (tool name, args, result string)
            for call in tool_calls:
                tool_fn = _TOOLS_BY_NAME.get(call["name"])
                if tool_fn is None:
                    result_str = json.dumps({"error": f"unknown tool {call['name']}"})
                else:
                    try:
                        result_str = tool_fn.invoke(call["args"])
                    except Exception:
                        logger.exception("Tool %s failed", call["name"])
                        result_str = json.dumps({"error": "tool execution failed"})

                tool_results.append((call["name"], call.get("args"), result_str))

                # Build the structured visual payload straight from the
                # tool's own result — not from the model's paraphrase of
                # it — so the frontend gets exact data (embed URL, live
                # numbers) rather than something reconstructed from text.
                if call["name"] == "show_3d_visual":
                    visual = _visual_from_show_3d(result_str) or visual
                elif call["name"] == "get_weather":
                    visual = _visual_from_json(result_str, "weather") or visual
                elif call["name"] == "get_system_stats":
                    visual = _visual_from_json(result_str, "stats") or visual

            # IMPORTANT: we deliberately do NOT replay the model's
            # tool-call message (AIMessage(tool_calls=...) + ToolMessage)
            # back to the model. Gemini 3 attaches a `thought_signature` to
            # every function call and rejects a replayed call without it
            # (HTTP 400), and LangChain's OpenAI client drops that field.
            # The tools already ran here, so the model only needs the
            # results as plain text to phrase its answer. This works the
            # same on OpenAI, Gemini 2.5/3, Ollama, etc.
            results_text = "\n".join(
                f"- {name}({json.dumps(args, ensure_ascii=False)}) -> {res}"
                for name, args, res in tool_results
            )
            followup = HumanMessage(content=(
                f"{user_text}\n\n"
                "[Tool results: the tools already ran, and any visual or "
                "live widget they produced is already shown on screen. "
                "Do not call tools again and do not mention tool names, "
                "JSON, or URLs. Just answer the user's message above in "
                "natural language using these results.]\n"
                f"{results_text}"
            ))

            try:
                final_msg = _get_plain_llm().invoke(base_messages + [followup])
                reply = _message_text(final_msg)
            except Exception as exc:
                logger.exception("LLM follow-up call failed")
                reply = self._format_llm_error(exc)
        else:
            reply = _message_text(ai_msg)

        if not reply:
            reply = "I'm not sure how to respond to that — could you rephrase?"

        return AgentResponse(reply, "agent", visual=visual)

    @staticmethod
    def _format_llm_error(exc):
        """
        Surfaces the actual exception in the reply when DEBUG=True (this
        is a local dev tool, not a public-facing product, so showing the
        real error — bad model name, invalid key, rate limit, network —
        saves a trip to the server logs). In production (DEBUG=False) it
        stays generic so nothing about your backend leaks to the page.
        """
        detail = str(exc).strip()
        if settings.DEBUG and detail:
            # Defensive: never echo the key itself even if some SDK
            # error message were to include it.
            safe_detail = detail.replace(settings.LLM_API_KEY, "***") if settings.LLM_API_KEY else detail
            return (
                f"LLM call failed: {safe_detail}\n\n"
                "Common causes: LLM_MODEL in .env isn't a real model name "
                "your key has access to (check your provider's dashboard "
                "for exact model IDs), the key is invalid/expired, or "
                "you've hit a rate limit."
            )
        return (
            "I ran into an error reaching the language model — check "
            "LLM_API_KEY / LLM_MODEL / LLM_BASE_URL in .env (and that the "
            "model name is one your key actually has access to), then "
            "check the server logs for the exact error."
        )

    @staticmethod
    def _setup_required_message():
        """
        Distinguishes the two distinct reasons is_configured() can be
        False, so the on-screen message tells you exactly what to fix
        instead of a generic "not configured" that could mean either.
        """
        if not _LANGCHAIN_AVAILABLE:
            return (
                "The langchain-openai / langchain-core packages aren't "
                "installed in this environment yet. Run:\n\n"
                "    pip install -r requirements.txt\n\n"
                "(if you're using a virtual environment, make sure it's "
                "activated first), then restart the server."
            )
        if not settings.LLM_API_KEY:
            return (
                "No LLM_API_KEY is set. Open your .env file (copy it from "
                ".env.example if you haven't yet) in the project root — the "
                "same folder as manage.py — and set:\n\n"
                "    LLM_API_KEY=sk-...your real key...\n"
                "    LLM_MODEL=gpt-4o-mini\n\n"
                "then restart the server (python manage.py runserver). "
                "Double-check the file is named exactly \".env\" (not "
                "\".env.txt\" — some editors hide the real extension) and "
                "is in the same folder as manage.py, not inside assistant/."
            )
        # Shouldn't normally be reachable, but keep a fallback just in case.
        return (
            "I'm not configured to answer right now — check LLM_API_KEY, "
            "LLM_MODEL, and that langchain-openai is installed, then "
            "restart the server."
        )


def _visual_from_show_3d(result_str):
    try:
        data = json.loads(result_str)
    except (ValueError, TypeError):
        return None
    if not data.get("found"):
        return None
    if data.get("kind") == "model3d":
        return {
            "type": "model3d",
            "data": {"title": data["title"], "embed_url": data["embed_url"]},
        }
    if data.get("kind") == "image":
        return {
            "type": "knowledge",
            "data": {"title": data["title"], "image": data["image"], "url": data.get("url")},
        }
    return None


def _visual_from_json(result_str, visual_type):
    try:
        data = json.loads(result_str)
    except (ValueError, TypeError):
        return None
    if data.get("error"):
        return None
    return {"type": visual_type, "data": data}
