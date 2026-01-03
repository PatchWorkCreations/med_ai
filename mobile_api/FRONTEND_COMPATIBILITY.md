# Frontend API Compatibility Analysis

## 🔍 Endpoint Mapping Comparison

### ❌ Current Mismatches

| Frontend Expects | Backend Implemented | Status |
|-----------------|---------------------|--------|
| `/api/auth/status/` | `/api/v1/mobile/health/` | ❌ Path mismatch |
| `/api/login/` | `/api/v1/mobile/login/` | ❌ Path mismatch |
| `/api/signup/` | `/api/v1/mobile/signup/` | ❌ Path mismatch |
| `/auth/google/` | Not implemented | ❌ Missing |
| `/api/user/settings/` | `/api/v1/mobile/user/settings/` | ❌ Path mismatch |
| `/api/user/settings/update/` | `/api/v1/mobile/user/settings/` (POST) | ⚠️ Different pattern |
| `/api/summarize/` (GET) | `/api/v1/mobile/summarize/` (POST) | ⚠️ Different methods |
| `/api/chat/sessions/` | `/api/v1/mobile/chat/sessions/` | ❌ Path mismatch |
| `/api/chat/sessions/new/` | `/api/v1/mobile/chat/sessions/` (POST) | ⚠️ Different pattern |
| `/api/send-chat/` | `/api/v1/mobile/send-chat/` | ❌ Path mismatch |

## 🔧 Request/Response Format Differences

### Sign Up
**Frontend Sends:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "pass123",
  "language": "en-US"
}
```

**Backend Expects:**
```json
{
  "email": "john@example.com",
  "password": "pass123",
  "first_name": "John",
  "last_name": "Doe",
  "username": "optional"
}
```
❌ Field name mismatch: `name` vs `first_name`/`last_name`

### User Profile
**Frontend Expects in User model:**
- Has all fields from snake_case converted to camelCase
- Expected structure not fully visible in provided code

**Backend Returns:**
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "date_joined": "2025-10-18T12:00:00Z",
  "last_login": "2025-10-18T12:00:00Z"
}
```

### Chat Message
**Frontend Sends:**
```json
{
  "message": "Hello"
}
```
Missing: `session_id` (backend expects it)

**Backend Returns:**
```json
{
  "id": "uuid",
  "role": "assistant",
  "content": "response",
  "timestamp": "2025-10-18T12:00:00Z",
  "session_id": "abc",
  "metadata": null
}
```

## ✅ What Works

1. **JSON encoding/decoding**: Frontend uses ISO8601 dates ✓
2. **Snake case conversion**: Frontend converts to/from snake_case ✓
3. **Token authentication**: Frontend sends `Authorization: Token XXX` ✓
4. **CSRF**: Frontend skips CSRF for `/api/` endpoints ✓

## 🎯 Solutions

### Option 1: Update Frontend (Recommended)
Update the frontend `APIService.swift` to use the new versioned endpoints.

### Option 2: Add Compatibility Routes to Backend
Create additional routes that match the frontend's expectations while keeping the versioned API.

### Option 3: Hybrid Approach
Keep versioned API + add backward-compatible aliases.

---

## Recommendation: Option 2 (Add Compatibility Routes)

This allows the frontend to work immediately while maintaining the clean versioned API for future use.

