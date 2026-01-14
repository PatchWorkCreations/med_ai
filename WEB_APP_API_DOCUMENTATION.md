# Web App API Functions Documentation

This document details all the API endpoints and functions required for the web application (`myApp`). These functions are separate from the mobile API (`mobile_api`) and use session-based authentication.

---

## Table of Contents

1. [Authentication & User Management](#authentication--user-management)
2. [Chat & Sessions](#chat--sessions)
3. [User Settings](#user-settings)
4. [Analytics & Tracking](#analytics--tracking)
5. [Utility Functions](#utility-functions)

---

## Authentication & User Management

### 1. `api_login`
**Endpoint:** `POST /api/login/`  
**Function:** `views.api_login`  
**Authentication:** None (public endpoint)  
**Request Format:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```
**Response Format:**
```json
{
  "success": true,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  },
  "token": "optional_token_if_needed"
}
```
**Description:** Authenticates a user and returns user information. Uses Django session authentication.

---

### 2. `auth_status`
**Endpoint:** `GET /api/auth/status/`  
**Function:** `views.auth_status`  
**Authentication:** Session-based (checks if user is logged in)  
**Request Format:** None (GET request)  
**Response Format:**
```json
{
  "authenticated": true,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```
**Description:** Checks if the current user is authenticated via session.

---

### 3. `get_csrf_token`
**Endpoint:** `GET /api/csrf/`  
**Function:** `views.get_csrf_token`  
**Authentication:** None  
**Request Format:** None (GET request)  
**Response Format:**
```json
{
  "csrf_token": "token_value"
}
```
**Description:** Returns the CSRF token for the current session.

---

### 4. `signup_view`
**Endpoint:** `POST /signup/`  
**Function:** `views.signup_view`  
**Authentication:** None (public endpoint)  
**Request Format:** Form data or JSON
```json
{
  "email": "user@example.com",
  "password": "password123",
  "first_name": "John",
  "last_name": "Doe"
}
```
**Response Format:** Redirects to dashboard on success, or returns error JSON
**Description:** Creates a new user account.

---

### 5. `logout_view`
**Endpoint:** `POST /logout/`  
**Function:** `views.logout_view`  
**Authentication:** Session-based  
**Request Format:** None (POST request)  
**Response Format:** Redirects to home page  
**Description:** Logs out the current user and clears session.

---

## Chat & Sessions

### 6. `send_chat`
**Endpoint:** `POST /api/send-chat/` or `POST /send-chat/` or `POST /api/send_chat/`  
**Function:** `views.send_chat`  
**Authentication:** `@permission_classes([AllowAny])` - Works for both authenticated and unauthenticated users  
**Request Format:** `multipart/form-data` or `application/x-www-form-urlencoded`
```
message: "User's message text"
tone: "PlainClinical" | "Clinical" | "Caregiver" | "Faith"
lang: "en-US" (ISO language code)
care_setting: "hospital" | "home" | "clinic" (optional, for Clinical/Caregiver tones)
faith_setting: "general" | "catholic" | "protestant" | etc. (optional, for Faith tone)
session_id: 123 (optional, integer)
files[]: [File objects] (optional, multiple files allowed)
```
**Response Format:**
```json
{
  "reply": "AI-generated response text",
  "session_id": 123
}
```
**Description:** Sends a chat message to the AI and returns the response. Handles file uploads (PDFs, images, DOCX). Creates or updates chat sessions automatically.

---

### 7. `list_chat_sessions`
**Endpoint:** `GET /api/chat/sessions/`  
**Function:** `api_chat.list_chat_sessions`  
**Authentication:** `@permission_classes([IsAuthenticated])` with `SessionAuthentication`  
**Request Format:** None (GET request)  
**Response Format:**
```json
[
  {
    "id": 123,
    "title": "Chat Title",
    "tone": "plain_clinical",
    "lang": "en-US",
    "archived": false,
    "created_at": "2025-01-08T12:00:00Z",
    "updated_at": "2025-01-08T12:30:00Z",
    "message_count": 5,
    "messages": [
      {
        "id": "msg_abc123",
        "role": "user",
        "content": "Hello",
        "timestamp": "2025-01-08T12:00:00Z",
        "session_id": 123,
        "metadata": null
      },
      {
        "id": "msg_def456",
        "role": "assistant",
        "content": "Hi there!",
        "timestamp": "2025-01-08T12:00:05Z",
        "session_id": 123,
        "metadata": null
      }
    ]
  }
]
```
**Description:** Returns up to 200 most recent chat sessions for the authenticated user. Includes messages array with transformed message format. Excludes empty sessions (sessions with no messages).

---

### 8. `get_chat_session`
**Endpoint:** `GET /api/chat/sessions/<session_id>/`  
**Function:** `api_chat.get_chat_session`  
**Authentication:** `@login_required`  
**Request Format:** None (GET request with session_id in URL)  
**Response Format:**
```json
{
  "id": 123,
  "title": "Chat Title",
  "tone": "plain_clinical",
  "lang": "en-US",
  "archived": false,
  "created_at": "2025-01-08T12:00:00Z",
  "updated_at": "2025-01-08T12:30:00Z",
  "message_count": 5,
  "messages": [
    {
      "role": "user",
      "content": "Hello",
      "ts": "2025-01-08T12:00:00Z",
      "meta": null
    }
  ]
}
```
**Description:** Returns a specific chat session with full message history.

---

### 9. `create_chat_session`
**Endpoint:** `POST /api/chat/sessions/new/`  
**Function:** `views.create_chat_session`  
**Authentication:** `@permission_classes([IsAuthenticated])`  
**Request Format:** None (POST request, optional JSON body)  
**Response Format:**
```json
{
  "session_id": 123
}
```
**Description:** Creates a new empty chat session and makes it the active session. Stores session_id in `request.session["active_chat_session_id"]`.

---

### 10. `chat_session_rename`
**Endpoint:** `POST /api/chat/sessions/<pk>/rename/`  
**Function:** `views.chat_session_rename`  
**Authentication:** `@permission_classes([IsAuthenticated])`  
**Request Format:**
```json
{
  "title": "New Chat Title"
}
```
**Response Format:**
```json
{
  "success": true,
  "title": "New Chat Title"
}
```
**Description:** Renames a chat session. Only works for sessions owned by the authenticated user.

---

### 11. `chat_session_archive`
**Endpoint:** `POST /api/chat/sessions/<pk>/archive/`  
**Function:** `views.chat_session_archive`  
**Authentication:** `@permission_classes([IsAuthenticated])`  
**Request Format:** None (POST request)  
**Response Format:**
```json
{
  "success": true,
  "archived": true
}
```
**Description:** Toggles the archived status of a chat session. Only works for sessions owned by the authenticated user.

---

### 12. `chat_session_delete`
**Endpoint:** `POST /api/chat/sessions/<pk>/delete/`  
**Function:** `views.chat_session_delete`  
**Authentication:** `@permission_classes([IsAuthenticated])`  
**Request Format:** None (POST request)  
**Response Format:**
```json
{
  "success": true
}
```
**Description:** Permanently deletes a chat session. Only works for sessions owned by the authenticated user.

---

### 13. `clear_session`
**Endpoint:** `POST /clear-session/`  
**Function:** `views.clear_session`  
**Authentication:** `@permission_classes([AllowAny])`  
**Request Format:** None (POST request)  
**Response Format:**
```json
{
  "ok": true
}
```
**Description:** Clears the active chat session from the server-side session storage. Used for guest users.

---

## User Settings

### 14. `get_user_settings`
**Endpoint:** `GET /api/user/settings/`  
**Function:** `views.get_user_settings`  
**Authentication:** `@login_required`  
**Request Format:** None (GET request)  
**Response Format:**
```json
{
  "display_name": "John Doe",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "profession": "Doctor",
  "language": "en-US"
}
```
**Description:** Returns the current user's settings and profile information. Constructs full_name from first_name + last_name, with fallbacks to display_name or username.

---

### 15. `update_user_settings`
**Endpoint:** `POST /api/user/settings/update/`  
**Function:** `views.update_user_settings`  
**Authentication:** `@login_required`  
**Request Format:**
```json
{
  "display_name": "John Doe",
  "first_name": "John",
  "last_name": "Doe",
  "email": "user@example.com",
  "profession": "Doctor",
  "language": "en-US",
  "appearance": "light",
  "accent_color": "#236092",
  "spoken_language": "en-US",
  "voice": "default",
  "separate_voice_mode": false,
  "show_additional_models": false,
  "personalization": {
    "base_style_tone": "PlainClinical",
    "characteristic_warm": true,
    "characteristic_enthusiastic": false,
    "characteristic_headers": true,
    "characteristic_emoji": false,
    "custom_instructions": "Custom instructions text",
    "nickname": "Johnny",
    "occupation": "Physician",
    "more_about_you": "Additional info",
    "reference_saved_memories": true,
    "reference_chat_history": true
  }
}
```
**Response Format:**
```json
{
  "success": true,
  "message": "Settings updated successfully"
}
```
**Description:** Updates user settings and profile information. Supports partial updates (only send fields that need to be changed).

---

## Analytics & Tracking

### 16. `track_event`
**Endpoint:** `POST /api/track`  
**Function:** `views.track_event`  
**Authentication:** None (public endpoint)  
**Request Format:**
```json
{
  "event": "button_click",
  "properties": {
    "button_name": "upload_file",
    "page": "dashboard"
  }
}
```
**Response Format:**
```json
{
  "success": true
}
```
**Description:** Tracks analytics events. Returns 204 No Content on success.

---

## Utility Functions

### 17. `summarize_medical_record`
**Endpoint:** `POST /api/summarize/`  
**Function:** `views.summarize_medical_record`  
**Authentication:** `@permission_classes([IsAuthenticated])`  
**Request Format:** `multipart/form-data`
```
file: [File object] (PDF, DOCX, or image)
tone: "PlainClinical" | "Clinical" | "Caregiver" | "Faith" (optional)
lang: "en-US" (optional)
```
**Response Format:**
```json
{
  "summary": "Extracted and summarized medical record text...",
  "session_id": 123
}
```
**Description:** Summarizes a medical record file (PDF, DOCX, or image). Creates a chat session automatically.

---

### 18. `smart_suggestions`
**Endpoint:** `POST /api/smart-suggestions/`  
**Function:** `views.smart_suggestions`  
**Authentication:** `@permission_classes([AllowAny])`  
**Request Format:**
```json
{
  "context": "User's current context or message",
  "session_id": 123 (optional)
}
```
**Response Format:**
```json
{
  "suggestions": [
    "Suggestion 1",
    "Suggestion 2",
    "Suggestion 3"
  ]
}
```
**Description:** Returns smart suggestions based on context.

---

### 19. `answer_question`
**Endpoint:** `POST /api/answer-question/`  
**Function:** `views.answer_question`  
**Authentication:** `@permission_classes([AllowAny])`  
**Request Format:**
```json
{
  "question": "User's question",
  "context": "Additional context" (optional)
}
```
**Response Format:**
```json
{
  "answer": "AI-generated answer"
}
```
**Description:** Answers a specific question using AI.

---

## Page Views (Non-API)

### 20. `landing_page`
**Endpoint:** `GET /`  
**Function:** `views.landing_page`  
**Authentication:** None  
**Description:** Renders the landing page template.

---

### 21. `dashboard`
**Endpoint:** `GET /dashboard/`  
**Function:** `views.dashboard`  
**Authentication:** `@login_required`  
**Description:** Renders the main dashboard page.

---

### 22. `new_dashboard`
**Endpoint:** `GET /dashboard/new/`  
**Function:** `views.new_dashboard`  
**Authentication:** `@login_required`  
**Description:** Renders the premium/new dashboard page.

---

### 23. `analytics_dashboard`
**Endpoint:** `GET /dashboard/analytics/`  
**Function:** `views.analytics_dashboard`  
**Authentication:** `@login_required`  
**Description:** Renders the analytics dashboard page.

---

### 24. `analytics_export`
**Endpoint:** `GET /dashboard/analytics/export/`  
**Function:** `views.analytics_export`  
**Authentication:** `@login_required`  
**Description:** Exports analytics data (CSV/JSON format).

---

### 25. `about_page`
**Endpoint:** `GET /about/`  
**Function:** `views.about_page`  
**Authentication:** None  
**Description:** Renders the about page.

---

## Authentication Requirements Summary

| Endpoint | Authentication | Notes |
|----------|---------------|-------|
| `/api/login/` | None | Public |
| `/api/auth/status/` | Session | Checks if logged in |
| `/api/csrf/` | None | Public |
| `/signup/` | None | Public |
| `/logout/` | Session | Must be logged in |
| `/api/send-chat/` | AllowAny | Works for guests and authenticated users |
| `/api/chat/sessions/` | IsAuthenticated | Session auth required |
| `/api/chat/sessions/<id>/` | LoginRequired | Session auth required |
| `/api/chat/sessions/new/` | IsAuthenticated | Session auth required |
| `/api/chat/sessions/<id>/rename/` | IsAuthenticated | Session auth required |
| `/api/chat/sessions/<id>/archive/` | IsAuthenticated | Session auth required |
| `/api/chat/sessions/<id>/delete/` | IsAuthenticated | Session auth required |
| `/clear-session/` | AllowAny | Works for guests |
| `/api/user/settings/` | LoginRequired | Session auth required |
| `/api/user/settings/update/` | LoginRequired | Session auth required |
| `/api/track` | None | Public |
| `/api/summarize/` | IsAuthenticated | Session auth required |
| `/api/smart-suggestions/` | AllowAny | Works for guests |
| `/api/answer-question/` | AllowAny | Works for guests |

---

## Important Notes

1. **Session Authentication**: The web app uses Django's session-based authentication, not token authentication. Users are authenticated via cookies/sessions.

2. **CSRF Protection**: All POST requests require a CSRF token. Get it from cookies (`csrftoken`) or via `/api/csrf/` endpoint.

3. **File Uploads**: The `send_chat` and `summarize_medical_record` endpoints accept `multipart/form-data` with file uploads. Use `files[]` for multiple files.

4. **Tone Options**: 
   - `PlainClinical` (default)
   - `Clinical`
   - `Caregiver`
   - `Faith`

5. **Language Codes**: Use ISO 639-1 language codes (e.g., `en-US`, `es-ES`, `fr-FR`).

6. **Session Management**: Chat sessions are automatically created when sending messages. Use `session_id` to continue conversations.

7. **Message Format**: Messages in chat sessions are stored as arrays of objects with `role` (user/assistant/system), `content`, `ts` (timestamp), and optional `meta` (metadata).

8. **Error Handling**: All endpoints return appropriate HTTP status codes:
   - `200` - Success
   - `400` - Bad Request
   - `401` - Unauthorized
   - `404` - Not Found
   - `500` - Server Error

---

## Frontend Integration Examples

### Sending a Chat Message
```javascript
const formData = new FormData();
formData.append('message', 'Hello, how are you?');
formData.append('tone', 'PlainClinical');
formData.append('lang', 'en-US');

const response = await fetch('/api/send-chat/', {
  method: 'POST',
  headers: {
    'X-CSRFToken': getCSRFToken() // From cookies
  },
  body: formData,
  credentials: 'include' // Important for session cookies
});

const data = await response.json();
console.log(data.reply); // AI response
console.log(data.session_id); // Session ID
```

### Getting Chat Sessions
```javascript
const response = await fetch('/api/chat/sessions/', {
  credentials: 'include' // Important for session cookies
});

const sessions = await response.json();
console.log(sessions); // Array of chat sessions
```

### Getting User Settings
```javascript
const response = await fetch('/api/user/settings/', {
  credentials: 'include'
});

const settings = await response.json();
console.log(settings.display_name);
```

---

## File Locations

- **Views**: `myApp/views.py`
- **Chat API**: `myApp/api_chat.py`
- **URLs**: `myApp/urls.py`
- **Main URL Config**: `myProject/urls.py`

---

*Last Updated: January 8, 2025*

