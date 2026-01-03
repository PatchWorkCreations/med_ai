# iOS Mobile API Documentation

**Last Updated:** October 24, 2025  
**Base URL:** Your server URL (e.g., `http://localhost:8000` or `https://yourserver.com`)

---

## 📋 Table of Contents
1. [Authentication](#authentication)
2. [User Management](#user-management)
3. [Chat System](#chat-system)
4. [Medical Summaries](#medical-summaries)
5. [Error Handling](#error-handling)

---

## 🔐 Authentication

All authenticated endpoints require a token in the `Authorization` header:
```
Authorization: Token YOUR_TOKEN_HERE
```

### POST /api/signup/
**Register a new user**

**Request:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "securepassword123",
  "language": "en-US"
}
```

**Success Response (201):**
```json
{
  "id": 123,
  "username": "john",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "date_joined": "2025-10-24T22:10:00.000Z",
  "last_login": null,
  "token": "abc123def456ghi789jkl012mno345pqr678stu901vwx234yz"
}
```

**Error Response (400):**
```json
{
  "error": "Email already exists"
}
```
or
```json
{
  "error": "email and password are required"
}
```

---

### POST /api/login/
**Authenticate existing user**

**Request:**
```json
{
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Success Response (200):**
```json
{
  "id": 123,
  "username": "john",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "date_joined": "2025-10-24T22:10:00.000Z",
  "last_login": "2025-10-24T22:15:00.000Z",
  "token": "abc123def456ghi789jkl012mno345pqr678stu901vwx234yz"
}
```

**Error Response (401):**
```json
{
  "error": "Invalid credentials"
}
```

---

### GET /api/auth/status/
**Check authentication status (public endpoint)**

**Request:** No body needed

**Success Response (200) - Authenticated:**
```json
{
  "authenticated": true,
  "user": {
    "id": 123,
    "username": "john",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "date_joined": "2025-10-24T22:10:00.000Z",
    "last_login": "2025-10-24T22:15:00.000Z"
  },
  "status": "ok",
  "time": "2025-10-24T22:20:00.000Z"
}
```

**Success Response (200) - Not Authenticated:**
```json
{
  "authenticated": false,
  "status": "ok",
  "time": "2025-10-24T22:20:00.000Z"
}
```

---

## 👤 User Management

### GET /api/user/settings/
**Get user profile** (Requires authentication)

**Request:** No body needed

**Success Response (200):**
```json
{
  "id": 123,
  "username": "john",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "date_joined": "2025-10-24T22:10:00.000Z",
  "last_login": "2025-10-24T22:15:00.000Z"
}
```

---

### POST /api/user/settings/update/
**Update user profile** (Requires authentication)

**Request (all fields optional):**
```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "email": "jane@example.com"
}
```

**Success Response (200):**
```json
{
  "id": 123,
  "username": "john",
  "email": "jane@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "date_joined": "2025-10-24T22:10:00.000Z",
  "last_login": "2025-10-24T22:15:00.000Z"
}
```

**Error Response (400):**
```json
{
  "error": "Email already in use"
}
```

---

## 💬 Chat System

### GET /api/chat/sessions/
**Get user's chat sessions** (Requires authentication)

**Request:** No body needed

**Success Response (200):**
```json
[
  {
    "id": 456,
    "title": "Medical Question",
    "created_at": "2025-10-24T22:00:00.000Z",
    "updated_at": "2025-10-24T22:15:00.000Z",
    "tone": "PlainClinical",
    "lang": "en-US"
  },
  {
    "id": 789,
    "title": "Follow-up Questions",
    "created_at": "2025-10-23T10:30:00.000Z",
    "updated_at": "2025-10-23T11:45:00.000Z",
    "tone": "Caregiver",
    "lang": "en-US"
  }
]
```

---

### POST /api/chat/sessions/new/
**Create a new chat session** (Requires authentication)

**Request:**
```json
{
  "title": "New Conversation",
  "tone": "PlainClinical",
  "lang": "en-US"
}
```

**Available Tones:**
- `PlainClinical` (default)
- `Caregiver`
- `Faith`
- `Clinical`

**Success Response (201):**
```json
{
  "id": 999,
  "title": "New Conversation",
  "created_at": "2025-10-24T22:30:00.000Z",
  "tone": "PlainClinical",
  "language": "en-US"
}
```

---

### POST /api/send-chat/
**Send a chat message to AI** (Requires authentication)

⚠️ **IMPORTANT:** Use `/api/send-chat/` (with hyphen) NOT `/api/send_chat/`

**Request Format 1 - Text Only:**
```json
{
  "message": "What are the symptoms of diabetes?",
  "tone": "PlainClinical",
  "lang": "en-US",
  "session_id": 999
}
```

**Request Format 2 - With Files (multipart/form-data):**
```
Content-Type: multipart/form-data

Fields:
- message: "Please analyze this document"
- tone: "PlainClinical"
- lang: "en-US"
- session_id: 999
- files[]: [file1.pdf]
- files[]: [file2.jpg]
```

**Required Parameters:**
- `message` (string): User's message text **OR** files must be provided
- `tone` (string, optional): Defaults to "PlainClinical"
- `lang` (string, optional): Defaults to "en-US"
- `session_id` (number, optional): If omitted, uses sticky session from backend

**Optional Parameters (tone-specific):**
- `care_setting`: "hospital" | "ambulatory" | "urgent" (for Clinical/Caregiver tones)
- `faith_setting`: "general" | "christian" | "muslim" | etc. (for Faith tone)

**Success Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "assistant",
  "content": "Diabetes symptoms include increased thirst, frequent urination, extreme hunger, unexplained weight loss, fatigue, blurred vision, and slow-healing sores.",
  "timestamp": "2025-10-24T22:35:00.000Z",
  "session_id": 999,
  "metadata": null
}
```

**Error Response (400):**
```json
{
  "error": "message or files required"
}
```

**Error Response (401) - Not Authenticated:**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Error Response (503) - System Busy:**
```json
{
  "error": "System busy. Try again in a moment."
}
```

---

### POST /api/chat/clear-session/
**Clear session for "New Chat"** (Requires authentication)

**Request:** Empty body `{}`

**Success Response (200):**
```json
{
  "ok": true
}
```

---

## 📄 Medical Summaries

### GET /api/summarize/
**Get user's medical summaries** (Requires authentication)

**Request:** No body needed

**Success Response (200):**
```json
[]
```
*Note: Currently returns empty array - summaries feature in progress*

---

### POST /api/summarize/
**Upload and summarize medical document** (Requires authentication)

**Request:**
```json
{
  "filename": "lab_results.pdf",
  "fileType": "application/pdf",
  "content": "base64_encoded_file_content_here",
  "tone": "professional",
  "language": "en-US"
}
```

**Success Response (201):**
```json
{
  "id": "660e9511-f30c-52e5-b827-557766551111",
  "title": "lab_results.pdf",
  "summary": "This is a medical summary placeholder. The document has been processed.",
  "created_at": "2025-10-24T22:40:00.000Z",
  "tone": "professional",
  "language": "en-US"
}
```

**Error Response (400):**
```json
{
  "error": "content is required"
}
```

---

## 🚫 Error Handling

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | Success | Request completed successfully |
| 201 | Created | New resource created (signup, session) |
| 400 | Bad Request | Missing required fields, invalid input |
| 401 | Unauthorized | Invalid credentials or missing token |
| 404 | Not Found | Wrong endpoint URL |
| 500 | Server Error | Backend issue - contact support |
| 503 | Service Unavailable | AI service temporarily busy |

### Error Response Format

All error responses follow this format:
```json
{
  "error": "Human-readable error message"
}
```

or (for DRF authentication errors):
```json
{
  "detail": "Authentication credentials were not provided."
}
```

---

## 🔍 Common Issues & Solutions

### Issue: 404 on /send_chat
**Solution:** Use `/api/send-chat/` (with hyphen) not `/api/send_chat/` (with underscore)

### Issue: 401 Unauthorized
**Solution:** Ensure you're including the token in headers:
```swift
request.setValue("Token \(userToken)", forHTTPHeaderField: "Authorization")
```

### Issue: Chat not working
**Current Status:** Backend returns stub responses. Real AI is ready but disabled.  
Set `USE_REAL_AI = True` in `mobile_api/compat_views.py` line 295 to enable.

---

## 📱 iOS Code Example

```swift
// Send Chat Message
func sendChatMessage(message: String, tone: String = "PlainClinical") async throws -> ChatMessage {
    var request = URLRequest(url: URL(string: "\(baseURL)/api/send-chat/")!)
    request.httpMethod = "POST"
    request.setValue("Token \(authToken)", forHTTPHeaderField: "Authorization")
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    
    let body: [String: Any] = [
        "message": message,
        "tone": tone,
        "lang": "en-US",
        "session_id": currentSessionId ?? 0
    ]
    
    request.httpBody = try JSONSerialization.data(withJSONObject: body)
    
    let (data, response) = try await URLSession.shared.data(for: request)
    
    guard let httpResponse = response as? HTTPURLResponse,
          httpResponse.statusCode == 200 else {
        throw NetworkError.requestFailed
    }
    
    return try JSONDecoder().decode(ChatMessage.self, from: data)
}
```

---

## 🎯 Mobile API Contract Summary

**iOS expects this structure for ChatMessage:**
```swift
struct ChatMessage: Codable {
    let id: String           // UUID string
    let role: String         // "assistant" or "user"
    let content: String      // Message text
    let timestamp: String    // ISO 8601 format
    let sessionId: Int?      // Optional session ID
    let metadata: String?    // Optional metadata (usually null)
}
```

**Backend guarantees:**
- All timestamps in ISO 8601 format (e.g., `2025-10-24T22:35:00.000Z`)
- Token authentication via `Authorization: Token XXX` header
- Consistent error format with `"error"` key
- Sticky session management (backend remembers your last session)

---

## 🔧 Backend Configuration

**To enable real AI responses:**
1. Open `/Users/Julia/Downloads/med_ai/mobile_api/compat_views.py`
2. Find line 295: `USE_REAL_AI = False`
3. Change to: `USE_REAL_AI = True`
4. Ensure `OPENAI_API_KEY` is set in your environment

**Current Status:** AI integration complete but using stub responses for testing.

---

## 📞 Support

Questions? Check:
- `/mobile_api/compat_views.py` - All endpoint implementations
- `/mobile_api/compat_urls.py` - URL routing
- Console logs show detailed request/response info

---

*Generated: October 24, 2025*

