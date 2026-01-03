# Tone Debugging Guide

**Issue:** User selects "Caregiver" in frontend, but backend logs show `Tone=PlainClinical`

## Quick Diagnosis

After adding debug logging, when you send a chat message, check the server logs for these lines:

```
🔍 DEBUG: Raw request.data keys: [...]
🔍 DEBUG: Raw tone value from request: '...'
🔍 DEBUG: Full request.data: {...}
💬 User=..., Tone=... (normalized from '...')
```

## What to Look For

### Scenario 1: Frontend Not Sending Tone
**Logs will show:**
```
🔍 DEBUG: Raw request.data keys: ['message', 'lang']
🔍 DEBUG: Raw tone value from request: 'PlainClinical'  # <-- Default fallback
```

**Fix:** This is a **frontend problem**. The iOS app needs to include `tone` in the POST body.

**Check in iOS code:**
- `APIService.sendChatMessage()` should include `tone: selectedTone.rawValue` in the request body
- Verify `selectedTone` is being read from `UserDefaults` or state correctly
- Check that the tone picker is actually updating the shared state

### Scenario 2: Frontend Sending Wrong Key Name
**Logs will show:**
```
🔍 DEBUG: Raw request.data keys: ['message', 'lang', 'toneName', 'selectedTone', ...]
🔍 DEBUG: Raw tone value from request: 'PlainClinical'  # <-- Not found, defaulted
```

**Fix:** This is a **frontend problem**. The iOS app is using the wrong key name.

**Check in iOS code:**
- Ensure the JSON key is exactly `"tone"` (lowercase)
- Not `"toneName"`, `"selectedTone"`, `"Tone"`, etc.

### Scenario 3: Frontend Sending Empty/Null Tone
**Logs will show:**
```
🔍 DEBUG: Raw request.data keys: ['message', 'lang', 'tone']
🔍 DEBUG: Raw tone value from request: None  # or '' or null
🔍 DEBUG: Full request.data: {'message': '...', 'tone': None, ...}
```

**Fix:** This is a **frontend problem**. The iOS app is sending `tone` but it's null/empty.

**Check in iOS code:**
- Verify `selectedTone` is not `nil` before sending
- Check that the tone picker initializes with a default value
- Ensure `tone.rawValue` is not an empty string

### Scenario 4: Frontend Sending Correctly, Backend Not Reading
**Logs will show:**
```
🔍 DEBUG: Raw request.data keys: ['message', 'lang', 'tone']
🔍 DEBUG: Raw tone value from request: 'Caregiver'  # <-- Correct!
💬 User=..., Tone=PlainClinical (normalized from 'Caregiver')  # <-- But normalized wrong!
```

**Fix:** This is a **backend problem**. The `normalize_tone()` function is not recognizing "Caregiver".

**Check backend:**
- Verify `PROMPT_TEMPLATES` in `myApp/views.py` includes "Caregiver" as a key
- Check `normalize_tone()` function handles case-insensitive matching correctly

## Most Likely Issue

Based on the current logs showing `Tone=PlainClinical` without any debug output, the most likely scenario is **#1: Frontend Not Sending Tone**.

The backend defaults to `PlainClinical` when `tone` is missing:
```python
tone_raw = request.data.get("tone", "PlainClinical")  # Defaults if missing
```

## Quick Test: Manual CURL

Test if the backend works correctly when tone IS provided:

```bash
curl -X POST http://localhost:8000/api/send-chat/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Test message",
    "tone": "Caregiver",
    "lang": "en-US"
  }'
```

**Expected log output:**
```
🔍 DEBUG: Raw request.data keys: ['message', 'tone', 'lang']
🔍 DEBUG: Raw tone value from request: 'Caregiver'
💬 User=..., Tone=Caregiver (normalized from 'Caregiver')
```

If this works, the backend is fine and the issue is in the iOS app.

## Next Steps

1. **Restart the Django server** to enable the new debug logging
2. **Send a chat message from the iOS app** with "Caregiver" selected
3. **Check the server logs** for the debug output
4. **Share the logs** to determine if it's frontend or backend

## iOS Code Checklist

Verify these in your iOS codebase:

- [ ] `ChatView` receives `selectedTone` as a parameter
- [ ] `sendChatMessage()` includes `tone: selectedTone.rawValue` in the request body
- [ ] The `Tone` enum's `rawValue` matches backend canonical keys exactly:
  - `PlainClinical` (not `Plain Clinical` or `plainclinical`)
  - `Caregiver` (not `caregiver` or `Care Giver`)
  - `Geriatric` (not `geriatric`)
  - etc.
- [ ] `selectedTone` is not `nil` when sending
- [ ] The tone picker actually updates the shared state before "Start Chat"

## Backend Code Checklist

- [x] ✅ Parser classes include `JSONParser` (already done)
- [x] ✅ Reading `tone` from `request.data.get("tone")` (already done)
- [x] ✅ Debug logging added (just added)
- [ ] ⏳ Verify `normalize_tone()` recognizes all tone keys (check `PROMPT_TEMPLATES`)



