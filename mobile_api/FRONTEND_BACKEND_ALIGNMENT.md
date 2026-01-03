# 🔄 Frontend-Backend Alignment Guide

## ✅ Quick Status Check

Run this to verify all endpoints are working:

```bash
cd /Users/Julia/Downloads/med_ai
./mobile_api/test_frontend_compat.sh http://localhost:8000
```

---

## 📋 Endpoint Alignment Reference

This document shows EXACTLY what your iOS app sends vs what Django expects.

### 1️⃣ Health Check / Auth Status

**iOS Sends:**
```
GET /api/auth/status/
Headers:
  - Content-Type: application/json
  - Authorization: Token <token> (if logged in)
```

**Django Expects:**
- Method: GET
- Authentication: Optional
- Response format:
```json
{
  "authenticated": false,
  "status": "ok",
  "time": "2025-10-24T11:00:00Z"
}
```

**Test Command:**
```bash
curl http://localhost:8000/api/auth/status/
```

---

### 2️⃣ Sign Up

**iOS Sends:**
```
POST /api/signup/
Headers:
  - Content-Type: application/json
Body:
{
  "name": "Test User",
  "email": "test@example.com",
  "password": "TestPass123!",
  "language": "en-US"
}
```

**Django Expects:**
- Method: POST
- Content-Type: application/json
- Authentication: None (public endpoint)
- Body fields:
  - `name` (string) - will be split into first_name/last_name
  - `email` (string, required)
  - `password` (string, required)
  - `language` (string, optional, default: "en-US")

**Django Returns:**
```json
{
  "id": 1,
  "username": "test",
  "email": "test@example.com",
  "first_name": "Test",
  "last_name": "User",
  "date_joined": "2025-10-24T11:00:00Z",
  "last_login": null,
  "token": "abc123def456..."
}
```

**Test Command:**
```bash
curl -X POST http://localhost:8000/api/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "password": "TestPass123!",
    "language": "en-US"
  }'
```

---

### 3️⃣ Login

**iOS Sends:**
```
POST /api/login/
Headers:
  - Content-Type: application/json
Body:
{
  "email": "test@example.com",
  "password": "TestPass123!"
}
```

**Django Expects:**
- Method: POST
- Content-Type: application/json
- Authentication: None (public endpoint)
- Body fields:
  - `email` (string, required)
  - `password` (string, required)

**Django Returns:**
```json
{
  "id": 1,
  "username": "test",
  "email": "test@example.com",
  "first_name": "Test",
  "last_name": "User",
  "date_joined": "2025-10-24T11:00:00Z",
  "last_login": "2025-10-24T11:05:00Z",
  "token": "abc123def456..."
}
```

**Test Command:**
```bash
# First sign up, then login
curl -X POST http://localhost:8000/api/signup/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test2@example.com","password":"TestPass123!"}'

curl -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test2@example.com","password":"TestPass123!"}'
```

---

### 4️⃣ Get User Settings

**iOS Sends:**
```
GET /api/user/settings/
Headers:
  - Content-Type: application/json
  - Authorization: Token <your_token>
```

**Django Expects:**
- Method: GET
- Content-Type: application/json
- Authentication: **Required** (Token)

**Django Returns:**
```json
{
  "id": 1,
  "username": "test",
  "email": "test@example.com",
  "first_name": "Test",
  "last_name": "User",
  "date_joined": "2025-10-24T11:00:00Z",
  "last_login": "2025-10-24T11:05:00Z"
}
```

**Test Command:**
```bash
# Replace <TOKEN> with actual token from signup/login
curl http://localhost:8000/api/user/settings/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token <TOKEN>"
```

---

### 5️⃣ Update User Settings

**iOS Sends:**
```
POST /api/user/settings/update/
Headers:
  - Content-Type: application/json
  - Authorization: Token <your_token>
Body:
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "newemail@example.com"
}
```

**Django Expects:**
- Method: POST
- Content-Type: application/json
- Authentication: **Required** (Token)
- Body fields (all optional):
  - `first_name` (string)
  - `last_name` (string)
  - `email` (string)

**Django Returns:**
```json
{
  "id": 1,
  "username": "test",
  "email": "newemail@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "date_joined": "2025-10-24T11:00:00Z",
  "last_login": "2025-10-24T11:05:00Z"
}
```

**Test Command:**
```bash
curl -X POST http://localhost:8000/api/user/settings/update/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token <TOKEN>" \
  -d '{"first_name":"John","last_name":"Doe"}'
```

---

### 6️⃣ Get Chat Sessions

**iOS Sends:**
```
GET /api/chat/sessions/
Headers:
  - Content-Type: application/json
  - Authorization: Token <your_token>
```

**Django Expects:**
- Method: GET
- Content-Type: application/json
- Authentication: **Required** (Token)

**Django Returns:**
```json
[]
```
*(Currently returns empty array - stub implementation)*

**Test Command:**
```bash
curl http://localhost:8000/api/chat/sessions/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token <TOKEN>"
```

---

### 7️⃣ Create Chat Session

**iOS Sends:**
```
POST /api/chat/sessions/new/
Headers:
  - Content-Type: application/json
  - Authorization: Token <your_token>
Body:
{
  "title": "Medical Report Discussion",
  "tone": "plain",
  "language": "en-US"
}
```

**Django Expects:**
- Method: POST
- Content-Type: application/json
- Authentication: **Required** (Token)
- Body fields (all optional):
  - `title` (string, default: "New Conversation")
  - `tone` (string, default: "professional")
  - `language` (string, default: "en-US")

**Django Returns:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Medical Report Discussion",
  "created_at": "2025-10-24T11:00:00Z",
  "tone": "plain",
  "language": "en-US"
}
```

**Test Command:**
```bash
curl -X POST http://localhost:8000/api/chat/sessions/new/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token <TOKEN>" \
  -d '{"title":"Medical Report Discussion","tone":"plain","language":"en-US"}'
```

---

### 8️⃣ Send Chat Message ⭐ (The one causing 415)

**iOS Sends:**
```
POST /api/send-chat/
Headers:
  - Content-Type: application/json
  - Authorization: Token <your_token>
Body:
{
  "message": "Hi, can you help me?"
}
```

**Django Expects:**
- Method: POST
- Content-Type: application/json ← **MUST BE application/json**
- Authentication: **Required** (Token)
- Body fields:
  - `message` (string, required)
  - `session_id` (string, optional)

**Django Returns:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "assistant",
  "content": "Hello! You said: Hi, can you help me?",
  "timestamp": "2025-10-24T11:00:00Z",
  "session_id": null,
  "metadata": null
}
```

**Test Command:**
```bash
# First get a token by signing up
TOKEN=$(curl -s -X POST http://localhost:8000/api/signup/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Chat Test","email":"chattest@example.com","password":"TestPass123!"}' \
  | grep -o '"token":"[^"]*"' | cut -d'"' -f4)

echo "Token: $TOKEN"

# Then send a chat message
curl -X POST http://localhost:8000/api/send-chat/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $TOKEN" \
  -d '{"message":"Hi, can you help me?"}'
```

---

### 9️⃣ Summarize (Upload Medical File)

**iOS Sends:**
```
POST /api/summarize/
Headers:
  - Content-Type: application/json
  - Authorization: Token <your_token>
Body:
{
  "filename": "medical_report.pdf",
  "fileType": "pdf",
  "content": "<base64_encoded_content>",
  "tone": "plain",
  "language": "en-US"
}
```

**Django Expects:**
- Method: POST
- Content-Type: application/json
- Authentication: **Required** (Token)
- Body fields:
  - `content` (string, required) - Base64 encoded file
  - `filename` (string, optional)
  - `fileType` or `file_type` (string, optional)
  - `tone` (string, optional)
  - `language` (string, optional)

**Django Returns:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "medical_report.pdf",
  "summary": "This is a medical summary placeholder...",
  "created_at": "2025-10-24T11:00:00Z",
  "tone": "plain",
  "language": "en-US"
}
```

---

## 🔍 Common Mismatches

### ❌ iOS sends snake_case, Django expects camelCase?
**Answer:** ✅ No issue - iOS uses `keyEncodingStrategy = .convertToSnakeCase` which automatically converts to snake_case. Django expects snake_case.

### ❌ iOS sends Date objects, Django can't parse?
**Answer:** ✅ No issue - iOS uses `dateEncodingStrategy = .iso8601` which Django can parse.

### ❌ CSRF token issues?
**Answer:** ✅ No issue for local dev - iOS skips CSRF for `/api/*` endpoints in local development.

### ❌ 415 Unsupported Media Type?
**Answer:** ✅ FIXED - Added `@parser_classes([JSONParser])` to all mobile_api POST endpoints.

---

## 🧪 Full Integration Test Script

Save this as `test_alignment.sh`:

```bash
#!/bin/bash

echo "🧪 Testing Frontend-Backend Alignment"
echo "======================================"
echo ""

BASE_URL="http://localhost:8000"

# Test 1: Health check
echo "1️⃣ Testing health check..."
STATUS=$(curl -s "$BASE_URL/api/auth/status/" | grep -o '"status":"ok"')
if [ "$STATUS" == '"status":"ok"' ]; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    exit 1
fi

# Test 2: Sign up
echo ""
echo "2️⃣ Testing sign up..."
TIMESTAMP=$(date +%s)
SIGNUP_RESPONSE=$(curl -s -X POST "$BASE_URL/api/signup/" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Test User\",\"email\":\"test$TIMESTAMP@example.com\",\"password\":\"TestPass123!\"}")

TOKEN=$(echo "$SIGNUP_RESPONSE" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
if [ -n "$TOKEN" ]; then
    echo "✅ Sign up passed"
    echo "   Token: $TOKEN"
else
    echo "❌ Sign up failed"
    echo "   Response: $SIGNUP_RESPONSE"
    exit 1
fi

# Test 3: Get user settings
echo ""
echo "3️⃣ Testing get user settings..."
SETTINGS=$(curl -s "$BASE_URL/api/user/settings/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $TOKEN")

EMAIL=$(echo "$SETTINGS" | grep -o "test$TIMESTAMP@example.com")
if [ -n "$EMAIL" ]; then
    echo "✅ Get user settings passed"
else
    echo "❌ Get user settings failed"
    echo "   Response: $SETTINGS"
fi

# Test 4: Send chat message
echo ""
echo "4️⃣ Testing send chat message..."
CHAT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/send-chat/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $TOKEN" \
  -d '{"message":"Hello, test message"}')

CHAT_CONTENT=$(echo "$CHAT_RESPONSE" | grep -o '"content"')
if [ -n "$CHAT_CONTENT" ]; then
    echo "✅ Send chat message passed"
    echo "   Response: $CHAT_RESPONSE"
else
    echo "❌ Send chat message failed"
    echo "   Response: $CHAT_RESPONSE"
fi

# Test 5: Create chat session
echo ""
echo "5️⃣ Testing create chat session..."
SESSION_RESPONSE=$(curl -s -X POST "$BASE_URL/api/chat/sessions/new/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $TOKEN" \
  -d '{"title":"Test Session","tone":"plain"}')

SESSION_ID=$(echo "$SESSION_RESPONSE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
if [ -n "$SESSION_ID" ]; then
    echo "✅ Create chat session passed"
    echo "   Session ID: $SESSION_ID"
else
    echo "❌ Create chat session failed"
    echo "   Response: $SESSION_RESPONSE"
fi

echo ""
echo "======================================"
echo "🎉 All tests completed!"
```

Make it executable and run:
```bash
chmod +x test_alignment.sh
./test_alignment.sh
```

---

## 📱 iOS App Checklist

Make sure your iOS app does this:

- [ ] Sets `Content-Type: application/json` header on ALL requests
- [ ] Sends `Authorization: Token <token>` header for authenticated endpoints
- [ ] Stores token after signup/login: `UserDefaults.standard.set(token, forKey: "auth_token")`
- [ ] Uses JSON encoder with snake_case: `encoder.keyEncodingStrategy = .convertToSnakeCase`
- [ ] Points to correct base URL: `http://localhost:8000` for simulator
- [ ] Has Info.plist with `NSAllowsLocalNetworking = true`

---

## 🐛 Troubleshooting

### Still getting 415 error?

1. **Restart Django server** - Code changes don't apply until restart!
   ```bash
   # Press Ctrl+C, then:
   python manage.py runserver
   ```

2. **Check Content-Type header** - Must be exactly `application/json`

3. **Test with curl** - If curl works but iOS doesn't, the issue is in iOS code

### Getting 401 error?

- You're not logged in or token is invalid
- Test signup first, save the token, then use it

### Getting 404 error?

- Check the URL path (trailing slash matters!)
- Django expects: `/api/send-chat/` (with slash)
- Not: `/api/send-chat` (without slash)

---

## ✅ Success Indicators

You know alignment is correct when:

1. ✅ Health check returns `{"status":"ok"}`
2. ✅ Signup returns a token
3. ✅ Login returns a token
4. ✅ Chat message returns `{"role":"assistant","content":"..."}`
5. ✅ No 415 errors in Django logs
6. ✅ No 401 errors (except when not logged in)

---

**Last Updated:** October 24, 2025  
**Backend Version:** mobile_api v1.0  
**iOS Requirements:** iOS 15+, Swift 5.5+

