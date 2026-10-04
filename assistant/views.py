import json

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .agent.core_agent import MindMeshAgent
from .agent import tools
from .models import ConversationSession, Message

_agent = MindMeshAgent()


def _get_or_create_session(request):
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    session, _ = ConversationSession.objects.get_or_create(session_key=session_key)
    return session


def dashboard(request):
    """Renders the MindMesh single-page dashboard shell."""
    session = _get_or_create_session(request)
    history = list(
        session.messages.order_by("created_at").values("role", "content", "created_at")
    )
    context = {
        "assistant_name": settings.ASSISTANT_NAME,
        "wake_word": settings.WAKE_WORD,
        "default_city": settings.DEFAULT_CITY,
        "history": history,
        "llm_configured": _agent.is_configured(),
    }
    return render(request, "assistant/dashboard.html", context)


@require_POST
def chat_api(request):
    """
    POST { "message": "..." }
    -> { "reply": "...", "intent": "...", "visual": {...}|null, "timestamp": "..." }
    """
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    user_text = (payload.get("message") or "").strip()
    if not user_text:
        return JsonResponse({"error": "message is required."}, status=400)

    session = _get_or_create_session(request)

    # Build recent history for LLM-fallback context.
    recent = list(
        session.messages.order_by("-created_at").values("role", "content")[:10]
    )
    recent.reverse()
    history = [{"role": m["role"], "content": m["content"]} for m in recent if m["role"] != "system"]

    Message.objects.create(session=session, role="user", content=user_text)

    result = _agent.handle(user_text, history=history, last_topic=session.last_topic)

    Message.objects.create(
        session=session,
        role="assistant",
        content=result.text,
        intent=result.intent,
        visual_type=(result.visual or {}).get("type", ""),
        visual_payload=result.visual,
    )

    if result.topic:
        session.last_topic = result.topic
        session.save(update_fields=["last_topic", "updated_at"])

    response = result.as_dict()
    response["timestamp"] = session.updated_at.isoformat()
    return JsonResponse(response)


@require_GET
def stats_api(request):
    return JsonResponse(tools.get_system_stats())


@require_GET
def weather_api(request):
    city = request.GET.get("city") or settings.DEFAULT_CITY
    return JsonResponse(tools.get_weather(city=city))


@require_GET
def clock_api(request):
    return JsonResponse(tools.get_current_datetime())


@require_GET
def history_api(request):
    session = _get_or_create_session(request)
    data = list(
        session.messages.order_by("created_at").values(
            "role", "content", "intent", "visual_type", "visual_payload", "created_at"
        )
    )
    return JsonResponse({"messages": data})
