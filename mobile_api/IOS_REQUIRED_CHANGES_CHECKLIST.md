# ✅ iOS Required Changes - Quick Checklist

## 🚨 MUST CHANGE THESE TO WORK WITH BACKEND

---

## 1️⃣ **User Model (CRITICAL)**

```swift
struct User: Codable, Identifiable {
    let id: Int
    let username: String
    let email: String
    let firstName: String?       // ← ADD ? (optional)
    let lastName: String?        // ← ADD ? (optional)
    let dateJoined: String       // ← CHANGE from Date to String
    let lastLogin: String?       // ← CHANGE from Date to String
    let token: String?
    
    enum CodingKeys: String, CodingKey {
        case id, username, email, token
        case firstName = "first_name"
        case lastName = "last_name"
        case dateJoined = "date_joined"
        case lastLogin = "last_login"
    }
}
```

**Why:** Backend sends empty strings and ISO8601 dates with timezone

---

## 2️⃣ **Request Headers (REQUIRED)**

```swift
// Every request:
request.setValue("application/json", forHTTPHeaderField: "Content-Type")

// Authenticated requests:
if let token = UserDefaults.standard.string(forKey: "auth_token") {
    request.setValue("Token \(token)", forHTTPHeaderField: "Authorization")
}
```

**Format:** `Token <value>` NOT `Bearer <value>`

---

## 3️⃣ **Endpoints (USE THESE)**

```
Health: GET  /api/auth/status/
Signup: POST /api/signup/
Login:  POST /api/login/
Chat:   POST /api/send-chat/
```

**Base URL:** `http://localhost:8000` (simulator)

---

## 4️⃣ **JSON Configuration (REQUIRED)**

```swift
let decoder = JSONDecoder()
decoder.keyDecodingStrategy = .convertFromSnakeCase

let encoder = JSONEncoder()
encoder.keyEncodingStrategy = .convertToSnakeCase
```

**Why:** Backend uses snake_case, iOS uses camelCase

---

## 5️⃣ **Token Storage (MUST DO)**

```swift
// After login/signup:
if let token = user.token {
    UserDefaults.standard.set(token, forKey: "auth_token")
}

// Before authenticated requests:
let token = UserDefaults.standard.string(forKey: "auth_token")
```

**Key:** `"auth_token"`

---

## 6️⃣ **Request Bodies (EXACT FORMAT)**

### Login:
```json
{
  "email": "user@example.com",
  "password": "password"
}
```

### Signup:
```json
{
  "name": "John Doe",
  "email": "user@example.com",
  "password": "password",
  "language": "en-US"
}
```

### Chat:
```json
{
  "message": "Hello",
  "session_id": null
}
```

---

## 7️⃣ **Response Handling (EXPECT THESE)**

### Login/Signup Response:
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

### Error Response:
```json
{
  "error": "Invalid credentials"
}
```

---

## 8️⃣ **Error Codes (HANDLE THESE)**

```swift
case 200...299: // Success
case 400:       // Bad Request
case 401:       // Unauthorized (clear token)
case 415:       // Wrong Content-Type
case 500:       // Server Error
```

---

## 🚨 **Critical Don'ts:**

- ❌ DON'T use `Date` for dateJoined/lastLogin
- ❌ DON'T make firstName/lastName non-optional
- ❌ DON'T use `Bearer` auth (use `Token`)
- ❌ DON'T send form data (use JSON)
- ❌ DON'T forget to save token after login
- ❌ DON'T forget Content-Type header

---

## ✅ **Testing:**

After changes, verify:
- [ ] Login works without "decode error"
- [ ] Token saved to UserDefaults
- [ ] Console shows: `🔑 Token saved: ...`
- [ ] Can navigate to main screen
- [ ] Django shows: `✅ LOGIN DEBUG: Login successful...`

---

**If ALL checkboxes pass → Integration works! 🎉**

---

For complete details see: `IOS_BACKEND_INTEGRATION_GUIDE.md`

