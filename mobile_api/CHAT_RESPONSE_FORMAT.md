# ✅ Chat Response Format - Backend Implementation

## Status: CORRECT ✅

The `/api/send-chat/` endpoint **already returns the correct chat message format**, not the document summary format.

## Current Implementation

### Response Format (CORRECT)

```python
# mobile_api/compat_views.py - send_chat() function
return Response({
    "id": str(uuid.uuid4()),
    "role": "assistant",           # ✅ Correct: "assistant" for AI responses
    "content": final,               # ✅ Correct: AI response text
    "timestamp": timezone.now().isoformat(),  # ✅ Correct: ISO 8601 format
    "session_id": sess.id,          # ✅ Correct: Integer session ID
    "metadata": None                # ✅ Correct: Optional field
}, status=200)
```

### Example Response

```json
{
  "id": "2c0b5498-0056-4fe0-830e-11da557e5921",
  "role": "assistant",
  "content": "I've analyzed the image you sent. Here's what I found...",
  "timestamp": "2025-12-30T15:50:53.701038+00:00",
  "session_id": 123,
  "metadata": null
}
```

## Field Verification

| Field | Type | Status | Notes |
|-------|------|--------|-------|
| `id` | String | ✅ | UUID format |
| `role` | String | ✅ | Always `"assistant"` for AI responses |
| `content` | String | ✅ | AI's response text (NOT "summary") |
| `timestamp` | String | ✅ | ISO 8601 format (NOT "created_at") |
| `session_id` | Integer | ✅ | Session ID (NOT string) |
| `metadata` | null | ✅ | Optional field |

## What the Backend Does NOT Return

❌ **The backend does NOT return:**
- `title` field
- `summary` field  
- `created_at` field
- `tone` field
- `language` field

These fields are from the `/api/summarize/` endpoint, NOT `/api/send-chat/`.

## Endpoint Comparison

### `/api/send-chat/` (Chat Message Format)
```json
{
  "id": "msg_123",
  "role": "assistant",
  "content": "AI response text...",
  "timestamp": "2025-01-20T10:30:00Z",
  "session_id": 123,
  "metadata": null
}
```

### `/api/summarize/` (Document Summary Format)
```json
{
  "id": "doc_123",
  "title": "Document Title",
  "summary": "Document summary...",
  "created_at": "2025-01-20T10:30:00Z",
  "tone": "PlainClinical",
  "language": "en-US"
}
```

## Troubleshooting

If you're seeing the wrong format, check:

1. **URL Path**: Ensure you're calling `/api/send-chat/` not `/api/summarize/`
2. **Request Method**: Must be `POST`
3. **Content-Type**: Should be `multipart/form-data` for file uploads
4. **Authentication**: Must include `Authorization: Token <token>` header

## Testing

### Test with curl

```bash
# Test text message
curl -X POST http://192.168.100.53:8000/api/send-chat/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello",
    "tone": "plain_clinical",
    "lang": "en-US"
  }'

# Test with file upload
curl -X POST http://192.168.100.53:8000/api/send-chat/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -F "message=Please analyze this image" \
  -F "tone=plain_clinical" \
  -F "lang=en-US" \
  -F "files[]=@/path/to/image.jpg"
```

### Expected Response

Both should return:
```json
{
  "id": "...",
  "role": "assistant",
  "content": "...",
  "timestamp": "...",
  "session_id": 123,
  "metadata": null
}
```

## Code Location

- **File**: `mobile_api/compat_views.py`
- **Function**: `send_chat()` (lines 400-579)
- **Response**: Lines 566-573

## Summary

✅ **The backend is correctly implemented** and returns the chat message format.

If you're seeing a different format, it's likely:
1. Wrong endpoint being called
2. Caching issue
3. Different code path being executed

The implementation is correct and matches the iOS app's expectations! 🎉

