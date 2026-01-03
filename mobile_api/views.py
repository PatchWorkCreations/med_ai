import uuid
from django.utils import timezone
from django.contrib.auth import authenticate, get_user_model
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework import status

User = get_user_model()

# ---- Helpers ----
def user_payload(user):
    """Keep it minimal + stable for iOS"""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "date_joined": user.date_joined.isoformat(),
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }

# ---- Public endpoints ----
@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    """Health check endpoint"""
    return Response({"status": "ok", "time": timezone.now().isoformat()}, status=200)

@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    """User registration endpoint"""
    email = (request.data.get("email") or "").lower()
    password = request.data.get("password") or ""
    first = request.data.get("first_name", "")
    last = request.data.get("last_name", "")
    username = (request.data.get("username") or email.split("@")[0])[:30]

    if not email or not password:
        return Response({"error": "email and password are required"}, status=400)

    if User.objects.filter(email=email).exists():
        return Response({"error": "Email already exists"}, status=400)

    # Unique username fallback
    base, n, candidate = username, 1, username
    while User.objects.filter(username=candidate).exists():
        candidate = f"{base}-{n}"
        n += 1

    user = User.objects.create_user(
        username=candidate, email=email, password=password,
        first_name=first, last_name=last
    )

    # Token
    from rest_framework.authtoken.models import Token
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"user": user_payload(user), "token": token.key}, status=201)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """User login endpoint"""
    email = (request.data.get("email") or "").lower()
    password = request.data.get("password") or ""

    try:
        u = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"error": "Invalid credentials"}, status=401)

    user = authenticate(request, username=u.username, password=password)
    if not user:
        return Response({"error": "Invalid credentials"}, status=401)

    from rest_framework.authtoken.models import Token
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"user": user_payload(user), "token": token.key}, status=200)

# ---- Authenticated endpoints ----
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def auth_status(request):
    """Check authentication status"""
    return Response({"authenticated": True, "user": user_payload(request.user)}, status=200)

@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def user_settings(request):
    """Get or update user settings"""
    if request.method == 'GET':
        return Response(user_payload(request.user))
    
    # Partial update
    first = request.data.get("first_name")
    last = request.data.get("last_name")
    changed = False
    if first is not None:
        request.user.first_name = first
        changed = True
    if last is not None:
        request.user.last_name = last
        changed = True
    if changed:
        request.user.save(update_fields=['first_name', 'last_name'])
    return Response({"success": True}, status=200)

# ---- Chat adapters (call your existing logic if you have it) ----
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def chat_sessions(request):
    """
    Get user's chat sessions.
    If you already have a function like get_sessions(user), call it here.
    """
    # Example static stub - replace with actual logic
    return Response({"sessions": []}, status=200)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def send_chat(request):
    """
    Send a chat message.
    If you have existing send_chat logic elsewhere, import & call it.
    """
    message = request.data.get("message")
    session_id = request.data.get("session_id")
    if not message:
        return Response({"error": "message is required"}, status=400)

    # If you have existing send_chat logic elsewhere, import & call it.
    # from myApp.api_chat import send_message
    # ai_response = send_message(user=request.user, session_id=session_id, text=message)

    # Placeholder response - replace with actual AI logic
    ai_response = "Hello from the model 👋"
    
    return Response({
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "content": ai_response,
        "timestamp": timezone.now().isoformat(),
        "session_id": session_id,
        "metadata": None
    }, status=200)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def summarize(request):
    """
    Summarize text.
    Replace with actual summarization logic if available.
    """
    text = request.data.get("text", "")
    summary = text[:200] + ("…" if len(text) > 200 else "")
    return Response({"summary": summary}, status=200)
