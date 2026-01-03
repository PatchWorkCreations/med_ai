# 🔧 Mobile API Backend - AI Integration Steps

**How to Connect Real AI to Your Mobile API**

---

## 🎯 **What We're Doing**

Connecting your mobile API stub responses to the **REAL AI chat system** that your PWA uses.

**Current:** Returns "Hello! You said: {message}"  
**After:** Returns real AI responses with all tone/mode/setting support

---

## 📋 **Step-by-Step Implementation**

### **Step 1: Update send_chat Function**

**File:** `/Users/Julia/Downloads/med_ai/mobile_api/compat_views.py`

**Find this function** (around line 275):
```python
@api_view(['POST'])
@parser_classes([JSONParser])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def send_chat(request):
```

**Replace the ENTIRE function** with the code from:
`/Users/Julia/Downloads/med_ai/mobile_api/send_chat_ai_connected.py`

---

### **Step 2: Update Parser Classes**

The new send_chat needs to accept both JSON and files. Change the decorator:

```python
# OLD:
@parser_classes([JSONParser])

# NEW:
@parser_classes([JSONParser, MultiPartParser, FormParser])
```

This allows the endpoint to accept:
- JSON only (for text messages)
- Multipart (for files + text)

---

### **Step 3: Add Required Imports**

At the top of `compat_views.py`, update the imports:

```python
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
```

---

### **Step 4: Update create_chat_session (Optional but Recommended)**

**Find this function** (around line 204):
```python
@api_view(['POST'])
@parser_classes([JSONParser])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_chat_session(request):
```

**Replace with:**
```python
@api_view(['POST'])
@parser_classes([JSONParser])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_chat_session(request):
    """
    Create a new chat session.
    POST /api/chat/sessions/new/
    Expects: {title, tone, language}
    """
    from myApp.models import ChatSession
    from myApp.views import normalize_tone
    
    title = request.data.get("title", "New Conversation")
    tone = normalize_tone(request.data.get("tone"))
    language = request.data.get("lang", "en-US")  # Use 'lang' per contract
    
    # Create real session
    session = ChatSession.objects.create(
        user=request.user,
        title=title,
        tone=tone,
        lang=language,
        messages=[]
    )
    
    # Make it sticky
    request.session["active_chat_session_id"] = session.id
    request.session.modified = True
    
    print(f"📝 SESSION: Created session {session.id} for user {request.user.username}")
    
    return Response({
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "tone": tone,
        "language": language,
    }, status=201)
```

---

### **Step 5: Update chat_sessions List (Optional)**

**Find:**
```python
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def chat_sessions(request):
```

**Replace with:**
```python
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def chat_sessions(request):
    """
    Get user's chat sessions.
    GET /api/chat/sessions/
    """
    from myApp.models import ChatSession
    
    sessions = ChatSession.objects.filter(
        user=request.user, 
        archived=False
    ).order_by('-updated_at')[:50]
    
    return Response([{
        "id": s.id,
        "title": s.title or "Untitled",
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
        "tone": s.tone or "PlainClinical",
        "lang": s.lang or "en-US",
    } for s in sessions], status=200)
```

---

### **Step 6: Add Session Management Endpoints**

Add these NEW functions to `compat_views.py`:

```python
@api_view(['POST'])
@parser_classes([JSONParser])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def clear_session(request):
    """
    Clear session and soft memory - for "New Chat" button.
    POST /api/chat/clear-session/
    """
    # Clear soft memory
    for k in ["latest_summary", "chat_history", "nm_last_mode", "nm_last_short_msg", "nm_last_ts"]:
        request.session.pop(k, None)
    request.session.pop("active_chat_session_id", None)
    request.session.modified = True
    
    return Response({"ok": True}, status=200)
```

Add to `compat_urls.py`:
```python
path('chat/clear-session/', compat_views.clear_session, name='clear_session'),
```

---

## 🧪 **Testing the Changes**

### **Test 1: Simple Chat (QUICK Mode)**
```bash
# Get a token first
TOKEN="your_token_here"

# Send short message
curl -X POST http://localhost:8000/api/send-chat/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $TOKEN" \
  -d '{
    "message": "headache",
    "tone": "PlainClinical",
    "lang": "en-US"
  }'
```

**Expected:** Quick 4-5 sentence response

---

### **Test 2: Detailed Chat (FULL Mode)**
```bash
curl -X POST http://localhost:8000/api/send-chat/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $TOKEN" \
  -d '{
    "message": "headache for 3 days with nausea and light sensitivity",
    "tone": "PlainClinical",
    "lang": "en-US"
  }'
```

**Expected:** Full structured response with sections

---

### **Test 3: Clinical Mode**
```bash
curl -X POST http://localhost:8000/api/send-chat/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $TOKEN" \
  -d '{
    "message": "Patient with K+ 5.8, Cr 1.2",
    "tone": "Clinical",
    "care_setting": "hospital",
    "lang": "en-US"
  }'
```

**Expected:** SOAP note + Quick-Scan Card

---

### **Test 4: Faith Mode**
```bash
curl -X POST http://localhost:8000/api/send-chat/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $TOKEN" \
  -d '{
    "message": "worried about surgery",
    "tone": "Faith",
    "faith_setting": "christian",
    "lang": "en-US"
  }'
```

**Expected:** Comfort + Bible verse

---

## ⚠️ **Important Notes**

### **OpenAI API Key Required:**

Make sure you have `OPENAI_API_KEY` set in your environment:

```bash
# Check if set:
python manage.py shell -c "from django.conf import settings; print(settings.OPENAI_API_KEY)"
```

If not set, add to your `.env` file or environment variables.

---

### **Dependencies:**

These should already be installed (they're used by myApp):
- openai
- ChatSession model
- All helper functions from myApp.views

---

### **Cost Warning:**

Real AI calls cost money! Each message uses:
- 2 OpenAI API calls (raw + polish)
- Model: gpt-4o
- Approximate cost: ~$0.01-0.03 per message

For testing, consider:
1. Using fewer test messages
2. Setting up API usage limits
3. Monitoring OpenAI dashboard

---

## 🔄 **Restart Server After Changes**

After making these changes:

1. **Stop server:** Ctrl+C
2. **Restart:** `python manage.py runserver`
3. **Test:** Try sending a chat message from iOS app

---

## ✅ **Verification Checklist**

After implementing:

- [ ] Code changes applied to compat_views.py
- [ ] Imports updated (MultiPartParser, FormParser)
- [ ] Parser classes updated in decorators
- [ ] Server restarted
- [ ] OpenAI API key is set
- [ ] Test with curl - get real AI response
- [ ] Test from iOS app - get real AI response
- [ ] Different tones return different styles
- [ ] Session ID persists across messages
- [ ] Soft memory works (QUICK → FULL upgrade)

---

## 📊 **What Changes**

### **Before (Stub):**
```python
ai_response = f"Hello! You said: {message}"
return Response({
    "content": ai_response,
    ...
})
```

### **After (Real AI):**
```python
# Classify mode
mode = _classify_mode(message, has_files, session)

# Build prompts with layers
system_prompt = get_system_prompt(tone)
if faith_setting:
    system_prompt = get_faith_prompt(system_prompt, faith_setting)

# Two-pass OpenAI
raw = openai.generate(messages)
polished = openai.polish(raw)

# Save to database
session.messages.append(user_msg)
session.messages.append(ai_msg)
session.save()

return Response({
    "content": polished,
    ...
})
```

---

## 🎯 **Summary**

**Changes Needed:**
1. Replace send_chat function (main change)
2. Update parser classes decorator
3. (Optional) Replace create_chat_session
4. (Optional) Replace chat_sessions list
5. (Optional) Add clear_session endpoint

**Time:** 15-30 minutes  
**Difficulty:** Medium (copy/paste mostly)  
**Dependencies:** OpenAI API key  
**Testing:** Required after changes  

**Result:** Full AI chat with all tones/modes/settings! 🎉

---

For the complete new send_chat code, see:
`send_chat_ai_connected.py`

