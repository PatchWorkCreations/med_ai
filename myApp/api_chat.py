# myApp/api_chat.py
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_datetime

from .models import ChatSession

def _row(s: ChatSession, include_messages=False):
    """Convert ChatSession to dict. Set include_messages=True to include message preview."""
    messages = s.messages or []
    result = {
        "id": s.id,
        "title": s.title or "Untitled",
        "tone": s.tone or "PlainClinical",
        "lang": s.lang or "en-US",
        "archived": getattr(s, 'archived', False),
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        "message_count": len(messages),  # Include message count for frontend filtering
    }
    if include_messages:
        result["messages"] = messages
    return result

@login_required
@require_GET
def list_chat_sessions(request):
    """Return up to 200 most recent sessions for the user (both archived and unarchived).
    Excludes empty sessions (sessions with no messages) to avoid cluttering the sidebar."""
    try:
        # Get all sessions (both archived and unarchived) for the user
        rows = (
            ChatSession.objects
            .filter(user=request.user)
            .order_by("-updated_at")[:200]
        )
        # Filter out empty sessions (sessions with no messages)
        # Only include sessions that have at least one message
        filtered_rows = [
            r for r in rows 
            if r.messages and len(r.messages) > 0
        ]
        return JsonResponse([_row(r) for r in filtered_rows], safe=False)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e), "detail": "Failed to load sessions"}, status=500)

@login_required
@require_GET
def get_chat_session(request, session_id: int):
    """Return a session with full message history."""
    try:
        s = ChatSession.objects.get(id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return JsonResponse({"detail": "Session not found"}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e), "detail": "Failed to load session"}, status=500)

    return JsonResponse({
        **_row(s, include_messages=False),
        "messages": s.messages or [],   # [{role, content, ts?, meta?}] in append order
    })
