"""
Compatibility views to match iOS frontend expectations.
These wrap the main views with the exact request/response formats the frontend expects.
"""
import uuid
from django.utils import timezone
from django.contrib.auth import authenticate, get_user_model
from rest_framework.decorators import api_view, permission_classes, authentication_classes, parser_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

User = get_user_model()

# ---- Helpers ----
def user_payload(user):
    """User payload matching frontend User model expectations"""
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
def config(request):
    """
    Get API configuration (public endpoint).
    GET /api/config/
    Returns basic configuration info the app might need.
    """
    from django.conf import settings
    return Response({
        "api_version": "1.0",
        "base_url": request.build_absolute_uri('/api/'),
        "features": {
            "signup": True,
            "login": True,
            "chat": True,
            "summarize": True,
        }
    }, status=200)

@api_view(['GET'])
@permission_classes([AllowAny])
def tones(request):
    """
    Get available AI tones.
    GET /api/tones/
    Returns list of available tones with descriptions.
    """
    return Response({
        "tones": [
            {
                "id": "PlainClinical",
                "name": "Plain Clinical",
                "description": "Warm but precise medical guidance"
            },
            {
                "id": "Caregiver",
                "name": "Caregiver",
                "description": "Comforting health companion mode"
            },
            {
                "id": "Faith",
                "name": "Faith",
                "description": "Faith-filled health guidance with spiritual support"
            },
            {
                "id": "Clinical",
                "name": "Clinical",
                "description": "Structured SOAP notes for healthcare professionals"
            },
            {
                "id": "Geriatric",
                "name": "Geriatric",
                "description": "Elderly care focused"
            },
            {
                "id": "EmotionalSupport",
                "name": "Emotional Support",
                "description": "Emotional support mode"
            }
        ]
    }, status=200)

@api_view(['GET'])
@permission_classes([AllowAny])
def auth_status(request):
    """
    Health check / auth status endpoint.
    GET /api/auth/status/
    """
    if request.user.is_authenticated:
        return Response({
            "authenticated": True,
            "user": user_payload(request.user),
            "status": "ok",
            "time": timezone.now().isoformat()
        }, status=200)
    else:
        return Response({
            "authenticated": False,
            "status": "ok",
            "time": timezone.now().isoformat()
        }, status=200)

@api_view(['POST'])
@parser_classes([JSONParser])
@permission_classes([AllowAny])
def signup(request):
    """
    User registration endpoint - uses SAME user creation as PWA.
    POST /api/signup/
    Expects: {name, email, password, language}
    """
    email = (request.data.get("email") or "").strip().lower()
    password = request.data.get("password") or ""
    name = request.data.get("name", "")
    language = request.data.get("language", "en-US")
    
    if not email or not password:
        return Response({"error": "email and password are required"}, status=400)

    # Case-insensitive email check (same as PWA)
    if User.objects.filter(email__iexact=email).exists():
        return Response({"error": "Email already exists"}, status=400)

    # Parse name into first_name and last_name
    name_parts = name.strip().split(' ', 1)
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""
    
    # Generate username from email
    username = email.split("@")[0][:30]
    base, n, candidate = username, 1, username
    while User.objects.filter(username__iexact=candidate).exists():
        candidate = f"{base}{n}"
        n += 1

    user = User.objects.create_user(
        username=candidate,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name
    )
    
    # Create Profile (same as PWA does in signup_view)
    try:
        from myApp.models import Profile
        from myApp.utils import get_client_ip
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.language = language
        profile.signup_ip = get_client_ip(request)
        profile.signup_country = getattr(request, "country_code", None)
        profile.save()
    except Exception:
        pass  # Don't fail signup if profile creation fails

    # Create token
    from rest_framework.authtoken.models import Token
    token, _ = Token.objects.get_or_create(user=user)
    
    response_data = user_payload(user)
    response_data['token'] = token.key
    
    return Response(response_data, status=201)

@api_view(['POST'])
@parser_classes([JSONParser])
@permission_classes([AllowAny])
def login(request):
    """
    User login endpoint - EXACT SAME as main website WarmLoginView.post()
    POST /api/login/
    Expects: {email, password}
    
    Matches EXACTLY what works on the main website at myApp/views.py line 3080:
    user = authenticate(request, username=email, password=password)
    """
    email = request.data.get("email")
    password = request.data.get("password")

    print(f"🔍 LOGIN DEBUG: Email={email}, Password={'*' * len(password) if password else 'None'}")

    if not email or not password:
        print(f"❌ LOGIN DEBUG: Missing credentials")
        return Response({"error": "Email and password are required"}, status=400)

    # EXACT SAME as main website: authenticate(request, username=email, password=password)
    # This is what works on your main website (line 3080 in myApp/views.py)
    from django.contrib.auth import authenticate
    user = authenticate(request, username=email, password=password)
    
    print(f"🔍 LOGIN DEBUG: Authenticate result: {user.username if user else None} (id={user.id if user else None})")
    
    if not user:
        print(f"❌ LOGIN DEBUG: Authentication failed for email: {email}")
        return Response({"error": "Invalid credentials"}, status=401)

    if not user.is_active:
        print(f"❌ LOGIN DEBUG: User inactive: {user.username}")
        return Response({"error": "Account is disabled"}, status=401)
    
    print(f"✅ LOGIN DEBUG: Authentication successful for {user.username} (id={user.id})")

    # Create/get token for mobile API
    from rest_framework.authtoken.models import Token
    token, _ = Token.objects.get_or_create(user=user)
    
    print(f"✅ LOGIN DEBUG: Token created: {token.key[:10]}...")
    
    response_data = user_payload(user)
    response_data['token'] = token.key
    
    return Response(response_data, status=200)

# ---- Authenticated endpoints ----
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def user_settings(request):
    """
    Get user settings/profile.
    GET /api/user/settings/
    """
    return Response(user_payload(request.user), status=200)

@api_view(['POST'])
@parser_classes([JSONParser])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def user_settings_update(request):
    """
    Update user settings/profile.
    POST /api/user/settings/update/
    """
    user = request.user
    changed = False
    
    # Update fields from request
    if 'first_name' in request.data:
        user.first_name = request.data['first_name']
        changed = True
    if 'last_name' in request.data:
        user.last_name = request.data['last_name']
        changed = True
    if 'email' in request.data:
        new_email = request.data['email'].lower()
        if new_email != user.email:
            # Check if email is already taken
            if User.objects.filter(email=new_email).exclude(id=user.id).exists():
                return Response({"error": "Email already in use"}, status=400)
            user.email = new_email
            changed = True
    
    if changed:
        user.save()
    
    return Response(user_payload(user), status=200)

@api_view(['GET', 'PUT'])
@parser_classes([JSONParser])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def user_preferences(request):
    """
    Get or update user preferences (tone, language, etc.).
    GET /api/user/preferences/
    PUT /api/user/preferences/
    """
    from myApp.models import Profile
    
    profile, _ = Profile.objects.get_or_create(user=request.user)
    
    if request.method == 'GET':
        return Response({
            "tone": getattr(profile, 'default_tone', 'PlainClinical'),
            "language": profile.language or 'en-US',
            "care_setting": getattr(profile, 'default_care_setting', None),
            "faith_setting": getattr(profile, 'default_faith_setting', None),
        }, status=200)
    
    elif request.method == 'PUT':
        # Update preferences
        if 'tone' in request.data:
            # Store tone preference (you may need to add this field to Profile model)
            # For now, we'll store it in a JSON field or add it later
            pass  # TODO: Add tone preference to Profile model if needed
        
        if 'language' in request.data:
            profile.language = request.data['language']
            profile.save(update_fields=['language'])
        
        return Response({
            "tone": getattr(profile, 'default_tone', 'PlainClinical'),
            "language": profile.language or 'en-US',
            "care_setting": getattr(profile, 'default_care_setting', None),
            "faith_setting": getattr(profile, 'default_faith_setting', None),
        }, status=200)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def chat_sessions(request):
    """
    Get user's chat sessions - REAL IMPLEMENTATION.
    GET /api/chat/sessions/
    """
    from myApp.models import ChatSession
    
    sessions = ChatSession.objects.filter(
        user=request.user,
        archived=False
    ).order_by('-updated_at')[:50]
    
    # Transform messages to match iOS ChatMessage format
    def transform_messages(msgs):
        if not msgs:
            return []
        transformed = []
        for msg in msgs:
            # Skip system messages for iOS
            if msg.get("role") == "system":
                continue
            # Convert 'ts' to 'timestamp' for iOS compatibility
            transformed_msg = {
                "id": str(uuid.uuid4()),  # Generate unique ID for iOS
                "role": msg.get("role", ""),
                "content": msg.get("content", ""),
                "timestamp": msg.get("ts", ""),  # Rename ts -> timestamp
                "session_id": None,  # iOS will decode this to sessionId
                "metadata": None
            }
            transformed.append(transformed_msg)
        return transformed
    
    return Response([{
        "id": s.id,
        "title": s.title or "Untitled",
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
        "tone": s.tone or "PlainClinical",
        "lang": s.lang or "en-US",
        "messages": transform_messages(s.messages or []),  # Transform messages!
    } for s in sessions], status=200)

@api_view(['POST'])
@parser_classes([JSONParser])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_chat_session(request):
    """
    Create a new chat session - REAL IMPLEMENTATION.
    POST /api/chat/sessions/new/
    Expects: {title, tone, lang} - uses 'lang' not 'language' per contract
    """
    from myApp.models import ChatSession
    from myApp.views import normalize_tone
    
    title = request.data.get("title", "New Conversation")
    tone = normalize_tone(request.data.get("tone"))
    lang = request.data.get("lang", "en-US")  # Use 'lang' per mobile contract
    
    # Create real session in database
    session = ChatSession.objects.create(
        user=request.user,
        title=title,
        tone=tone,
        lang=lang,
        messages=[]
    )
    
    # Make it server-sticky
    request.session["active_chat_session_id"] = session.id
    request.session.modified = True
    
    print(f"📝 SESSION: Created {session.id} for {request.user.username}, Tone={tone}")
    
    return Response({
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "tone": tone,
        "language": lang,
    }, status=201)

@api_view(['POST'])
@parser_classes([JSONParser, MultiPartParser, FormParser])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def send_chat(request):
    """
    Send a chat message - REAL AI CONNECTED.
    POST /api/send-chat/
    
    Frontend sends multipart/form-data with:
    - message: string (user text message)
    - tone: string (e.g., "plain_clinical", "caregiver", "faith", etc.)
    - lang: string (language code, e.g., "en-US")
    - session_id: string (optional, represents integer session ID)
    - care_setting: string (optional, for Clinical/Caregiver tones)
    - faith_setting: string (optional, for Faith tone)
    - files[]: array of file data (multipart file uploads)
    
    Returns iOS ChatMessage format: {id, role, content, timestamp, session_id, metadata}
    """
    # Real AI enabled! 🚀
    USE_REAL_AI = True
    
    # Extract form fields (works for both multipart and JSON)
    user_message = (request.data.get("message") or "").strip()
    tone_raw = request.data.get("tone", "PlainClinical")
    lang = request.data.get("lang", "en-US")
    care_setting = request.data.get("care_setting")
    faith_setting = request.data.get("faith_setting")
    
    # Parse session_id (frontend sends as string, but it's an integer)
    incoming_session_id = None
    session_id_str = request.data.get("session_id")
    if session_id_str:
        try:
            incoming_session_id = int(session_id_str)
        except (ValueError, TypeError):
            print(f"⚠️ Invalid session_id format: {session_id_str}, ignoring")
    
    # Get files - frontend sends as "files[]" array
    files = request.FILES.getlist("files[]")
    
    # Fallback for alternative field names (backwards compatibility)
    if not files:
        files = request.FILES.getlist("file") or ([request.FILES["file"]] if "file" in request.FILES else [])
    
    # Log file information for debugging
    if files:
        print(f"📎 Received {len(files)} file(s):")
        for idx, f in enumerate(files):
            print(f"  File {idx}: name={f.name}, size={f.size}, content_type={f.content_type}")
    
    # DEBUG: Log raw request data to diagnose issues
    print(f"🔍 DEBUG: Request keys: {list(request.data.keys())}")
    print(f"🔍 DEBUG: Tone from request: {repr(tone_raw)}")
    print(f"🔍 DEBUG: Message: {user_message[:50] if user_message else '[empty]'}...")
    print(f"🔍 DEBUG: Files: {len(files)} file(s)")
    print(f"🔍 DEBUG: Session ID: {incoming_session_id}")
    
    if not user_message and not files:
        return Response({"error": "message or files required"}, status=400)
    
    # Real AI implementation
    try:
        from myApp.views import (
            normalize_tone, get_system_prompt, get_setting_prompt, get_faith_prompt,
            norm_setting, norm_faith_setting, _classify_mode, _now_ts, _now_iso,
            _trim_history, _ensure_session_for_user, summarize_single_file
        )
        from openai import OpenAI
        
        client = OpenAI()
        
        # Normalize tone (frontend may send "plain_clinical" but backend expects "PlainClinical")
        # The normalize_tone function handles this conversion
        tone = normalize_tone(tone_raw)
        
        print(f"💬 User={request.user.username}, Msg={user_message[:40] if user_message else '[files]'}..., Tone={tone} (normalized from {repr(tone_raw)})")
        
        # Classify mode
        mode, topic_hint = _classify_mode(user_message, bool(files), request.session)
        print(f"📊 Mode={mode}, Files={len(files)}")
        
        # Build layered system prompt
        base = get_system_prompt(tone)
        if tone == "Faith" and faith_setting:
            sys_prompt = get_faith_prompt(base, norm_faith_setting(faith_setting))
        elif tone in ("Clinical", "Caregiver") and care_setting:
            sys_prompt = get_setting_prompt(base, norm_setting(care_setting))
        else:
            sys_prompt = base
        sys_prompt = f"{sys_prompt}\n\n(Always respond in {lang} unless told otherwise.)"
        
        header = f"ResponseMode: {mode}" + (f"\nTopicHint: {topic_hint}" if topic_hint else "")
        
        # Session management
        # incoming_session_id is already parsed as int above
        sticky = request.session.get("active_chat_session_id")
        chosen_id = incoming_session_id or sticky
        sess, created = _ensure_session_for_user(request.user, tone, lang, user_message or "[files]", chosen_id)
        request.session["active_chat_session_id"] = sess.id
        request.session.modified = True
        
        # Build history (strip stale system prompts so tone swaps take effect)
        hist = [
            {"role": m.get("role"), "content": m.get("content")}
            for m in (sess.messages or [])
            if m.get("role") in ("user", "assistant") and m.get("content")
        ]
        chat_history = [
            {"role": "system", "content": sys_prompt},
            {"role": "system", "content": header},
            *hist,
        ]
        
        # Process files
        if files:
            sections = [
                summarize_single_file(f, tone, sys_prompt, request.user, request)[1]
                for f in files
            ]
            context = "\n\n".join(sections).strip()
            if context:
                chat_history.append({
                    "role": "user",
                    "content": f"(Medical context):\n{context}"
                })
        
        if user_message:
            chat_history.append({"role": "user", "content": user_message})
        
        # Two-pass AI
        raw = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.6,
            messages=chat_history
        ).choices[0].message.content.strip()
        final = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.3,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "system", "content": header},
                {"role": "user", "content": f"Rewrite warmly:\n\n{raw}"}
            ]
        ).choices[0].message.content.strip()
        
        # Save
        existing = sess.messages or []
        non_system_msgs = [m for m in existing if m.get("role") != "system"]
        msgs = [
            {"role": "system", "content": sys_prompt, "ts": _now_iso()},
            {"role": "system", "content": header, "ts": _now_iso()},
        ]
        msgs.extend(non_system_msgs)
        if files:
            msgs.append({"role": "user", "content": "(Files uploaded)", "ts": _now_iso()})
        if user_message:
            msgs.append({"role": "user", "content": user_message, "ts": _now_iso()})
        msgs.append({"role": "assistant", "content": final, "ts": _now_iso()})
        sess.messages = _trim_history(msgs, 200)
        sess.updated_at = timezone.now()
        sess.save(update_fields=["messages", "updated_at"])
        
        # Soft memory
        request.session["nm_last_mode"] = mode if mode != "QUICK" else "QUICK"
        request.session["nm_last_short_msg"] = user_message if mode == "QUICK" else ""
        request.session["nm_last_ts"] = _now_ts()
        request.session.modified = True
        
        # Return iOS ChatMessage format (NOT document summary format)
        # Required fields: id, role, content, timestamp, session_id, metadata
        response_data = {
            "id": str(uuid.uuid4()),
            "role": "assistant",  # MUST be "assistant" for AI responses
            "content": final,  # The AI's response text (NOT "summary")
            "timestamp": timezone.now().isoformat(),  # ISO 8601 format (NOT "created_at")
            "session_id": sess.id,  # Integer session ID (NOT string)
            "metadata": None  # Optional, can be null
        }
        
        print(f"✅ CHAT RESPONSE: Returning chat message format with {len(final)} chars")
        return Response(response_data, status=200)
        
    except Exception as e:
        print(f"❌ CHAT ERROR: {e}")
        import traceback
        traceback.print_exc()
        # Return error in JSON format (not HTML)
        # Always return JSON, never HTML error pages
        from django.conf import settings
        error_detail = str(e) if getattr(settings, 'DEBUG', False) else None
        return Response({
            "error": "System busy. Try again in a moment.",
            "detail": error_detail
        }, status=503)

@api_view(['GET', 'POST'])
@parser_classes([JSONParser])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def summarize(request):
    """
    Get medical summaries (GET) or create new summary (POST).
    GET /api/summarize/ - Get all summaries
    POST /api/summarize/ - Upload file and create summary
    Expects: {filename, fileType, content, tone, language}
    """
    if request.method == 'GET':
        # TODO: Connect to your actual medical summary model
        # from myApp.models import MedicalSummary
        # summaries = MedicalSummary.objects.filter(user=request.user).order_by('-created_at')
        # return Response([{
        #     "id": str(s.id),
        #     "title": s.title,
        #     "summary": s.summary,
        #     "created_at": s.created_at.isoformat(),
        # } for s in summaries], status=200)
        
        # Stub response
        return Response([], status=200)
    
    else:  # POST
        filename = request.data.get("filename")
        file_type = request.data.get("fileType", request.data.get("file_type"))
        content = request.data.get("content")  # Base64 encoded
        tone = request.data.get("tone", "professional")
        language = request.data.get("language", "en-US")
        
        if not content:
            return Response({"error": "content is required"}, status=400)
        
        # TODO: Connect to your actual file processing logic
        # Process the base64 content, extract text, summarize
        
        # Stub response
        return Response({
            "id": str(uuid.uuid4()),
            "title": filename or "Untitled Document",
            "summary": "This is a medical summary placeholder. The document has been processed.",
            "created_at": timezone.now().isoformat(),
            "tone": tone,
            "language": language,
        }, status=201)

@api_view(['POST'])
@parser_classes([JSONParser])
@permission_classes([AllowAny])
def google_signin(request):
    """
    Google Sign-In endpoint.
    POST /auth/google/
    Expects: {token}
    """
    google_token = request.data.get("token")
    
    if not google_token:
        return Response({"error": "token is required"}, status=400)
    
    # TODO: Implement Google OAuth token verification
    # from google.oauth2 import id_token
    # from google.auth.transport import requests
    # 
    # try:
    #     # Verify the token
    #     idinfo = id_token.verify_oauth2_token(
    #         google_token, 
    #         requests.Request(), 
    #         GOOGLE_CLIENT_ID
    #     )
    #     
    #     email = idinfo['email']
    #     name = idinfo.get('name', '')
    #     
    #     # Get or create user
    #     user, created = User.objects.get_or_create(
    #         email=email,
    #         defaults={
    #             'username': email.split('@')[0],
    #             'first_name': name.split()[0] if name else '',
    #             'last_name': ' '.join(name.split()[1:]) if len(name.split()) > 1 else '',
    #         }
    #     )
    #     
    #     from rest_framework.authtoken.models import Token
    #     token, _ = Token.objects.get_or_create(user=user)
    #     
    #     response_data = user_payload(user)
    #     response_data['token'] = token.key
    #     
    #     return Response(response_data, status=200)
    # except ValueError:
    #     return Response({"error": "Invalid Google token"}, status=401)
    
    # Stub response - you need to implement Google OAuth
    return Response({
        "error": "Google Sign-In not yet implemented. Please use email/password authentication."
    }, status=501)

@api_view(['POST'])
@parser_classes([JSONParser])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def clear_session(request):
    """
    Clear session and soft memory - for "New Chat" button.
    POST /api/chat/clear-session/
    """
    # Clear soft memory (affects mode upgrades)
    for k in ["latest_summary", "chat_history", "nm_last_mode", "nm_last_short_msg", "nm_last_ts"]:
        request.session.pop(k, None)
    
    # Clear sticky session ID
    request.session.pop("active_chat_session_id", None)
    request.session.modified = True
    
    print(f"🆕 CLEAR: Cleared session for {request.user.username}")
    
    return Response({"ok": True}, status=200)

