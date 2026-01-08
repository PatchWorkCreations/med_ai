import uuid
import json
from django.utils import timezone
from django.contrib.auth import authenticate, get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes, authentication_classes, parser_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework import status

User = get_user_model()

# Import chat models and functions
from myApp.models import ChatSession

# ---- Helpers ----
def user_payload(user):
    """Keep it minimal + stable for iOS - matches iOS User model"""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "date_joined": user.date_joined.isoformat(),
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }

def format_message_for_ios(msg_dict):
    """Convert internal message format to iOS expected format"""
    return {
        "id": msg_dict.get("id") or f"msg_{uuid.uuid4().hex[:12]}",
        "role": msg_dict.get("role", "user"),
        "content": msg_dict.get("content", ""),
        "timestamp": msg_dict.get("ts") or msg_dict.get("timestamp") or timezone.now().isoformat(),
        "session_id": msg_dict.get("session_id"),
        "metadata": msg_dict.get("meta")
    }

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

def format_session_for_ios(session):
    """Convert ChatSession to iOS expected format"""
    messages = session.messages or []
    formatted_messages = []
    
    for msg in messages:
        # Skip system messages for iOS
        if msg.get("role") == "system":
            continue
        
        formatted_msg = format_message_for_ios({
            **msg,
            "session_id": session.id
        })
        formatted_messages.append(formatted_msg)
    
    # Convert tone from PascalCase to snake_case for iOS
    tone = _pascal_to_snake_case(session.tone or "PlainClinical")
    
    return {
        "id": session.id,
        "title": session.title or "Untitled",
        "created_at": session.created_at.isoformat() if session.created_at else timezone.now().isoformat(),
        "updated_at": session.updated_at.isoformat() if session.updated_at else timezone.now().isoformat(),
        "tone": tone,  # ✅ Now converted to snake_case
        "lang": session.lang or "en-US",
        "messages": formatted_messages  # ✅ Always includes messages array
    }

# ---- Public endpoints ----
@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    """Health check endpoint"""
    return Response({"status": "ok", "time": timezone.now().isoformat()}, status=200)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    """User registration endpoint - iOS compatible"""
    email = (request.data.get("email") or "").lower()
    password = request.data.get("password") or ""
    language = request.data.get("language", "en-US")
    
    # Handle both iOS format (name) and standard format (first_name, last_name)
    name = request.data.get("name", "")
    first = request.data.get("first_name", "")
    last = request.data.get("last_name", "")
    
    # If iOS sends "name", parse it into first_name and last_name
    if name and not (first or last):
        name_parts = name.strip().split(None, 1)
        if len(name_parts) >= 2:
            first = name_parts[0]
            last = name_parts[1]
        elif len(name_parts) == 1:
            first = name_parts[0]
            last = ""
    
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
    
    # Set language preference
    if language:
        from myApp.models import Profile
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.language = language
        profile.save()

    # Token
    from rest_framework.authtoken.models import Token
    token, _ = Token.objects.get_or_create(user=user)
    
    # Return in iOS-expected format (flat structure, not nested)
    # iOS expects: {id, username, email, first_name, last_name, date_joined, last_login, token}
    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "date_joined": user.date_joined.isoformat(),
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "token": token.key
    }, status=201)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """User login endpoint - Returns token in iOS-expected format"""
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
    
    # Return in iOS-expected format (flat structure, not nested)
    # iOS expects: {id, email, first_name, last_name, date_joined, last_login, token}
    return Response({
        **user_payload(user),
        "token": token.key
    }, status=200)

# ---- Authenticated endpoints ----
@csrf_exempt
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def auth_status(request):
    """Check authentication status"""
    return Response({"authenticated": True, "user": user_payload(request.user)}, status=200)

@csrf_exempt
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def user_settings(request):
    """Get user settings"""
    return Response(user_payload(request.user))
    
@csrf_exempt
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def user_settings_update(request):
    """Update user settings"""
    first = request.data.get("first_name")
    last = request.data.get("last_name")
    email = request.data.get("email")
    language = request.data.get("language")
    
    changed = False
    if first is not None:
        request.user.first_name = first
        changed = True
    if last is not None:
        request.user.last_name = last
        changed = True
    if email is not None:
        request.user.email = email
        changed = True
    if language is not None:
        from myApp.models import Profile
        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.language = language
        profile.save()
    
    if changed:
        request.user.save(update_fields=['first_name', 'last_name', 'email'])
    
    return Response(user_payload(request.user), status=200)

@csrf_exempt
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def user_preferences(request):
    """Get user preferences"""
    from myApp.models import Profile
    profile, _ = Profile.objects.get_or_create(user=request.user)
    
    return Response({
        "defaultTone": "plain_clinical",  # Default tone
        "language": profile.language or "en-US",
        "notifications": {
            "enabled": True,
            "email": True,
            "push": False
        }
    }, status=200)

@csrf_exempt
@api_view(['PUT', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def user_preferences_update(request):
    """Update user preferences"""
    from myApp.models import Profile
    profile, _ = Profile.objects.get_or_create(user=request.user)
    
    default_tone = request.data.get("defaultTone", "plain_clinical")
    language = request.data.get("language", "en-US")
    
    if language:
        profile.language = language
        profile.save()
    
    return Response({
        "success": True,
        "preferences": {
            "defaultTone": default_tone,
            "language": profile.language or "en-US",
            "notifications": {
                "enabled": True,
                "email": True,
                "push": False
            }
        }
    }, status=200)

# ---- Chat endpoints ----
@csrf_exempt
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def chat_sessions(request):
    """
    Get user's chat sessions with messages.
    Returns array of sessions in iOS-expected format.
    """
    try:
        # Get all sessions (both archived and unarchived) for the user
        sessions = (
            ChatSession.objects
            .filter(user=request.user)
            .order_by("-updated_at")[:200]
        )
        
        # Filter out empty sessions (sessions with no messages)
        # Only include sessions that have at least one message
        filtered_sessions = [
            s for s in sessions 
            if s.messages and len(s.messages) > 0
        ]
        
        # Format for iOS
        formatted_sessions = [format_session_for_ios(s) for s in filtered_sessions]
        
        return Response(formatted_sessions, status=200)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({
            "error": str(e),
            "detail": "Failed to load sessions"
        }, status=500)

@csrf_exempt
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_chat_session(request):
    """
    Create a new chat session.
    iOS sends: {title, tone, lang}
    """
    title = request.data.get("title", "New Conversation")
    tone = request.data.get("tone", "PlainClinical")
    lang = request.data.get("lang", "en-US")
    
    # Normalize tone format (iOS might send "PlainClinical", backend uses "plain_clinical")
    tone_map = {
        "PlainClinical": "plain_clinical",
        "Clinical": "clinical",
        "Caregiver": "caregiver",
        "Faith": "faith"
    }
    normalized_tone = tone_map.get(tone, tone.lower().replace(" ", "_"))
    
    # Create session
    session = ChatSession.objects.create(
        user=request.user,
        title=title,
        tone=normalized_tone,
        lang=lang,
        messages=[]
    )
    
    return Response({
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "tone": tone,  # Return original tone format (PascalCase) as iOS expects
        "language": session.lang  # iOS spec uses "language" not "lang"
    }, status=201)

@csrf_exempt
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def send_chat(request):
    """
    Send a chat message.
    MUST accept both:
    1. application/json (text-only messages)
    2. multipart/form-data (messages with files)
    
    Returns message object in iOS-expected format.
    """
    try:
        # Check Content-Type and parse accordingly
        content_type = request.META.get('CONTENT_TYPE', '')
        
        if 'application/json' in content_type:
            # Format 1: JSON (text-only)
            try:
                if hasattr(request, 'body') and request.body:
                    data = json.loads(request.body)
                else:
                    data = request.data
                
                message = data.get('message', '').strip()
                tone = data.get('tone', 'plain_clinical')
                lang = data.get('lang', 'en-US')
                # Session ID in JSON is integer
                session_id = data.get('session_id')
                if session_id is not None:
                    try:
                        session_id = int(session_id)
                    except (ValueError, TypeError):
                        session_id = None
                care_setting = data.get('care_setting')
                faith_setting = data.get('faith_setting')
                files = []  # No files in JSON format
            except (json.JSONDecodeError, AttributeError):
                return Response({
                    "error": "Invalid JSON",
                    "detail": "Could not parse JSON body"
                }, status=400)
        elif 'multipart/form-data' in content_type or 'application/x-www-form-urlencoded' in content_type:
            # Format 2: Multipart (with or without files)
            message = request.data.get('message', '').strip()
            tone = request.data.get('tone', 'plain_clinical')
            lang = request.data.get('lang', 'en-US')
            # Session ID in multipart is string - convert to int
            session_id = request.data.get('session_id')
            if session_id:
                try:
                    session_id = int(session_id)
                except (ValueError, TypeError):
                    session_id = None
            care_setting = request.data.get('care_setting')
            faith_setting = request.data.get('faith_setting')
            files = request.FILES.getlist('files[]') if hasattr(request, 'FILES') else []
        else:
            # Try to parse as JSON if content type is missing
            try:
                if hasattr(request, 'body') and request.body:
                    data = json.loads(request.body)
                    message = data.get('message', '').strip()
                    tone = data.get('tone', 'plain_clinical')
                    lang = data.get('lang', 'en-US')
                    session_id = data.get('session_id')
                    care_setting = data.get('care_setting')
                    faith_setting = data.get('faith_setting')
                    files = []
                else:
                    return Response({
                        "detail": f"Unsupported media type \"{content_type}\" in request."
                    }, status=415)
            except (json.JSONDecodeError, AttributeError):
                return Response({
                    "detail": f"Unsupported media type \"{content_type}\" in request."
                }, status=415)
        
        # Validate required fields
        if not message and not files:
            return Response({
                "error": "Either 'message' or 'files[]' must be provided",
                "detail": "Message or files required"
            }, status=400)
        
        # Debug: log what we received
        print(f"DEBUG: Parsed message: '{message}' (length: {len(message)}, empty: {not message})")
        print(f"DEBUG: Files count: {len(files) if files else 0}")
        
        # Normalize tone format
        tone_map = {
            "PlainClinical": "plain_clinical",
            "Clinical": "clinical",
            "Caregiver": "caregiver",
            "Faith": "faith"
        }
        normalized_tone = tone_map.get(tone, tone.lower().replace(" ", "_"))
        
        # Create a NEW HttpRequest object from scratch instead of modifying the existing one
        # This avoids all the read-only attribute issues
        from django.http import HttpRequest, QueryDict
        from myApp.views import send_chat as real_send_chat
        
        # Get the underlying Django HttpRequest to access session
        django_request = request._request if hasattr(request, '_request') else request
        
        # Create a fresh HttpRequest with all necessary attributes
        new_request = HttpRequest()
        new_request.method = 'POST'
        new_request.user = request.user
        new_request.session = django_request.session  # Use session from underlying request
        new_request.META = django_request.META.copy() if hasattr(django_request, 'META') else {}
        
        # CRITICAL: Set content type to application/x-www-form-urlencoded
        # real_send_chat accepts both MultiPartParser and FormParser
        # Since we're setting POST directly (not a multipart body), use form-urlencoded
        # This allows FormParser to work without requiring multipart boundaries
        new_request.META['CONTENT_TYPE'] = 'application/x-www-form-urlencoded'
        new_request.META['HTTP_CONTENT_TYPE'] = 'application/x-www-form-urlencoded'
        
        # Set attributes that DRF expects
        # CRITICAL: DRF's FormParser reads from the body stream, not POST
        # So we need to encode our data as form-urlencoded in the body
        new_request._read_started = False
        new_request._stream = None
        if not hasattr(new_request, '_encoding'):
            new_request._encoding = 'utf-8'
        
        # Create QueryDict with our data
        chat_data = QueryDict(mutable=True)
        chat_data['message'] = message
        chat_data['tone'] = normalized_tone
        chat_data['lang'] = lang
        if session_id:
            chat_data['session_id'] = str(session_id)
        if care_setting:
            chat_data['care_setting'] = care_setting
        if faith_setting:
            chat_data['faith_setting'] = faith_setting
        chat_data._mutable = False
        
        # CRITICAL: DRF's FormParser reads from stream, not _body
        # We need to encode the form data and create a BytesIO stream for FormParser
        from urllib.parse import urlencode
        import io
        form_data = urlencode(chat_data, doseq=True)
        body_bytes = form_data.encode('utf-8')
        
        # Create a BytesIO stream for DRF's FormParser to read from
        body_stream = io.BytesIO(body_bytes)
        
        # Set both _body and _stream so DRF can read it
        new_request._body = body_bytes
        new_request._stream = body_stream
        new_request.META['CONTENT_LENGTH'] = str(len(body_bytes))
        
        # Reset stream position to beginning
        body_stream.seek(0)
        
        # Also set POST for compatibility
        new_request.POST = chat_data
        new_request._post = chat_data
        
        # Debug: verify everything is set
        print(f"DEBUG: Setting message in body: '{message}' (length: {len(message)})")
        print(f"DEBUG: Body length: {len(body_bytes)} bytes")
        print(f"DEBUG: Body preview: {body_bytes[:100]}")
        print(f"DEBUG: new_request.POST.get('message'): '{new_request.POST.get('message', 'NOT FOUND')}'")
        
        # Handle FILES - only if we have files
        if files:
            # Create a mock FILES object
            class MockFiles:
                def __init__(self, file_list):
                    self._files = file_list
                
                def getlist(self, key):
                    return self._files if key == 'files[]' else []
                
                def __contains__(self, key):
                    return key == 'files[]' or key == 'file'
            
            new_request.FILES = MockFiles(files)
        else:
            # Empty dict for FILES when no files
            new_request.FILES = {}
        
        # Debug: Check what DRF sees before calling real_send_chat
        # Wrap the request in DRF Request to see what it parses
        from rest_framework.request import Request
        from rest_framework.parsers import FormParser
        drf_request = Request(new_request, parsers=[FormParser()])
        print(f"DEBUG: DRF request.data before calling real_send_chat: {dict(drf_request.data)}")
        print(f"DEBUG: DRF request.data.get('message'): '{drf_request.data.get('message', 'NOT FOUND')}'")
        
        # Call the real send_chat function with the new request
        try:
            response = real_send_chat(new_request)
            
            # Parse the response - handle both JsonResponse and DRF Response
            response_data = {}
            if hasattr(response, 'render'):
                # It's a TemplateResponse - render it first
                response.render()
                import json as json_lib
                try:
                    response_data = json_lib.loads(response.content)
                except (json_lib.JSONDecodeError, AttributeError):
                    pass
            elif hasattr(response, 'content'):
                # It's a JsonResponse - content is bytes, need to decode
                import json as json_lib
                try:
                    content = response.content
                    if isinstance(content, bytes):
                        content = content.decode('utf-8')
                    response_data = json_lib.loads(content)
                except (json_lib.JSONDecodeError, AttributeError, TypeError) as e:
                    print(f"DEBUG: Failed to parse JsonResponse: {e}")
                    print(f"DEBUG: Content type: {type(response.content)}, Content: {response.content[:200] if hasattr(response.content, '__getitem__') else response.content}")
                    response_data = {}
            elif hasattr(response, 'data'):
                # It's a DRF Response object
                response_data = response.data if hasattr(response, 'data') else {}
            
            # Debug: print response structure to console
            print(f"DEBUG: Response type: {type(response)}")
            print(f"DEBUG: Response data: {response_data}")
            print(f"DEBUG: Response data keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'not a dict'}")
            
            # Extract the reply from the response
            # The real send_chat returns {"reply": "...", "session_id": ...}
            reply_text = response_data.get('reply', '')
            print(f"DEBUG: Extracted reply_text: {reply_text[:100] if reply_text else 'EMPTY'}")
            
            if not reply_text:
                # Try alternative field names
                reply_text = response_data.get('content', '') or response_data.get('summary', '') or response_data.get('message', '')
                print(f"DEBUG: After fallback, reply_text: {reply_text[:100] if reply_text else 'STILL EMPTY'}")
            
            if not reply_text:
                # If still no reply, this is an error - log it
                print(f"ERROR: No reply found in response. Response data: {response_data}")
                reply_text = "I apologize, but I'm having trouble processing your request right now. Please try again."
            
            # Get session_id from response or use the one we sent
            session_id_from_response = response_data.get('session_id')
            final_session_id = None
            if session_id_from_response is not None:
                try:
                    final_session_id = int(session_id_from_response)
                except (ValueError, TypeError):
                    pass
            elif session_id is not None:
                try:
                    final_session_id = int(session_id)
                except (ValueError, TypeError):
                    pass
            
            # Return in iOS-expected format (exactly as specified)
            now = timezone.now()
            timestamp = now.isoformat()
            return Response({
                "id": f"msg_{uuid.uuid4().hex[:12]}",
                "role": "assistant",
                "content": reply_text,
                "timestamp": timestamp,
                "session_id": final_session_id,
                "metadata": None
            }, status=200)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                "error": str(e),
                "detail": "Failed to process chat message"
            }, status=500)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({
            "error": str(e),
            "detail": "Failed to process chat message"
        }, status=500)

@csrf_exempt
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def summarize(request):
    """
    Summarize text or document.
    """
    text = request.data.get("text", "")
    summary = text[:200] + ("…" if len(text) > 200 else "")
    return Response({"summary": summary}, status=200)

# ---- Tone Management ----
@csrf_exempt
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def tones(request):
    """
    Get available AI tones.
    GET /api/tones/
    Returns list of available tones with descriptions.
    """
    return Response({
        "tones": [
            {
                "id": "plain_clinical",
                "displayName": "Plain Clinical",
                "description": "Clear & simple explanation.",
                "iconName": "heart.text.square.fill",
                "isAvailable": True,
                "order": 1
            },
            {
                "id": "caregiver",
                "displayName": "Caregiver",
                "description": "With care and understanding.",
                "iconName": "person.2.fill",
                "isAvailable": True,
                "order": 2
            },
            {
                "id": "faith",
                "displayName": "Faith",
                "description": "With comfort and hope.",
                "iconName": "cross.fill",
                "isAvailable": True,
                "order": 3
            },
            {
                "id": "clinical",
                "displayName": "Clinical",
                "description": "Structured SOAP notes for healthcare professionals.",
                "iconName": "stethoscope",
                "isAvailable": True,
                "order": 4
            },
            {
                "id": "geriatric",
                "displayName": "Geriatric",
                "description": "Elderly care focused.",
                "iconName": "person.crop.circle.fill",
                "isAvailable": True,
                "order": 5
            },
            {
                "id": "emotional_support",
                "displayName": "Emotional Support",
                "description": "Emotional support mode.",
                "iconName": "heart.fill",
                "isAvailable": True,
                "order": 6
            }
        ],
        "defaultTone": "plain_clinical"
    }, status=200)

@csrf_exempt
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def tone_detail(request, tone_id):
    """
    Get tone detail.
    GET /api/tones/{tone_id}/
    """
    tones_data = {
        "plain_clinical": {
            "id": "plain_clinical",
            "displayName": "Plain Clinical",
            "description": "Clear & simple explanation.",
            "iconName": "heart.text.square.fill",
            "isAvailable": True,
            "order": 1
        },
        "caregiver": {
            "id": "caregiver",
            "displayName": "Caregiver",
            "description": "With care and understanding.",
            "iconName": "person.2.fill",
            "isAvailable": True,
            "order": 2
        },
        "faith": {
            "id": "faith",
            "displayName": "Faith",
            "description": "With comfort and hope.",
            "iconName": "cross.fill",
            "isAvailable": True,
            "order": 3
        },
        "clinical": {
            "id": "clinical",
            "displayName": "Clinical",
            "description": "Structured SOAP notes for healthcare professionals.",
            "iconName": "stethoscope",
            "isAvailable": True,
            "order": 4
        },
        "geriatric": {
            "id": "geriatric",
            "displayName": "Geriatric",
            "description": "Elderly care focused.",
            "iconName": "person.crop.circle.fill",
            "isAvailable": True,
            "order": 5
        },
        "emotional_support": {
            "id": "emotional_support",
            "displayName": "Emotional Support",
            "description": "Emotional support mode.",
            "iconName": "heart.fill",
            "isAvailable": True,
            "order": 6
        }
    }
    
    tone_data = tones_data.get(tone_id)
    if not tone_data:
        return Response({
            "error": "Tone not found",
            "detail": f"Tone '{tone_id}' does not exist"
        }, status=404)
    
    return Response(tone_data, status=200)

# ---- App Configuration ----
@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def config(request):
    """
    Get API configuration (public endpoint).
    GET /api/config/
    Returns basic configuration info the app might need.
    """
    from django.conf import settings
    base_url = request.build_absolute_uri('/api/').rstrip('/')
    
    return Response({
        "api": {
            "baseUrl": base_url,
            "version": "v1",
            "timeout": 30
        },
        "features": {
            "voiceMode": True,
            "imageUpload": True,
            "exportData": True,
            "darkMode": True
        },
        "legal": {
            "privacyPolicyUrl": f"{request.build_absolute_uri('/')}legal/#privacy",
            "termsOfServiceUrl": f"{request.build_absolute_uri('/')}legal/#terms",
            "supportEmail": "support@neuromedai.org"
        },
        "ui": {
            "minimumAppVersion": "1.0.0",
            "forceUpdate": False,
            "maintenanceMode": False
        },
        "languages": [
            {
                "code": "en-US",
                "displayName": "English",
                "isAvailable": True
            },
            {
                "code": "es-ES",
                "displayName": "Spanish",
                "isAvailable": True
            },
            {
                "code": "fr-FR",
                "displayName": "French",
                "isAvailable": True
            },
            {
                "code": "de-DE",
                "displayName": "German",
                "isAvailable": True
            }
        ]
    }, status=200)

# ---- Clear Chat Session ----
@csrf_exempt
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def clear_session(request):
    """
    Clear chat session.
    POST /api/chat/clear-session/
    """
    session_id = request.data.get("session_id")
    
    if session_id:
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
            session.messages = []
            session.save()
        except ChatSession.DoesNotExist:
            return Response({
                "error": "Session not found",
                "detail": f"Session {session_id} does not exist"
            }, status=404)
    
    # Also clear server-sticky session
    request.session.pop("active_chat_session_id", None)
    request.session.modified = True
    
    return Response({"ok": True}, status=200)
