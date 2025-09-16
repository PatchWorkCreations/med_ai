# myApp/api_chat.py
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_datetime

from .models import ChatSession

def _row(s: ChatSession):
    return {
        "id": s.id,
        "title": s.title or "Untitled",
        "tone": s.tone or "PlainClinical",
        "lang": s.lang or "en-US",
        "archived": s.archived,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    }

@login_required
@require_GET
def list_chat_sessions(request):
    """Return up to 200 most recent unarchived sessions for the user."""
    rows = (
        ChatSession.objects
        .filter(user=request.user, archived=False)
        .order_by("-updated_at")[:200]
    )
    return JsonResponse([_row(r) for r in rows], safe=False)

@login_required
@require_GET
def get_chat_session(request, session_id: int):
    """Return a session with full message history."""
    try:
        s = ChatSession.objects.get(id=session_id, user=request.user, archived=False)
    except ChatSession.DoesNotExist:
        return JsonResponse({"detail": "Not found"}, status=404)

    return JsonResponse({
        **_row(s),
        "messages": s.messages,   # [{role, content, ts?, meta?}] in append order
    })
