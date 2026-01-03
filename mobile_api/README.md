# Mobile API

A safe, additive REST API for mobile applications using Django REST Framework.

## Features

- ✅ **Versioned & Namespaced**: All endpoints under `/api/v1/mobile/`
- ✅ **Zero Conflicts**: No changes to existing views, models, or URLs
- ✅ **Token Authentication**: Per-view DRF auth (doesn't affect existing site auth)
- ✅ **Scoped CORS**: Only applies to mobile API paths
- ✅ **Feature Flag**: Can be disabled instantly via `MOBILE_API_ENABLED=0`

## Configuration

### Feature Flag

The API is controlled by an environment variable:

```bash
MOBILE_API_ENABLED=1  # API is active (default)
MOBILE_API_ENABLED=0  # API is disabled
```

### CORS Settings

CORS is scoped to only `/api/v1/mobile/*` paths and allows:
- `https://neuromedai.org`
- `https://www.neuromedai.org`

For local testing, uncomment in `settings.py`:
```python
CORS_ALLOWED_ORIGIN_REGEXES = [r"^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$"]
```

## Endpoints

### Public Endpoints (No Authentication)

#### Health Check
```bash
GET /api/v1/mobile/health/
```
Response:
```json
{
  "status": "ok",
  "time": "2025-10-18T12:00:00Z"
}
```

#### Sign Up
```bash
POST /api/v1/mobile/signup/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123",
  "first_name": "John",
  "last_name": "Doe",
  "username": "johndoe"  // optional, defaults to email prefix
}
```
Response (201):
```json
{
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "date_joined": "2025-10-18T12:00:00Z",
    "last_login": null
  },
  "token": "abc123token456"
}
```

#### Login
```bash
POST /api/v1/mobile/login/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```
Response (200):
```json
{
  "user": { /* user object */ },
  "token": "abc123token456"
}
```

### Authenticated Endpoints (Require Token)

All authenticated endpoints require the `Authorization` header:
```
Authorization: Token abc123token456
```

#### Check Auth Status
```bash
GET /api/v1/mobile/auth/status/
Authorization: Token YOUR_TOKEN
```
Response:
```json
{
  "authenticated": true,
  "user": { /* user object */ }
}
```

#### Get User Settings
```bash
GET /api/v1/mobile/user/settings/
Authorization: Token YOUR_TOKEN
```
Response:
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "date_joined": "2025-10-18T12:00:00Z",
  "last_login": "2025-10-18T12:05:00Z"
}
```

#### Update User Settings
```bash
POST /api/v1/mobile/user/settings/
Authorization: Token YOUR_TOKEN
Content-Type: application/json

{
  "first_name": "Jane",
  "last_name": "Smith"
}
```
Response:
```json
{
  "success": true
}
```

#### Get Chat Sessions
```bash
GET /api/v1/mobile/chat/sessions/
Authorization: Token YOUR_TOKEN
```
Response:
```json
{
  "sessions": []
}
```
_Note: This is a stub. Replace with actual logic from your existing chat system._

#### Send Chat Message
```bash
POST /api/v1/mobile/send-chat/
Authorization: Token YOUR_TOKEN
Content-Type: application/json

{
  "message": "Hello, how are you?",
  "session_id": "abc123"  // optional
}
```
Response:
```json
{
  "id": "uuid-here",
  "role": "assistant",
  "content": "Hello from the model 👋",
  "timestamp": "2025-10-18T12:00:00Z",
  "session_id": "abc123",
  "metadata": null
}
```
_Note: This is a placeholder. Connect to your existing AI logic in `myApp.api_chat`._

#### Summarize Text
```bash
POST /api/v1/mobile/summarize/
Authorization: Token YOUR_TOKEN
Content-Type: application/json

{
  "text": "Long text to summarize..."
}
```
Response:
```json
{
  "summary": "First 200 characters of text..."
}
```
_Note: Placeholder logic. Replace with actual summarization._

## Testing

### Quick Smoke Tests

```bash
# 1. Health check
curl http://localhost:8000/api/v1/mobile/health/

# 2. Sign up
curl -X POST http://localhost:8000/api/v1/mobile/signup/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!","first_name":"Test"}'

# 3. Login (save the token)
curl -X POST http://localhost:8000/api/v1/mobile/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!"}'

# 4. Auth status (replace YOUR_TOKEN)
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/v1/mobile/auth/status/

# 5. Send chat
curl -X POST http://localhost:8000/api/v1/mobile/send-chat/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","message":"Hello!"}'
```

## Integration with Existing Code

The mobile API is designed as a thin adapter layer. To integrate with your existing business logic:

### Chat Integration
In `mobile_api/views.py`, update the `send_chat` function:

```python
from myApp.api_chat import your_existing_function

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def send_chat(request):
    message = request.data.get("message")
    session_id = request.data.get("session_id")
    
    # Call your existing logic
    ai_response = your_existing_function(
        user=request.user,
        session_id=session_id,
        text=message
    )
    
    return Response({
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "content": ai_response,
        "timestamp": timezone.now().isoformat(),
        "session_id": session_id,
        "metadata": None
    }, status=200)
```

### Session Management
Update `chat_sessions` to return actual user sessions from your database.

### Summarization
Update `summarize` to call your actual AI summarization logic.

## Rollback Plan

If you need to disable the API:

1. **Quick disable**: Set `MOBILE_API_ENABLED=0` in environment
2. **Full removal**: Delete these lines from `myProject/urls.py`:
   ```python
   if getattr(settings, "MOBILE_API_ENABLED", False):
       urlpatterns += [
           path('api/v1/mobile/', include('mobile_api.urls', namespace='mobile_api')),
       ]
   ```

## Security Notes

- ✅ Per-view authentication (doesn't affect existing site)
- ✅ Token-based auth for mobile clients
- ✅ No sensitive fields exposed (no `is_staff`, `is_superuser`)
- ✅ Timestamps in ISO format for easy Swift parsing
- ⚠️ Consider rate limiting for login/signup (future enhancement)
- ⚠️ Use HTTPS in production for token security

## Future Enhancements

- [ ] Rate limiting on authentication endpoints
- [ ] Token refresh mechanism
- [ ] Push notification support
- [ ] File upload endpoints
- [ ] WebSocket support for real-time chat
- [ ] API versioning strategy (v2, v3, etc.)

