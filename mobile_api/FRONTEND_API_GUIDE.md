# 📱 Mobile API - Frontend Integration Guide

**For:** iOS/React Native/Mobile Frontend Developers  
**Base URL:** `https://neuromedai.org` (production) or `http://localhost:8000` (development)  
**API Version:** v1  
**Status:** ✅ Production Ready

---

## 🚀 Quick Start

### 1. Base URL Configuration

```swift
// iOS Example
let baseURL = "https://neuromedai.org"  // Production
// let baseURL = "http://localhost:8000"  // Development
```

### 2. Authentication Flow

1. **Sign up** or **Login** → Get `token`
2. Store token securely (e.g., `UserDefaults` or Keychain)
3. Include token in all authenticated requests: `Authorization: Token <your_token>`

### 3. Request Format

All requests use:
- **Content-Type:** `application/json`
- **Method:** GET or POST (as specified)
- **Authentication:** `Authorization: Token <token>` (for protected endpoints)

---

## 📋 Available Endpoints

### 🔓 Public Endpoints (No Authentication)

#### 1. Health Check / Auth Status
```http
GET /api/auth/status/
```

**Response:**
```json
{
  "authenticated": false,
  "status": "ok",
  "time": "2025-10-24T12:00:00Z"
}
```

**Use Case:** Check server connectivity and current auth status

---

#### 2. Sign Up
```http
POST /api/signup/
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "language": "en-US"  // optional, default: "en-US"
}
```

**Success Response (201):**
```json
{
  "id": 1,
  "username": "john",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "date_joined": "2025-10-24T12:00:00Z",
  "last_login": null,
  "token": "abc123def456ghi789..."
}
```

**Error Response (400):**
```json
{
  "error": "Email already exists"
}
```

**Important:** Save the `token` from this response!

---

#### 3. Login
```http
POST /api/login/
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "SecurePass123!"
}
```

**Success Response (200):**
```json
{
  "id": 1,
  "username": "john",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "date_joined": "2025-10-24T12:00:00Z",
  "last_login": "2025-10-24T12:05:00Z",
  "token": "abc123def456ghi789..."
}
```

**Error Response (401):**
```json
{
  "error": "Invalid credentials"
}
```

---

### 🔒 Authenticated Endpoints (Require Token)

**All authenticated endpoints require this header:**
```
Authorization: Token <your_token>
```

---

#### 4. Get User Profile
```http
GET /api/user/settings/
Authorization: Token <your_token>
```

**Response (200):**
```json
{
  "id": 1,
  "username": "john",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "date_joined": "2025-10-24T12:00:00Z",
  "last_login": "2025-10-24T12:05:00Z"
}
```

---

#### 5. Update User Profile
```http
POST /api/user/settings/update/
Authorization: Token <your_token>
Content-Type: application/json

{
  "first_name": "Jane",  // optional
  "last_name": "Smith",  // optional
  "email": "jane@example.com"  // optional
}
```

**Response (200):**
```json
{
  "id": 1,
  "username": "john",
  "email": "jane@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "date_joined": "2025-10-24T12:00:00Z",
  "last_login": "2025-10-24T12:05:00Z"
}
```

**Error Response (400):**
```json
{
  "error": "Email already in use"
}
```

---

#### 6. Get Chat Sessions
```http
GET /api/chat/sessions/
Authorization: Token <your_token>
```

**Response (200):**
```json
[
  {
    "id": 123,
    "title": "Medical Question",
    "created_at": "2025-10-24T12:00:00Z",
    "updated_at": "2025-10-24T12:15:00Z",
    "tone": "PlainClinical",
    "lang": "en-US",
    "messages": [
      {
        "id": "uuid-here",
        "role": "user",
        "content": "What are diabetes symptoms?",
        "timestamp": "2025-10-24T12:00:00Z",
        "session_id": 123,
        "metadata": null
      },
      {
        "id": "uuid-here",
        "role": "assistant",
        "content": "Diabetes symptoms include...",
        "timestamp": "2025-10-24T12:00:05Z",
        "session_id": 123,
        "metadata": null
      }
    ]
  }
]
```

---

#### 7. Create New Chat Session
```http
POST /api/chat/sessions/new/
Authorization: Token <your_token>
Content-Type: application/json

{
  "title": "New Conversation",  // optional
  "tone": "PlainClinical",      // optional, default: "PlainClinical"
  "lang": "en-US"               // optional, default: "en-US"
}
```

**Available Tones:**
- `PlainClinical` (default)
- `Caregiver`
- `Faith`
- `Clinical`

**Response (201):**
```json
{
  "id": 123,
  "title": "New Conversation",
  "created_at": "2025-10-24T12:00:00Z",
  "tone": "PlainClinical",
  "language": "en-US"
}
```

---

#### 8. Send Chat Message ⭐ **Core Feature**
```http
POST /api/send-chat/
Authorization: Token <your_token>
Content-Type: application/json

{
  "message": "What are the symptoms of diabetes?",
  "tone": "PlainClinical",      // optional
  "lang": "en-US",              // optional
  "session_id": 123,            // optional (uses sticky session if omitted)
  "care_setting": "hospital",   // optional (for Clinical/Caregiver tones)
  "faith_setting": "general"    // optional (for Faith tone)
}
```

**With File Upload (multipart/form-data):**
```http
POST /api/send-chat/
Authorization: Token <your_token>
Content-Type: multipart/form-data

Fields:
- message: "Please analyze this document"
- tone: "PlainClinical"
- lang: "en-US"
- session_id: 123
- files[]: [file1.pdf]
- files[]: [file2.jpg]
```

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "assistant",
  "content": "Diabetes symptoms include increased thirst, frequent urination...",
  "timestamp": "2025-10-24T12:00:00Z",
  "session_id": 123,
  "metadata": null
}
```

**Error Responses:**
- `400`: `{"error": "message or files required"}`
- `401`: `{"detail": "Authentication credentials were not provided."}`
- `503`: `{"error": "System busy. Try again in a moment."}`

**Important Notes:**
- ✅ **Real AI is connected** - This endpoint uses GPT-4o
- ✅ Backend manages sessions automatically (sticky sessions)
- ✅ Supports file uploads (PDF, images, etc.)
- ✅ Tone customization works (PlainClinical, Caregiver, Faith, Clinical)

---

#### 9. Clear Chat Session
```http
POST /api/chat/clear-session/
Authorization: Token <your_token>
Content-Type: application/json

{}
```

**Response (200):**
```json
{
  "ok": true
}
```

**Use Case:** Call this when user taps "New Chat" button

---

#### 10. Get Medical Summaries
```http
GET /api/summarize/
Authorization: Token <your_token>
```

**Response (200):**
```json
[]
```

*Note: Currently returns empty array - feature in progress*

---

#### 11. Upload & Summarize Medical Document
```http
POST /api/summarize/
Authorization: Token <your_token>
Content-Type: application/json

{
  "filename": "lab_results.pdf",
  "fileType": "application/pdf",
  "content": "base64_encoded_file_content_here",
  "tone": "professional",  // optional
  "language": "en-US"      // optional
}
```

**Response (201):**
```json
{
  "id": "660e9511-f30c-52e5-b827-557766551111",
  "title": "lab_results.pdf",
  "summary": "This is a medical summary placeholder...",
  "created_at": "2025-10-24T12:00:00Z",
  "tone": "professional",
  "language": "en-US"
}
```

*Note: Currently returns placeholder - real processing in progress*

---

## 🔐 Authentication Details

### Token Format
- **Type:** Django REST Framework Token
- **Length:** 40 characters (hex)
- **Example:** `abc123def456ghi789jkl012mno345pqr678stu901`
- **Persistence:** Tokens persist across server restarts
- **Shared:** Same tokens work for web PWA and mobile API

### Token Storage (iOS Example)
```swift
// Save token after login/signup
UserDefaults.standard.set(token, forKey: "auth_token")

// Retrieve token for requests
let token = UserDefaults.standard.string(forKey: "auth_token") ?? ""
request.setValue("Token \(token)", forHTTPHeaderField: "Authorization")
```

### Token Lifetime
- **Current:** Tokens don't expire (stateless)
- **Future:** May add refresh tokens (optional enhancement)

---

## 📊 Response Format Standards

### Success Responses
- **200 OK:** Successful GET/POST
- **201 Created:** New resource created (signup, session)
- **Format:** JSON object or array

### Error Responses
All errors follow this format:
```json
{
  "error": "Human-readable error message"
}
```

Or (for DRF auth errors):
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | Success | Request completed successfully |
| 201 | Created | New resource created |
| 400 | Bad Request | Missing required fields, invalid input |
| 401 | Unauthorized | Invalid credentials or missing token |
| 404 | Not Found | Wrong endpoint URL |
| 500 | Server Error | Backend issue - contact support |
| 503 | Service Unavailable | AI service temporarily busy |

---

## 🎯 Data Models

### User Object
```json
{
  "id": 1,
  "username": "john",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "date_joined": "2025-10-24T12:00:00Z",  // ISO 8601 string
  "last_login": "2025-10-24T12:05:00Z"    // ISO 8601 string or null
}
```

### ChatMessage Object
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",  // UUID string
  "role": "assistant",                            // "user" or "assistant"
  "content": "Message text here",
  "timestamp": "2025-10-24T12:00:00Z",           // ISO 8601 string
  "session_id": 123,                             // Integer or null
  "metadata": null                                // Usually null
}
```

### ChatSession Object
```json
{
  "id": 123,
  "title": "Medical Question",
  "created_at": "2025-10-24T12:00:00Z",
  "updated_at": "2025-10-24T12:15:00Z",
  "tone": "PlainClinical",
  "lang": "en-US",
  "messages": [ /* array of ChatMessage objects */ ]
}
```

---

## 💻 Code Examples

### Swift (iOS) Example

```swift
import Foundation

class APIClient {
    let baseURL = "https://neuromedai.org"
    var authToken: String? {
        return UserDefaults.standard.string(forKey: "auth_token")
    }
    
    // Sign Up
    func signUp(name: String, email: String, password: String) async throws -> User {
        var request = URLRequest(url: URL(string: "\(baseURL)/api/signup/")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = [
            "name": name,
            "email": email,
            "password": password,
            "language": "en-US"
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 201 else {
            throw APIError.requestFailed
        }
        
        let user = try JSONDecoder().decode(User.self, from: data)
        
        // Save token
        if let token = user.token {
            UserDefaults.standard.set(token, forKey: "auth_token")
        }
        
        return user
    }
    
    // Send Chat Message
    func sendChatMessage(
        message: String,
        tone: String = "PlainClinical",
        sessionId: Int? = nil
    ) async throws -> ChatMessage {
        var request = URLRequest(url: URL(string: "\(baseURL)/api/send-chat/")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        if let token = authToken {
            request.setValue("Token \(token)", forHTTPHeaderField: "Authorization")
        }
        
        var body: [String: Any] = [
            "message": message,
            "tone": tone,
            "lang": "en-US"
        ]
        if let sessionId = sessionId {
            body["session_id"] = sessionId
        }
        
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError.requestFailed
        }
        
        return try JSONDecoder().decode(ChatMessage.self, from: data)
    }
}

// Models
struct User: Codable {
    let id: Int
    let username: String
    let email: String
    let firstName: String?
    let lastName: String?
    let dateJoined: String  // ISO 8601 string
    let lastLogin: String?  // ISO 8601 string or null
    let token: String?
    
    enum CodingKeys: String, CodingKey {
        case id, username, email
        case firstName = "first_name"
        case lastName = "last_name"
        case dateJoined = "date_joined"
        case lastLogin = "last_login"
        case token
    }
}

struct ChatMessage: Codable {
    let id: String
    let role: String
    let content: String
    let timestamp: String
    let sessionId: Int?
    let metadata: String?
    
    enum CodingKeys: String, CodingKey {
        case id, role, content, timestamp, metadata
        case sessionId = "session_id"
    }
}

enum APIError: Error {
    case requestFailed
    case invalidResponse
    case unauthorized
}
```

---

## ⚠️ Important Notes

### 1. Date/Time Format
- All timestamps are **ISO 8601 strings** (e.g., `"2025-10-24T12:00:00Z"`)
- **Do NOT** expect Date objects - parse as strings
- Use `ISO8601DateFormatter` in Swift for parsing

### 2. Field Naming
- Backend uses **snake_case** (`first_name`, `last_name`, `session_id`)
- iOS should use `keyEncodingStrategy = .convertToSnakeCase` when encoding
- iOS should use `keyDecodingStrategy = .convertFromSnakeCase` when decoding

### 3. Optional Fields
- `first_name`, `last_name` can be `null`
- `last_login` can be `null`
- `session_id` in ChatMessage can be `null`
- `metadata` is usually `null`

### 4. Session Management
- Backend uses **sticky sessions** - if you don't provide `session_id`, backend remembers your last session
- To start fresh, call `/api/chat/clear-session/` first
- Sessions persist across app restarts

### 5. File Uploads
- Use `multipart/form-data` for file uploads
- Field name: `files[]` (array) or `file` (single)
- Supported: PDF, images, text files

---

## 🧪 Testing

### Quick Test with curl

```bash
# 1. Health check
curl http://localhost:8000/api/auth/status/

# 2. Sign up
curl -X POST http://localhost:8000/api/signup/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com","password":"Test123!"}'

# 3. Login (save token from response)
TOKEN="your_token_here"

# 4. Get user settings
curl http://localhost:8000/api/user/settings/ \
  -H "Authorization: Token $TOKEN"

# 5. Send chat message
curl -X POST http://localhost:8000/api/send-chat/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello!"}'
```

---

## 🐛 Troubleshooting

### 401 Unauthorized
- **Cause:** Missing or invalid token
- **Fix:** Check that token is included in `Authorization` header
- **Format:** `Authorization: Token <token>` (note the space after "Token")

### 400 Bad Request
- **Cause:** Missing required fields or invalid data
- **Fix:** Check request body matches expected format
- **Check:** Ensure `Content-Type: application/json` header is set

### 404 Not Found
- **Cause:** Wrong URL path
- **Fix:** Check endpoint URL (trailing slash matters!)
- **Correct:** `/api/send-chat/` ✅
- **Wrong:** `/api/send_chat/` ❌

### 415 Unsupported Media Type
- **Cause:** Missing or wrong Content-Type header
- **Fix:** Set `Content-Type: application/json` on all POST requests

### Chat Not Working
- **Status:** ✅ Real AI is connected and working
- **If issues:** Check that `OPENAI_API_KEY` is set on backend
- **Response time:** May take 5-10 seconds for AI responses

---

## 📞 Support & Resources

### Documentation Files
- `IOS_API_DOCUMENTATION.md` - Detailed iOS-specific guide
- `FRONTEND_BACKEND_ALIGNMENT.md` - Endpoint alignment reference
- `BACKEND_FINAL_REPORT.md` - Complete backend status

### Backend Code
- `mobile_api/compat_views.py` - All endpoint implementations
- `mobile_api/compat_urls.py` - URL routing

### Testing Scripts
- `test_frontend_compat.sh` - Automated endpoint testing
- `smoke_test.sh` - Quick smoke tests

---

## ✅ Integration Checklist

Before going live, verify:

- [ ] Base URL configured correctly (production vs development)
- [ ] Token storage implemented securely
- [ ] All requests include `Content-Type: application/json`
- [ ] Authenticated requests include `Authorization: Token <token>`
- [ ] Date parsing handles ISO 8601 strings
- [ ] Error handling implemented for all status codes
- [ ] User model matches backend response format
- [ ] ChatMessage model matches backend response format
- [ ] Session management implemented
- [ ] File upload works (if using)
- [ ] Tested with real backend (not just mocks)

---

## 🎉 You're Ready!

The backend is **production-ready** and fully operational. All core features are working:
- ✅ Authentication (signup/login)
- ✅ User management
- ✅ Chat with real AI (GPT-4o)
- ✅ Session management
- ✅ File uploads

Just integrate the endpoints above and you're good to go!

---

**Last Updated:** October 24, 2025  
**API Version:** 1.0  
**Backend Status:** 🟢 Production Ready

