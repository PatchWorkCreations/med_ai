# 📎 File Upload Implementation - Backend Accommodation

## ✅ Backend Implementation Status

The backend has been updated to fully accommodate the iOS frontend's file upload format.

## Frontend Format (What iOS Sends)

### Request Structure
- **Endpoint:** `POST /api/send-chat/`
- **Content-Type:** `multipart/form-data; boundary=<UUID>`
- **Authorization:** `Token <authentication_token>`

### Form Fields
| Field Name | Type | Description | Example |
|------------|------|-------------|---------|
| `message` | String | User text message | `"Please analyze this image"` |
| `tone` | String | Chat tone preference | `"plain_clinical"`, `"caregiver"`, `"faith"` |
| `lang` | String | Language code | `"en-US"` |
| `session_id` | String | Session ID (sent as string, represents integer) | `"123"` |
| `care_setting` | String | Care setting (optional) | `"hospital"`, `"ambulatory"`, `"urgent"` |
| `faith_setting` | String | Faith setting (optional) | `"general"`, `"christian"`, `"muslim"`, etc. |
| `files[]` | Binary Data | Array of file data | Multiple files supported |

### File Details
- **Field Name:** `files[]` (with array brackets)
- **Filename:** Preserved from original (e.g., `"file0.jpg"`, `"document.pdf"`)
- **MIME Type:** Provided in Content-Type header (may default to `image/jpeg`)

## Backend Implementation (What We Handle)

### ✅ Parsing
```python
# Extract form fields
user_message = (request.data.get("message") or "").strip()
tone_raw = request.data.get("tone", "PlainClinical")
lang = request.data.get("lang", "en-US")
care_setting = request.data.get("care_setting")
faith_setting = request.data.get("faith_setting")

# Parse session_id (frontend sends as string, backend needs int)
incoming_session_id = None
session_id_str = request.data.get("session_id")
if session_id_str:
    try:
        incoming_session_id = int(session_id_str)
    except (ValueError, TypeError):
        print(f"⚠️ Invalid session_id format: {session_id_str}, ignoring")

# Get files - frontend sends as "files[]" array
files = request.FILES.getlist("files[]")
```

### ✅ Tone Normalization
The backend automatically normalizes tone values:
- Frontend sends: `"plain_clinical"` → Backend converts to: `"PlainClinical"`
- Frontend sends: `"caregiver"` → Backend converts to: `"Caregiver"`
- Frontend sends: `"faith"` → Backend converts to: `"Faith"`
- etc.

This is handled by the `normalize_tone()` function.

### ✅ File Processing
```python
# Process files if present
if files:
    sections = [
        summarize_single_file(f, tone, sys_prompt, request.user, request)[1]
        for f in files
    ]
    context = "\n\n".join(sections).strip()
    if context:
        chat_history.append({
            "role": "user",
            "content": f"(Medical context):\n{context}"
        })
```

### ✅ Response Format
The backend returns the exact format expected by iOS:

```json
{
  "id": "uuid-string",
  "role": "assistant",
  "content": "AI response text...",
  "timestamp": "2025-01-20T10:30:00.000Z",
  "session_id": 123,
  "metadata": null
}
```

## Key Features

### 1. Multiple File Support
- Backend accepts multiple files in a single request
- Files are processed sequentially
- All file contexts are combined into a single medical context

### 2. File Type Detection
- Backend detects file type from:
  - Filename extension
  - MIME type from Content-Type header
  - File content (magic bytes) for validation

### 3. Image Processing
- Images are processed using OCR and image analysis
- PDFs are processed using PDF text extraction
- Text files are processed directly

### 4. Session Management
- Session ID is parsed from string to integer
- Falls back to sticky session if no session_id provided
- Creates new session if needed

### 5. Error Handling
- Returns proper JSON error responses
- Logs file information for debugging
- Handles missing or invalid files gracefully

## Testing

### Test Image Upload
```bash
curl -X POST http://192.168.100.53:8000/api/send-chat/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -F "message=Please analyze this image" \
  -F "tone=plain_clinical" \
  -F "lang=en-US" \
  -F "files[]=@/path/to/image.jpg"
```

### Test PDF Upload
```bash
curl -X POST http://192.168.100.53:8000/api/send-chat/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -F "message=Please analyze this PDF" \
  -F "tone=plain_clinical" \
  -F "lang=en-US" \
  -F "session_id=123" \
  -F "files[]=@/path/to/document.pdf"
```

### Test Multiple Files
```bash
curl -X POST http://192.168.100.53:8000/api/send-chat/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -F "message=Please analyze these files" \
  -F "tone=plain_clinical" \
  -F "lang=en-US" \
  -F "files[]=@/path/to/image1.jpg" \
  -F "files[]=@/path/to/image2.jpg" \
  -F "files[]=@/path/to/document.pdf"
```

## Debugging

The backend logs detailed information:
```
📎 Received 2 file(s):
  File 0: name=file0.jpg, size=123456, content_type=image/jpeg
  File 1: name=document.pdf, size=234567, content_type=application/pdf
🔍 DEBUG: Request keys: ['message', 'tone', 'lang', 'session_id', 'files[]']
🔍 DEBUG: Tone from request: 'plain_clinical'
🔍 DEBUG: Message: Please analyze this image...
🔍 DEBUG: Files: 2 file(s)
🔍 DEBUG: Session ID: 123
💬 User=admin, Msg=Please analyze this image..., Tone=PlainClinical (normalized from 'plain_clinical')
```

## Summary

✅ **Fully Accommodated:**
- Multipart form data parsing
- `files[]` array field name
- All form fields (message, tone, lang, session_id, care_setting, faith_setting)
- Session ID string-to-integer conversion
- Tone normalization (plain_clinical → PlainClinical)
- Multiple file support
- Proper JSON response format
- Error handling

The backend is ready to receive file uploads from the iOS app! 🎉

