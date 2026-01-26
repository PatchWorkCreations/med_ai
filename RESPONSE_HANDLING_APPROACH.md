# NeuroMed Aira - Response Handling Approach

**Last Updated:** January 2025  
**Location:** `myApp/views.py` - `send_chat()` function

---

## Overview

NeuroMed Aira uses a **single-pass, context-aware response generation system** that processes user inputs (text + files) and generates medically accurate, tone-appropriate responses. The system is optimized for speed while maintaining quality and medical accuracy.

---

## Core Response Generation Strategy

### **Single-Pass Approach (Optimized)**

**Current Implementation:**
- **One API call** to GPT-4o with temperature 0.5 (balanced between accuracy and warmth)
- **No second pass** for tone polishing (removed for speed optimization)
- System prompt includes all tone instructions upfront
- Response is returned directly to user

**Why Single-Pass:**
- **Faster responses** - Reduces latency from ~4-6 seconds to ~2-3 seconds
- **Cost efficient** - Half the API calls
- **Quality maintained** - System prompt is comprehensive enough to generate tone-appropriate responses in one pass

**Code Location:**
```python
# myApp/views.py lines 1721-1729
reply = client.chat.completions.create(
    model="gpt-4o", 
    temperature=0.5,  # Balanced between accuracy (0.3) and creativity (0.6)
    messages=chat_history,
).choices[0].message.content.strip()
```

---

## Response Flow Architecture

### 1. **Input Processing**

#### A. Tone & Settings Selection
- **Tone normalization** - Converts various formats to standard tone names
- **Care settings** - Applied for Clinical/Caregiver tones (hospital, ambulatory, urgent)
- **Faith settings** - Applied for Faith tone (general, christian, muslim, etc.)
- **Language detection** - User preference or default (en-US)

#### B. System Prompt Construction
```
Base Tone Prompt → Care/Faith Setting Context → Language Instruction → Final System Prompt
```

**Process:**
1. Get base prompt from `PROMPT_TEMPLATES[tone]`
2. Add care setting context (if Clinical/Caregiver)
3. Add faith setting context (if Faith)
4. Append language instruction
5. Result: Complete system prompt with all instructions

#### C. Mode Classification
**Function:** `_classify_mode(user_message, has_files, session)`

**Modes:**
- **QUICK** - Short symptom (<12 words), no files
- **EXPLAIN** - General health question, no files
- **FULL** - Files uploaded OR detailed description OR follow-up

**Soft Memory:**
- Remembers recent QUICK mode interactions
- Auto-upgrades to FULL if user provides files/details within 5 minutes
- Maintains topic continuity

---

### 2. **File Processing**

#### A. File Type Detection
- **Images:** `.jpg`, `.jpeg`, `.png`, `.heic`, `.webp`
- **Documents:** `.pdf`, `.docx`, `.txt`
- **Separation:** Images and documents processed differently

#### B. Image Processing Strategy

**Single Image:**
- Uses `extract_contextual_medical_insights_from_image()`
- **Two-pass approach:**
  1. **First pass:** Detailed analysis (temperature 0.4) - "What do you see?"
  2. **Second pass:** Tone polish (temperature 0.3) - "Make it warm and conversational"
- **Special format:** Image analysis mode overrides FULL BREAKDOWN mode
- **Output:** Descriptive, observation-based explanation

**Multiple Images (2-4):**
- Uses `extract_contextual_medical_insights_from_multiple_images()`
- **Single API call** with all images in context
- **Two-pass approach** (same as single image)
- **Better context understanding** - AI sees all images together

**Many Images (5+):**
- **Batch processing** - Groups into batches of 2-3 images
- **Prevents timeout** - Stays under 25-second API timeout
- **Combines results** - Merges batch summaries into single context
- **Fallback:** If batch fails, processes individually

#### C. Document Processing

**PDF/DOCX/TXT:**
- **Text extraction** - Uses specialized libraries
- **Two-pass approach:**
  1. **First pass:** Summarize (temperature 0.4) - "Summarize clearly and kindly"
  2. **Second pass:** Tone polish (temperature 0.3) - "Polish the tone—warm, clear, confident"
- **Context preservation** - Full text available for follow-up questions

#### D. Combined Context Assembly
- All file summaries combined into `combined_context`
- Format: `"filename\nsummary\n\nfilename2\nsummary2"`
- Added to chat history as user message: `"(Here's the latest medical context):\n{combined_context}"`

---

### 3. **Chat History Management**

#### A. Session Persistence

**Authenticated Users (Database):**
- Uses `ChatSession` model
- Stores full conversation history (up to 200 messages)
- Persists across devices/sessions
- Auto-titles conversations
- Tracks tone, language, timestamps

**Guest Users (Session Storage):**
- Uses Django session storage
- Limited to last 10 messages
- Session-based (lost on logout)
- Stores in `request.session["chat_history"]`

#### B. History Structure
```python
chat_history = [
    {"role": "system", "content": system_prompt},      # Tone instructions
    {"role": "system", "content": "ResponseMode: FULL"},  # Mode header
    {"role": "user", "content": "(Here's the latest medical context):\n..."},  # File summaries
    {"role": "user", "content": user_message},         # User's question
    {"role": "assistant", "content": reply},           # AI response
    # ... more messages
]
```

#### C. Context Injection
- **File summaries** added as user messages before user's question
- **Previous summaries** from session injected if no new files
- **Mode headers** guide response structure
- **System prompts** define tone and behavior

---

### 4. **Response Generation**

#### A. API Call Configuration

**Model:** GPT-4o  
**Temperature:** 0.5 (balanced)  
**Messages:** Complete chat history with system prompts  
**Timeout:** 25 seconds (explicit timeout to prevent Railway 502 errors)

**Why Temperature 0.5:**
- **0.3** = More accurate but robotic
- **0.6** = More creative but less precise
- **0.5** = Balanced - accurate medical info with warm, human tone

#### B. Response Processing

**Direct Return:**
- Response returned immediately (no post-processing)
- Markdown preserved for frontend rendering
- Emojis included (per tone instructions)
- Conversation-ending prevention built into prompt

**Error Handling:**
- **Timeout errors** → Suggest fewer images
- **Gateway errors** → Retry-friendly message
- **Processing errors** → Generic error with support contact

---

## Special Processing Modes

### 1. **Image Analysis Mode**

**Trigger:** When medical images are uploaded

**Override Behavior:**
- Replaces FULL BREAKDOWN mode instructions
- Uses specialized image analysis format
- Two-pass approach for accuracy + warmth

**Format:**
```
1. Warm introduction (what images show, not diagnosing)
2. Big picture first - brief summary
3. Break down by anatomical region with specific observations
4. Compare dates if visible
5. Overall meaning in everyday language
6. When to seek urgent attention (specific red flags)
```

**Key Phrases:**
- "These images show..."
- "You can clearly see..."
- "What stands out..."
- "This typically means..."

**Avoid:**
- Generic advice sections
- "Common signs:", "What you can do:", "When to seek help:"

---

### 2. **Text Document Mode**

**Trigger:** When PDF/DOCX/TXT files are uploaded

**Process:**
1. Extract text from document
2. First pass: Summarize (temperature 0.4)
3. Second pass: Tone polish (temperature 0.3)
4. Save to `MedicalSummary` model (if authenticated)
5. Inject into chat context

**Why Two-Pass:**
- **First pass** focuses on accuracy and completeness
- **Second pass** ensures tone matches user's selected mode
- **Better quality** than single-pass for complex documents

---

### 3. **Quick Mode (PlainClinical Only)**

**Trigger:** Single short symptom (<12 words), no files

**Response Structure:**
- Gentle acknowledgment with emoji
- 2-4 safe immediate actions (with emojis)
- 1 clear red flag
- 1 soft follow-up invitation
- **Maximum:** 5 sentences

**Example:**
```
I understand you're experiencing [symptom]. 😊 Here are some safe steps you can try:
• [Action 1] 🧘
• [Action 2] 💧
• [Action 3] 📝

⚠️ Seek immediate care if [red flag].

Does this align with what you're experiencing? 😊
```

---

### 4. **Explain Mode (PlainClinical Only)**

**Trigger:** General health question, no files

**Response Structure:**
- What it is (with emoji)
- Common signs or causes (with emojis)
- Simple prevention or management (with emojis)
- Invitation to explore further (with emoji)
- **Length:** 2-4 sentences
- **No clinician notes** unless asked

---

### 5. **Full Breakdown Mode**

**Trigger:** Files uploaded OR detailed description OR follow-up

**Response Structure:**
- Short conversational lead-in with emoji (no "Introduction" heading)
- Common signs (3-5 bullets with emojis)
- What you can do now (3-5 bullets with emojis)
- When to seek medical help (2-4 bullets with emojis)
- Clinician notes (only when relevant, 1-4 concise points with emojis)
- Warm conversational close with emoji

**Key:** Never ends conversation - always invites continuation

---

## Response Quality Features

### 1. **Conversation Persistence**

**Built into All Prompts:**
- **NEVER** end conversations
- **NEVER** use closing phrases like "feel free to ask", "I'm here to help"
- **ALWAYS** end with engaging follow-up questions
- **ALWAYS** invite continuation

**Examples of Good Endings:**
- "What else would you like to know?"
- "Tell me more about..."
- "How does that compare to what you've experienced?"
- "Want me to suggest some next steps for your situation?"

---

### 2. **Emoji Usage**

**Policy:** Use emojis naturally and frequently throughout responses

**Purpose:**
- Add warmth and emotional connection
- Improve clarity and visual organization
- Make responses more engaging and human-like
- Similar to ChatGPT's approach

**Tone-Specific:**
- **PlainClinical:** Balanced emoji usage
- **Caregiver:** Warm, supportive emojis
- **Clinical:** Organizational emojis for scannability
- **EmotionalSupport:** Extra emojis for empathy

---

### 3. **Medical Safety**

**Principles:**
- **Guidance Without Diagnosis** - Never diagnose
- **Accuracy Without Alarmism** - Don't cause unnecessary worry
- **Clarity Before Complexity** - Simplify but don't oversimplify
- **Red flags always mentioned** - Safety first

**Built-in Safeguards:**
- System prompts emphasize medical accuracy
- Never substitutes faith/spirituality for medical care
- Always encourages professional care when needed
- Maintains HIPAA compliance in processing

---

## Performance Optimizations

### 1. **Single-Pass Response Generation**
- **Before:** Two API calls (generate + polish)
- **After:** One API call (generate with comprehensive prompt)
- **Result:** ~50% faster, ~50% cheaper

### 2. **Batch Image Processing**
- **5+ images:** Process in batches of 2-3
- **Prevents timeouts:** Stays under 25-second limit
- **Better context:** Processes related images together

### 3. **History Trimming**
- **Database:** Keeps last 200 messages
- **Session:** Keeps last 10 messages
- **Prevents:** Token limit issues, slow responses

### 4. **Timeout Management**
- **Explicit 25-second timeout** on all API calls
- **Prevents Railway 502 errors**
- **User-friendly error messages** for timeouts

---

## Error Handling

### 1. **Timeout Errors**
```python
if "timeout" in error_msg or "502" in error_msg:
    return JsonResponse({
        "reply": "The image analysis is taking longer than expected. Please try with fewer images (5 or less) or try again in a moment.",
        "error": "TIMEOUT"
    }, status=504)
```

### 2. **Processing Errors**
```python
return JsonResponse({
    "reply": "Sorry, something went wrong while processing your request. Please try again with fewer images or contact support if this persists.",
    "error": "PROCESSING_ERROR"
}, status=500)
```

### 3. **File Processing Failures**
- Individual file failures don't stop entire request
- Failed files marked as "(Unable to process this image)"
- Other files still processed successfully

---

## Session Management

### 1. **Sticky Sessions**

**Authenticated Users:**
- Server maintains `active_chat_session_id` in session
- Client can override with `session_id` in request
- Prefers client-provided ID, falls back to server-sticky ID

**Guest Users:**
- Session-based chat history
- Lost on logout/clear cookies
- Limited to 10 messages

### 2. **Auto-Titling**

**Process:**
1. Check if title is placeholder ("new chat", "untitled", "")
2. Try AI-generated title (lightweight model)
3. Fall back to derived title (from user message/files)
4. Update session title

**AI Title Generation:**
- Uses `gpt-4o-mini` for cost efficiency
- Generates concise, PHI-safe titles
- Falls back silently on errors

---

## Language Support

### 1. **Bilingual Responses**

**Implementation:**
- Language instruction appended to system prompt
- Function: `_add_language_instruction(system_prompt, lang)`
- Format: `"(Always respond in {lang} unless told otherwise.)"`

**Supported:**
- Any language code (en-US, es-ES, fr-FR, etc.)
- Works with all tones
- Maintains tone characteristics in target language

---

## Key Design Decisions

### 1. **Why Single-Pass Instead of Two-Pass?**

**Trade-offs:**
- ✅ **Faster** - Half the latency
- ✅ **Cheaper** - Half the API calls
- ✅ **Still high quality** - Comprehensive system prompts
- ⚠️ **Slightly less polished** - But acceptable for speed gain

**Decision:** Speed and cost efficiency prioritized while maintaining quality

---

### 2. **Why Two-Pass for Images/Documents?**

**Reason:**
- **First pass** focuses on accuracy and completeness
- **Second pass** ensures tone and warmth
- **Better quality** for complex medical content
- **Worth the extra time** for file analysis

**Exception:** Text-only chat uses single-pass

---

### 3. **Why Temperature 0.5?**

**Balance:**
- Medical accuracy requires lower temperature (0.3-0.4)
- Warm, human tone requires higher temperature (0.6-0.7)
- **0.5 = Sweet spot** - Accurate medical info with warm tone

---

## Future Considerations

### Potential Improvements:
1. **Streaming responses** - Show partial responses as they generate
2. **Response caching** - Cache common questions
3. **Multi-model support** - Use faster models for simple queries
4. **Response validation** - Post-process to ensure safety
5. **A/B testing** - Test different temperature/approach combinations

---

## Code Locations

- **Main chat handler:** `myApp/views.py` lines 1353-1781
- **Mode classification:** `myApp/views.py` lines 289-311
- **System prompt building:** `myApp/views.py` lines 314-324
- **Image processing:** `myApp/views.py` lines 705-944
- **Document processing:** `myApp/views.py` lines 3065-3126
- **Tone prompts:** `myApp/views.py` lines 328-529

---

**Document Generated:** January 2025  
**Maintained By:** Development Team
