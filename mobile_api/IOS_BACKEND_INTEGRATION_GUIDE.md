# 📱 iOS App → Django Backend Integration Guide

**What Your iOS App Must Change to Work With This Backend**

---

## 🎯 **Backend Configuration You're Connecting To:**

```
Server: http://localhost:8000 (local development)
API Prefix: /api/
Auth Method: Token Authentication
Content-Type: application/json
Date Format: ISO8601 with timezone
Field Naming: snake_case
```

---

## 1️⃣ **CRITICAL: Fix Your User Model**

### **What Backend Sends:**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@gmail.com",
  "first_name": "",
  "last_name": "",
  "date_joined": "2025-07-30T17:42:33.835913+00:00",
  "last_login": "2025-10-24T11:25:30.448571+00:00",
  "token": "659cc7fdf89da1a611c61e95689fb6e4a3b6213f"
}
```

### **Your iOS Model Must Be:**
```swift
struct User: Codable, Identifiable {
    let id: Int
    let username: String
    let email: String
    let firstName: String?       // ← OPTIONAL (can be empty string)
    let lastName: String?        // ← OPTIONAL (can be empty string)
    let dateJoined: String       // ← STRING (not Date)
    let lastLogin: String?       // ← STRING (not Date)
    let token: String?
    
    enum CodingKeys: String, CodingKey {
        case id
        case username
        case email
        case firstName = "first_name"      // ← snake_case mapping
        case lastName = "last_name"        // ← snake_case mapping
        case dateJoined = "date_joined"    // ← snake_case mapping
        case lastLogin = "last_login"      // ← snake_case mapping
        case token
    }
}
```

**Why:**
- Backend returns empty strings `""` not `null` for names
- Backend sends dates as ISO8601 strings with timezone
- Backend uses `snake_case`, iOS uses `camelCase`

---

## 2️⃣ **API Endpoints Your App Must Use**

### **Base URL Configuration:**
```swift
struct APIConfig {
    #if DEBUG
    static let baseURL = "http://localhost:8000"  // ← For simulator
    // OR for physical device:
    // static let baseURL = "http://192.168.1.XXX:8000"  // ← Your Mac's IP
    #else
    static let baseURL = "https://neuromedai.org"  // ← Production
    #endif
}
```

### **All Available Endpoints:**

| Endpoint | Method | Auth | Request Body | Response |
|----------|--------|------|--------------|----------|
| `/api/auth/status/` | GET | No | None | `{"authenticated": bool}` |
| `/api/signup/` | POST | No | See below | User + token |
| `/api/login/` | POST | No | See below | User + token |
| `/api/user/settings/` | GET | Yes | None | User object |
| `/api/user/settings/update/` | POST | Yes | See below | User object |
| `/api/chat/sessions/` | GET | Yes | None | Array of sessions |
| `/api/chat/sessions/new/` | POST | Yes | See below | Session object |
| `/api/send-chat/` | POST | Yes | See below | Message object |
| `/api/summarize/` | GET/POST | Yes | See below | Summary object |

---

## 3️⃣ **Request Formats Your App Must Send**

### **Signup Request:**
```swift
struct SignupRequest: Codable {
    let name: String          // Will be split into first_name/last_name
    let email: String
    let password: String
    let language: String?     // Optional, default: "en-US"
}

// Example:
let request = SignupRequest(
    name: "John Doe",
    email: "john@example.com",
    password: "SecurePass123!",
    language: "en-US"
)
```

**Backend expects:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "language": "en-US"
}
```

### **Login Request:**
```swift
struct LoginRequest: Codable {
    let email: String
    let password: String
}

// Example:
let request = LoginRequest(
    email: "admin@gmail.com",
    password: "admin"
)
```

**Backend expects:**
```json
{
  "email": "admin@gmail.com",
  "password": "admin"
}
```

### **Send Chat Message Request:**
```swift
struct SendChatRequest: Codable {
    let message: String
    let sessionId: String?    // Optional
    
    enum CodingKeys: String, CodingKey {
        case message
        case sessionId = "session_id"
    }
}

// Example:
let request = SendChatRequest(
    message: "Hello, can you help me?",
    sessionId: nil
)
```

**Backend expects:**
```json
{
  "message": "Hello, can you help me?",
  "session_id": null
}
```

### **Update User Settings Request:**
```swift
struct UpdateUserRequest: Codable {
    let firstName: String?
    let lastName: String?
    let email: String?
    
    enum CodingKeys: String, CodingKey {
        case firstName = "first_name"
        case lastName = "last_name"
        case email
    }
}

// Example:
let request = UpdateUserRequest(
    firstName: "Jane",
    lastName: "Smith",
    email: nil  // Don't update email
)
```

**Backend expects:**
```json
{
  "first_name": "Jane",
  "last_name": "Smith"
}
```

---

## 4️⃣ **Response Formats Your App Must Handle**

### **Chat Message Response:**
```swift
struct ChatMessage: Codable {
    let id: String
    let role: String              // "assistant" or "user"
    let content: String
    let timestamp: String         // ISO8601 string
    let sessionId: String?
    let metadata: [String: Any]?  // Optional metadata
    
    enum CodingKeys: String, CodingKey {
        case id, role, content, timestamp
        case sessionId = "session_id"
        case metadata
    }
}
```

**Backend sends:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "assistant",
  "content": "Hello! You said: Hello, can you help me?",
  "timestamp": "2025-10-24T14:01:16.000000+00:00",
  "session_id": null,
  "metadata": null
}
```

### **Error Response:**
```swift
struct ErrorResponse: Codable {
    let error: String
}
```

**Backend sends:**
```json
{
  "error": "Invalid credentials"
}
```

---

## 5️⃣ **Headers Your App Must Send**

### **All Requests:**
```swift
request.setValue("application/json", forHTTPHeaderField: "Content-Type")
```

### **Authenticated Requests:**
```swift
if let token = UserDefaults.standard.string(forKey: "auth_token") {
    request.setValue("Token \(token)", forHTTPHeaderField: "Authorization")
}
```

**Format:** `Token <token_value>`  
**Example:** `Token 659cc7fdf89da1a611c61e95689fb6e4a3b6213f`

### **DO NOT Send:**
- ❌ CSRF tokens (backend handles this automatically for `/api/*` endpoints)
- ❌ Session cookies (not used for mobile API)
- ❌ Custom auth schemes (only Token auth)

---

## 6️⃣ **JSON Encoder/Decoder Configuration**

### **Your JSON Decoder Must Be:**
```swift
private let jsonDecoder: JSONDecoder = {
    let decoder = JSONDecoder()
    decoder.keyDecodingStrategy = .convertFromSnakeCase
    // NO date decoding strategy - use strings!
    return decoder
}()
```

### **Your JSON Encoder Must Be:**
```swift
private let jsonEncoder: JSONEncoder = {
    let encoder = JSONEncoder()
    encoder.keyEncodingStrategy = .convertToSnakeCase
    // NO date encoding strategy - use strings!
    return encoder
}()
```

**Why:**
- Backend uses `snake_case` (first_name)
- iOS uses `camelCase` (firstName)
- Automatic conversion handles this

---

## 7️⃣ **Token Management**

### **After Successful Login/Signup:**
```swift
func handleAuthSuccess(user: User) {
    // 1. Save token
    if let token = user.token {
        UserDefaults.standard.set(token, forKey: "auth_token")
        print("🔑 Token saved: \(token)")
    }
    
    // 2. Update app state
    appState.currentUser = user
    appState.isAuthenticated = true
    
    // 3. Navigate to main screen
    navigationManager.navigateToMain()
}
```

### **On App Launch:**
```swift
func checkAuthStatus() {
    if let token = UserDefaults.standard.string(forKey: "auth_token"),
       !token.isEmpty {
        // User has a token - auto-login
        appState.isAuthenticated = true
    } else {
        // No token - show login
        appState.isAuthenticated = false
    }
}
```

### **On Logout:**
```swift
func logout() {
    // 1. Clear token
    UserDefaults.standard.removeObject(forKey: "auth_token")
    
    // 2. Clear app state
    appState.currentUser = nil
    appState.isAuthenticated = false
    
    // 3. Navigate to login
    navigationManager.navigateToLogin()
}
```

---

## 8️⃣ **Error Handling**

### **HTTP Status Codes to Handle:**

```swift
switch httpResponse.statusCode {
case 200...299:
    // Success - decode response
    let data = try decoder.decode(ResponseType.self, from: data)
    return data
    
case 400:
    // Bad Request - show error from backend
    let error = try? decoder.decode(ErrorResponse.self, from: data)
    throw APIError.badRequest(error?.error ?? "Invalid request")
    
case 401:
    // Unauthorized - token invalid or expired
    UserDefaults.standard.removeObject(forKey: "auth_token")
    throw APIError.unauthorized
    
case 403:
    // Forbidden - user doesn't have permission
    throw APIError.forbidden
    
case 404:
    // Not Found
    throw APIError.notFound
    
case 415:
    // Unsupported Media Type - check Content-Type header
    throw APIError.invalidContentType
    
case 500...599:
    // Server Error
    throw APIError.serverError
    
default:
    throw APIError.unknown(statusCode: httpResponse.statusCode)
}
```

### **Backend Error Messages:**
```swift
// Backend always returns errors in this format:
{
    "error": "Specific error message"
}

// Your app should:
let errorResponse = try? decoder.decode(ErrorResponse.self, from: data)
let message = errorResponse?.error ?? "Unknown error"
showAlert(message)
```

---

## 9️⃣ **Field Validation**

### **Email:**
- Backend accepts any valid email format
- Case-insensitive (converts to lowercase)
- Must be unique

### **Password:**
- Backend has no specific requirements (set your own in iOS)
- Recommended: Min 8 characters, mix of letters/numbers

### **Name:**
- Can be any string
- Will be split on first space: "John Doe" → first="John", last="Doe"
- Empty names are allowed (will be empty strings in backend)

### **Dates:**
- Backend sends: `"2025-10-24T14:01:16.835913+00:00"`
- iOS should store as String
- Convert to Date when displaying if needed

---

## 🔟 **Complete Request Example**

### **Login Flow:**
```swift
func login(email: String, password: String) async throws -> User {
    // 1. Configure request
    let url = URL(string: "\(APIConfig.baseURL)/api/login/")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    
    // 2. Prepare body
    let body = LoginRequest(email: email, password: password)
    request.httpBody = try jsonEncoder.encode(body)
    
    print("🌐 Making request to: \(url)")
    print("📤 Body: \(String(data: request.httpBody!, encoding: .utf8)!)")
    
    // 3. Send request
    let (data, response) = try await URLSession.shared.data(for: request)
    
    guard let httpResponse = response as? HTTPURLResponse else {
        throw APIError.invalidResponse
    }
    
    print("📥 Status: \(httpResponse.statusCode)")
    print("📥 Data: \(String(data: data, encoding: .utf8) ?? "nil")")
    
    // 4. Handle response
    switch httpResponse.statusCode {
    case 200:
        let user = try jsonDecoder.decode(User.self, from: data)
        
        // 5. Save token
        if let token = user.token {
            UserDefaults.standard.set(token, forKey: "auth_token")
            print("🔑 Token saved: \(token)")
        }
        
        return user
        
    case 401:
        let error = try? jsonDecoder.decode(ErrorResponse.self, from: data)
        throw APIError.unauthorized(message: error?.error ?? "Invalid credentials")
        
    default:
        throw APIError.unknown(statusCode: httpResponse.statusCode)
    }
}
```

---

## 1️⃣1️⃣ **Testing Checklist**

Before claiming anything works, verify:

### **Backend Connection:**
- [ ] Can reach `http://localhost:8000`
- [ ] Health check endpoint returns `{"authenticated": false}`

### **Signup:**
- [ ] Sends correct JSON format
- [ ] Receives User object with token
- [ ] Token is saved to UserDefaults
- [ ] Can see token in console: `🔑 Token saved: ...`

### **Login:**
- [ ] Sends email and password
- [ ] Receives User object with token
- [ ] Token is saved
- [ ] No "Failed to decode response" error
- [ ] Navigates to main screen

### **Authenticated Requests:**
- [ ] Sends `Authorization: Token <token>` header
- [ ] Backend accepts token
- [ ] Can fetch user settings
- [ ] Can send chat messages

---

## 🚨 **Common Mistakes to Avoid**

### ❌ **DON'T:**
```swift
// Wrong date type
let dateJoined: Date  // ← Backend sends String with timezone

// Wrong field types
let firstName: String  // ← Backend sends empty string, needs optional

// Wrong auth header
request.setValue("Bearer \(token)", ...)  // ← Backend expects "Token"

// Wrong Content-Type
request.setValue("application/x-www-form-urlencoded", ...)  // ← Must be JSON

// Missing snake_case conversion
enum CodingKeys: String, CodingKey {
    case firstName  // ← Won't match backend's "first_name"
}
```

### ✅ **DO:**
```swift
// Correct date type
let dateJoined: String  // ← Matches backend

// Correct field types
let firstName: String?  // ← Can handle empty strings

// Correct auth header
request.setValue("Token \(token)", ...)  // ← Matches backend

// Correct Content-Type
request.setValue("application/json", ...)  // ← Required

// Correct snake_case conversion
enum CodingKeys: String, CodingKey {
    case firstName = "first_name"  // ← Matches backend
}
```

---

## 📊 **Backend Capabilities**

### **What Backend CAN Do:**
- ✅ Authenticate users (email + password)
- ✅ Generate and validate tokens
- ✅ Create new user accounts
- ✅ Update user profiles
- ✅ Handle chat messages (stub)
- ✅ Manage chat sessions (stub)
- ✅ Accept file uploads (stub)
- ✅ Return JSON responses
- ✅ Handle CORS for localhost

### **What Backend CANNOT Do:**
- ❌ OAuth/Social login (not implemented yet)
- ❌ Password reset (not implemented yet)
- ❌ Email verification (not implemented yet)
- ❌ Real AI responses (returns stub messages)
- ❌ File processing (returns stub summaries)

---

## 🎯 **Summary of Required Changes**

### **Your iOS App Must:**

1. **Fix User model** - Make firstName/lastName optional, dates as Strings
2. **Use correct endpoints** - `/api/login/`, `/api/signup/`, etc.
3. **Send JSON** - Content-Type: application/json
4. **Use Token auth** - Authorization: Token <token>
5. **Handle snake_case** - Use keyDecodingStrategy
6. **Save tokens** - To UserDefaults after login
7. **Handle errors** - Parse error messages from backend
8. **Use correct date format** - Store as strings
9. **Handle empty names** - firstName/lastName can be ""
10. **Test thoroughly** - Verify complete flow works

---

## ✅ **After Making These Changes:**

Your app will:
- ✅ Successfully connect to backend
- ✅ Parse login responses without errors
- ✅ Save authentication tokens
- ✅ Make authenticated requests
- ✅ Handle user data correctly
- ✅ Work seamlessly with Django backend

---

## 🆘 **If Still Having Issues:**

1. Check Xcode console for exact error
2. Check Django terminal for backend logs
3. Verify all field types match
4. Confirm Content-Type header is set
5. Verify token is being sent
6. Test with curl to confirm backend works

---

**Your backend is perfect! Just configure your iOS app to match these specifications!** 🚀

