# 🔗 Backend-Frontend Integration Guide

**Date:** January 7, 2026  
**Purpose:** Complete documentation of how the Django backend connects to the iOS frontend  
**Status:** ✅ **FULLY INTEGRATED**

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Authentication Flow](#authentication-flow)
3. [Chat Message Flow](#chat-message-flow)
4. [Session Management](#session-management)
5. [Data Format Specifications](#data-format-specifications)
6. [Key Implementation Details](#key-implementation-details)
7. [Troubleshooting](#troubleshooting)

---

## 🏗️ Architecture Overview

### System Components

```
iOS App (Swift)
    ↓ HTTP Requests (JSON/Multipart)
    ↓ Authorization: Token <token>
Django Backend (Python)
    ├── mobile_api/views.py (iOS-specific endpoints)
    ├── myApp/views.py (Core business logic)
    └── OpenAI API (AI responses)
    ↓ HTTP Responses (JSON)
    ↓ Status: 200 OK
iOS App (Swift)
```

### Key Files

**Backend:**
- `mobile_api/views.py` - iOS API endpoints (wrapper/adapter layer)
- `mobile_api/urls.py` - URL routing for mobile API
- `myProject/urls.py` - Main URL configuration (prioritizes mobile_api routes)
- `myApp/views.py` - Core chat logic (used by mobile_api)

**Frontend (iOS):**
- `ChatService.swift` - Network service for API calls
- `NetworkService.swift` - HTTP request/response handling
- `ChatConversationView.swift` - UI for chat interface

---

## 🔐 Authentication Flow

### 1. User Login

**iOS App → Backend:**

```http
POST /api/login/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**Backend Processing (`mobile_api/views.py`):**

```python
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    email = (request.data.get("email") or "").lower()
    password = request.data.get("password") or ""
    
    # Authenticate user
    user = authenticate(request, username=email, password=password)
    
    # Generate token
    from rest_framework.authtoken.models import Token
    token, _ = Token.objects.get_or_create(user=user)
    
    # Return user data + token
    return Response({
        **user_payload(user),
        "token": token.key
    }, status=200)
```

**Backend → iOS App:**

```json
{
  "id": 1,
  "username": "johndoe",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "date_joined": "2025-07-30T17:42:33.835913+00:00",
  "last_login": "2025-12-23T16:13:34.883308+00:00",
  "token": "659cc7fdf89da1a611c61e95689fb6e4a3b6213f"
}
```

**iOS App Processing:**

1. Receives response
2. Extracts `token` field
3. Stores token in secure storage (Keychain)
4. Uses token for all subsequent authenticated requests

### 2. Authenticated Requests

**iOS App → Backend:**

```http
GET /api/chat/sessions/
Authorization: Token 659cc7fdf89da1a611c61e95689fb6e4a3b6213f
```

**Backend Processing:**

```python
@csrf_exempt
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def chat_sessions(request):
    # TokenAuthentication automatically validates the token
    # request.user is set to the authenticated user
    sessions = ChatSession.objects.filter(user=request.user)
    return Response(format_sessions_for_ios(sessions), status=200)
```

**Key Points:**
- Token is sent in `Authorization: Token <token>` header
- DRF's `TokenAuthentication` validates the token
- `request.user` is automatically set to the authenticated user
- All authenticated endpoints use `@permission_classes([IsAuthenticated])`

---

## 💬 Chat Message Flow

### Complete Flow Diagram

```
User Types Message in iOS App
    ↓
ChatConversationView.sendMessage()
    ↓
ChatService.sendChat()
    ↓
NetworkService.post() (JSON) or postMultipart() (with files)
    ↓
HTTP POST /api/send-chat/
    Authorization: Token <token>
    Content-Type: application/json
    ↓
mobile_api/views.py → send_chat()
    ├── Parses JSON request
    ├── Extracts: message, tone, lang, session_id
    ├── Creates new HttpRequest with form data
    ├── Calls myApp/views.py → send_chat()
    │   ├── Processes message
    │   ├── Calls OpenAI API
    │   └── Returns JsonResponse({"reply": "...", "session_id": ...})
    ├── Extracts reply from response
    └── Formats for iOS
    ↓
HTTP Response
    Status: 200 OK
    Content-Type: application/json
    {
      "id": "msg_abc123",
      "role": "assistant",
      "content": "AI response here...",
      "timestamp": "2026-01-07T12:00:00.123456+00:00",
      "session_id": 288,
      "metadata": null
    }
    ↓
NetworkService decodes JSON
    ↓
ChatMessageResponse.toChatMessage()
    ↓
ChatMessage added to messages array
    ↓
UI updates (MessageBubble rendered)
    ↓
User sees AI response in chat
```

### Step-by-Step: Sending a Chat Message

#### Step 1: iOS App Sends Request

**Location:** `ChatService.swift` → `sendChat()`

```swift
let response = try await NetworkService.shared.post(
    endpoint: "/api/send-chat/",
    body: [
        "message": text,
        "tone": currentTone.rawValue,  // e.g., "plain_clinical"
        "lang": "en-US",
        "session_id": sessionId
    ],
    headers: ["Authorization": "Token \(token)"]
)
```

**HTTP Request:**

```http
POST /api/send-chat/ HTTP/1.1
Authorization: Token 659cc7fdf89da1a611c61e95689fb6e4a3b6213f
Content-Type: application/json

{
  "message": "What are the symptoms of diabetes?",
  "tone": "plain_clinical",
  "lang": "en-US",
  "session_id": 288
}
```

#### Step 2: Backend Receives Request

**Location:** `mobile_api/views.py` → `send_chat()`

```python
@csrf_exempt
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def send_chat(request):
    # Parse JSON request
    if 'application/json' in content_type:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        tone = data.get('tone', 'plain_clinical')
        lang = data.get('lang', 'en-US')
        session_id = data.get('session_id')
        files = []
```

#### Step 3: Convert to Form Data for Core Logic

**Problem:** `myApp/views.py` → `send_chat()` only accepts `multipart/form-data` (via `@parser_classes([MultiPartParser, FormParser])`)

**Solution:** Convert JSON data to form-urlencoded body

```python
# Create QueryDict with our data
chat_data = QueryDict(mutable=True)
chat_data['message'] = message
chat_data['tone'] = normalized_tone  # Convert to PascalCase if needed
chat_data['lang'] = lang
if session_id:
    chat_data['session_id'] = str(session_id)

# Encode as form-urlencoded
from urllib.parse import urlencode
import io
form_data = urlencode(chat_data, doseq=True)
body_bytes = form_data.encode('utf-8')

# Create BytesIO stream for DRF's FormParser
body_stream = io.BytesIO(body_bytes)

# Create new HttpRequest with form data
new_request = HttpRequest()
new_request.method = 'POST'
new_request.user = request.user
new_request.session = django_request.session
new_request.META['CONTENT_TYPE'] = 'application/x-www-form-urlencoded'
new_request._body = body_bytes
new_request._stream = body_stream
new_request.POST = chat_data
new_request._post = chat_data
```

#### Step 4: Call Core Chat Logic

**Location:** `myApp/views.py` → `send_chat()`

```python
# This function:
# 1. Processes the message
# 2. Builds chat history
# 3. Calls OpenAI API
reply = client.chat.completions.create(
    model="gpt-4o",
    temperature=0.5,
    messages=chat_history,
).choices[0].message.content.strip()

# Returns JsonResponse
return JsonResponse({
    "reply": reply,
    "session_id": session_obj.id
}, status=200)
```

#### Step 5: Format Response for iOS

**Location:** `mobile_api/views.py` → `send_chat()`

```python
# Parse response from real_send_chat
response_data = json.loads(response.content)
reply_text = response_data.get('reply', '')

# Format in iOS-expected format
return Response({
    "id": f"msg_{uuid.uuid4().hex[:12]}",
    "role": "assistant",
    "content": reply_text,
    "timestamp": timezone.now().isoformat(),
    "session_id": int(session_id_from_response) if session_id_from_response else None,
    "metadata": None
}, status=200)
```

#### Step 6: iOS App Receives Response

**Location:** `ChatService.swift` → `sendChat()`

```swift
// Response is decoded as ChatMessageResponse
struct ChatMessageResponse: Codable {
    let id: String
    let role: String
    let content: String
    let timestamp: String
    let sessionId: Int?
    let metadata: String?
}

// Convert to ChatMessage for display
func toChatMessage() -> ChatMessage? {
    return ChatMessage(
        id: id,
        content: content,
        isUser: role == "user",
        timestamp: ISO8601DateFormatter().date(from: timestamp) ?? Date()
    )
}
```

#### Step 7: Display in UI

**Location:** `ChatConversationView.swift`

```swift
// Add AI response to messages array
if let aiResponse = response.toChatMessage() {
    messages.append(aiResponse)
    // UI automatically updates via @Published property
}
```

---

## 📚 Session Management

### Creating a New Session

**iOS App → Backend:**

```http
POST /api/chat/sessions/new/
Authorization: Token <token>
Content-Type: application/json

{
  "title": "New Conversation",
  "tone": "PlainClinical",
  "lang": "en-US"
}
```

**Backend Processing:**

```python
@csrf_exempt
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_chat_session(request):
    title = request.data.get('title', 'New Conversation')
    tone = request.data.get('tone', 'PlainClinical')
    lang = request.data.get('lang', 'en-US')
    
    # Normalize tone (PascalCase → snake_case for storage)
    normalized_tone = _pascal_to_snake_case(tone)
    
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
        "tone": tone,  # Return original format
        "language": session.lang
    }, status=201)
```

### Getting All Sessions

**iOS App → Backend:**

```http
GET /api/chat/sessions/
Authorization: Token <token>
```

**Backend Processing:**

```python
@csrf_exempt
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def chat_sessions(request):
    sessions = ChatSession.objects.filter(
        user=request.user
    ).order_by("-updated_at")[:200]
    
    # Format each session with messages
    formatted_sessions = []
    for session in sessions:
        formatted_sessions.append(format_session_for_ios(session))
    
    return Response(formatted_sessions, status=200)
```

**Response Format:**

```json
[
  {
    "id": 288,
    "title": "Health Check Discussion",
    "created_at": "2026-01-07T12:00:00.000000+00:00",
    "updated_at": "2026-01-07T12:05:00.000000+00:00",
    "tone": "plain_clinical",
    "lang": "en-US",
    "messages": [
      {
        "id": "msg_abc123",
        "role": "user",
        "content": "What are the symptoms of diabetes?",
        "timestamp": "2026-01-07T12:00:00.000000+00:00",
        "session_id": 288,
        "metadata": null
      },
      {
        "id": "msg_def456",
        "role": "assistant",
        "content": "Diabetes symptoms include...",
        "timestamp": "2026-01-07T12:00:05.000000+00:00",
        "session_id": 288,
        "metadata": null
      }
    ]
  }
]
```

---

## 📊 Data Format Specifications

### Request Formats

#### 1. JSON (Text-Only Messages)

```http
POST /api/send-chat/
Content-Type: application/json

{
  "message": "What are the symptoms of diabetes?",
  "tone": "plain_clinical",
  "lang": "en-US",
  "session_id": 288
}
```

#### 2. Multipart (Messages with Files)

```http
POST /api/send-chat/
Content-Type: multipart/form-data

message: "Please analyze this image"
tone: "plain_clinical"
lang: "en-US"
session_id: "288"
files[]: [binary file data]
```

### Response Formats

#### Success Response

```json
{
  "id": "msg_abc123def456",
  "role": "assistant",
  "content": "AI response text here...",
  "timestamp": "2026-01-07T12:00:00.123456+00:00",
  "session_id": 288,
  "metadata": null
}
```

#### Error Response

```json
{
  "error": "Error type",
  "message": "Human-readable error message",
  "detail": "Detailed error information"
}
```

### Field Naming Conventions

**Backend → Frontend:**
- All fields in **snake_case**: `first_name`, `last_name`, `date_joined`, `session_id`
- Dates in **ISO 8601 format**: `"2026-01-07T12:00:00.123456+00:00"`
- Tones in **snake_case**: `"plain_clinical"`, `"caregiver"`, `"faith"`

**Frontend → Backend:**
- Tones can be **PascalCase** in requests: `"PlainClinical"` (converted to snake_case internally)
- Session ID as **integer** (JSON) or **string** (multipart, converted to int)

---

## 🔧 Key Implementation Details

### 1. URL Routing Priority

**File:** `myProject/urls.py`

```python
# CRITICAL: mobile_api routes MUST be before myApp routes
# Django processes URLs in order, first match wins

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # iOS/Mobile API routes - Processed FIRST
    path('api/login/', mobile_views.login, name='mobile_api_login'),
    path('api/signup/', mobile_views.signup, name='mobile_api_signup'),
    path('api/send-chat/', mobile_views.send_chat, name='mobile_api_send_chat'),
    # ... all other mobile_api routes ...
    
    # Main app routes (processed AFTER mobile_api routes)
    path('', include("myApp.urls")),
]
```

**Why:** Ensures iOS app hits the correct endpoints, not the web app endpoints.

### 2. Token Authentication

**File:** `myProject/settings.py`

```python
INSTALLED_APPS = [
    # ...
    'rest_framework',
    'rest_framework.authtoken',  # Required for token auth
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ]
}
```

**How it works:**
1. User logs in → Backend generates token
2. Token stored in database (`authtoken_token` table)
3. iOS app sends token in `Authorization: Token <token>` header
4. DRF's `TokenAuthentication` validates token
5. `request.user` is automatically set to authenticated user

### 3. Request Format Conversion

**Problem:** iOS sends JSON, but `myApp/views.py` → `send_chat()` only accepts multipart/form-data

**Solution:** Convert JSON to form-urlencoded body

```python
# Step 1: Parse JSON from iOS
data = json.loads(request.body)
message = data.get('message')

# Step 2: Create QueryDict
chat_data = QueryDict(mutable=True)
chat_data['message'] = message
chat_data['tone'] = normalized_tone
# ...

# Step 3: Encode as form-urlencoded
form_data = urlencode(chat_data, doseq=True)
body_bytes = form_data.encode('utf-8')

# Step 4: Create BytesIO stream for DRF
body_stream = io.BytesIO(body_bytes)

# Step 5: Create new HttpRequest with form data
new_request = HttpRequest()
new_request._body = body_bytes
new_request._stream = body_stream
new_request.POST = chat_data
new_request.META['CONTENT_TYPE'] = 'application/x-www-form-urlencoded'

# Step 6: Call core logic
response = real_send_chat(new_request)
```

**Why this works:**
- DRF's `FormParser` reads from the `stream` property
- We create a `BytesIO` stream with the form data
- FormParser parses it into `request.data`
- Core logic can access `request.data.get("message")`

### 4. Response Format Transformation

**Problem:** Core logic returns `{"reply": "...", "session_id": ...}`, but iOS expects `{"id": "...", "role": "assistant", "content": "...", ...}`

**Solution:** Transform response in `mobile_api/views.py`

```python
# Extract reply from core logic response
response_data = json.loads(response.content)
reply_text = response_data.get('reply', '')

# Transform to iOS format
return Response({
    "id": f"msg_{uuid.uuid4().hex[:12]}",
    "role": "assistant",
    "content": reply_text,
    "timestamp": timezone.now().isoformat(),
    "session_id": int(session_id_from_response) if session_id_from_response else None,
    "metadata": None
}, status=200)
```

### 5. Tone Format Conversion

**Problem:** iOS sends tones in different formats (PascalCase, snake_case)

**Solution:** Normalize in `mobile_api/views.py`

```python
def _pascal_to_snake_case(tone: str) -> str:
    """Convert PascalCase to snake_case"""
    if not tone:
        return "plain_clinical"
    result = []
    for i, char in enumerate(tone):
        if char.isupper() and i > 0:
            result.append('_')
        result.append(char.lower())
    return ''.join(result)

# Usage
normalized_tone = _pascal_to_snake_case(tone)  # "PlainClinical" → "plain_clinical"
```

**Storage:** Tones stored in database as snake_case  
**API Response:** Tones returned as snake_case  
**API Request:** Accepts both PascalCase and snake_case (converted internally)

---

## 🐛 Troubleshooting

### Issue 1: "Authentication credentials were not provided" (403)

**Cause:** Token not being sent or validated

**Check:**
1. iOS app is sending `Authorization: Token <token>` header
2. Token exists in database: `Token.objects.filter(key=token).exists()`
3. Token is valid (not expired)
4. Endpoint has `@authentication_classes([TokenAuthentication])`

**Fix:**
- Verify token is stored correctly after login
- Check iOS app is including token in headers
- Ensure `rest_framework.authtoken` is in `INSTALLED_APPS`

### Issue 2: "Unsupported media type" (415)

**Cause:** Backend rejecting JSON requests

**Check:**
1. Endpoint has `@parser_classes([JSONParser, MultiPartParser, FormParser])`
2. Content-Type header is correct
3. Request body is valid JSON

**Fix:**
- Add `JSONParser` to `@parser_classes` decorator
- Verify iOS app is sending correct `Content-Type` header

### Issue 3: "Hmm… I didn't catch that" Response

**Cause:** Message not reaching core logic

**Check:**
1. Message is being parsed from JSON request
2. Message is being set in form data body
3. DRF's FormParser is reading the body correctly
4. Core logic can access `request.data.get("message")`

**Debug:**
```python
# Add debug statements
print(f"DEBUG: Parsed message: '{message}'")
print(f"DEBUG: Body: {body_bytes}")
print(f"DEBUG: DRF request.data: {drf_request.data}")
```

**Fix:**
- Ensure body is encoded as form-urlencoded
- Create BytesIO stream from body bytes
- Set `_stream` property on HttpRequest
- Verify CONTENT_TYPE is `application/x-www-form-urlencoded`

### Issue 4: Wrong Response Format

**Cause:** Response not matching iOS expectations

**Check:**
1. Response has all required fields: `id`, `role`, `content`, `timestamp`, `session_id`, `metadata`
2. Field names are in snake_case
3. Dates are in ISO 8601 format
4. `role` is "assistant" for AI responses

**Fix:**
- Use `format_message_for_ios()` helper function
- Ensure all fields are present
- Convert dates to ISO 8601: `timezone.now().isoformat()`

### Issue 5: Session Not Found

**Cause:** Session ID mismatch or session doesn't exist

**Check:**
1. Session ID is being sent correctly
2. Session belongs to authenticated user
3. Session exists in database

**Fix:**
- Verify session_id is integer (not string)
- Check session ownership: `ChatSession.objects.filter(id=session_id, user=request.user)`
- Create new session if session_id is None

---

## ✅ Integration Checklist

### Authentication
- [x] Login returns token
- [x] Signup returns token
- [x] Token stored securely in iOS app
- [x] Token sent in `Authorization: Token <token>` header
- [x] All authenticated endpoints validate token
- [x] 401 returned for invalid/missing token

### Chat Messages
- [x] Accepts JSON for text-only messages
- [x] Accepts multipart for messages with files
- [x] Converts JSON to form data for core logic
- [x] Calls OpenAI API correctly
- [x] Returns iOS-expected format
- [x] All required fields present
- [x] Proper error handling

### Session Management
- [x] Creates new sessions
- [x] Returns all sessions with messages
- [x] Formats sessions correctly
- [x] Converts tones to snake_case
- [x] Includes message history

### Data Formats
- [x] All dates in ISO 8601 format
- [x] All field names in snake_case
- [x] Tones normalized correctly
- [x] Session IDs as integers
- [x] JSON responses (not HTML)

---

## 📝 Summary

### How It All Connects

1. **Authentication:**
   - iOS app sends credentials → Backend validates → Returns token
   - Token stored in iOS Keychain
   - Token sent in all subsequent requests

2. **Chat Messages:**
   - iOS app sends JSON request → `mobile_api/views.py` receives it
   - Converts JSON to form data → Creates new HttpRequest
   - Calls `myApp/views.py` → `send_chat()` (core logic)
   - Core logic calls OpenAI → Returns AI response
   - `mobile_api/views.py` formats response → Returns to iOS
   - iOS app displays response in chat UI

3. **Session Management:**
   - iOS app creates session → Backend stores in database
   - iOS app sends messages with session_id → Backend links to session
   - iOS app requests sessions → Backend returns with message history
   - All formatted for iOS consumption

### Key Design Decisions

1. **Wrapper Pattern:** `mobile_api/views.py` acts as adapter between iOS and core logic
2. **Format Conversion:** JSON → Form Data → Core Logic → iOS Format
3. **Token Authentication:** Secure, stateless authentication for mobile
4. **URL Routing Priority:** Mobile API routes processed first to avoid conflicts
5. **Response Transformation:** Core logic format → iOS-expected format

---

## 🔗 Related Files

- `mobile_api/views.py` - iOS API endpoints
- `mobile_api/urls.py` - URL routing
- `myProject/urls.py` - Main URL configuration
- `myApp/views.py` - Core chat logic
- `myProject/settings.py` - DRF configuration

---

**Last Updated:** January 7, 2026  
**Status:** ✅ Production Ready

