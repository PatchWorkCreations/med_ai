# myApp/api_chat.py
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
import uuid

from .models import ChatSession

def _pascal_to_snake_case(tone: str) -> str:
    """Convert PascalCase tone to snake_case (e.g., 'PlainClinical' -> 'plain_clinical')."""
    if not tone:
        return "plain_clinical"
    # If already snake_case, return as is
    if '_' in tone:
        return tone.lower()
    # Convert PascalCase to snake_case
    result = []
    for i, char in enumerate(tone):
        if char.isupper() and i > 0:
            result.append('_')
        result.append(char.lower())
    return ''.join(result)

def _transform_message(msg: dict, session_id: int) -> dict:
    """Transform a message from database format to iOS expected format."""
    return {
        "id": msg.get("id") or f"msg_{uuid.uuid4().hex[:12]}",
        "role": msg.get("role", ""),
        "content": msg.get("content", ""),
        "timestamp": msg.get("ts") or msg.get("timestamp", ""),  # ✅ Renamed ts -> timestamp
        "session_id": session_id,  # ✅ Added session_id
        "metadata": msg.get("meta") or msg.get("metadata") or None  # ✅ Added metadata
    }

def _row(s: ChatSession, include_messages=False):
    """Convert ChatSession to dict. Set include_messages=True to include message preview."""
    messages = s.messages or []
    tone = _pascal_to_snake_case(s.tone or "PlainClinical")  # ✅ Convert to snake_case
    
    result = {
        "id": s.id,
        "title": s.title or "Untitled",
        "tone": tone,  # ✅ Now in snake_case
        "lang": s.lang or "en-US",
        "archived": getattr(s, 'archived', False),
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        "message_count": len(messages),  # Include message count for frontend filtering
    }
    
    if include_messages:
        # ✅ Transform messages to iOS format
        result["messages"] = [
            _transform_message(msg, s.id) 
            for msg in messages 
            if msg.get("role") != "system"  # Skip system messages
        ]
    else:
        result["messages"] = []  # ✅ Always include messages array
    
    return result

@api_view(['GET'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def list_chat_sessions(request):
    """Return up to 200 most recent sessions for the user (both archived and unarchived).
    Excludes empty sessions (sessions with no messages) to avoid cluttering the sidebar.
    Now supports both TokenAuthentication (iOS) and SessionAuthentication (web)."""
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
        # ✅ Return sessions with messages included
        return JsonResponse([_row(r, include_messages=True) for r in filtered_rows], safe=False)
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
