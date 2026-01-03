# 💬 NeuroMed AI Chat System - Complete Guide

**How Your AI Chat Works - Tones, Modes, Layers & Format**

---

## 🎨 **TONES - 6 Different Personalities**

Your chat system has **6 tones** that change how the AI responds:

### **1. PlainClinical** (Default)
**Who it's for:** General users, patients, families  
**Style:** Warm but precise, friendly and confident  
**Special Feature:** Has 3 automatic response modes (see below)  
**Aliases:** "plain", "science", "default", "balanced"

### **2. Caregiver**
**Who it's for:** Family caregivers, people caring for loved ones  
**Style:** Comforting, gentle, reassuring  
**Focus:** Practical next steps with warmth  
**Always:** Ends by inviting caregiver to share more

### **3. Faith**
**Who it's for:** Users who want spiritual comfort  
**Style:** Faith-filled, hopeful, peaceful  
**Special Feature:** Can include Bible verses or prayers  
**Subtypes:** Christian, Muslim, Hindu, Buddhist, Jewish, General

### **4. Clinical**
**Who it's for:** Healthcare professionals (doctors, nurses)  
**Style:** Medical-first, structured, evidence-based  
**Output:** SOAP notes + Quick-Scan Cards  
**Format:** 
- Structured SOAP (Subjective, Objective, Assessment, Plan)
- Quick-Scan Card with emoji codes for rapid review
- Action-driven recommendations with urgency thresholds

### **5. Geriatric**
**Who it's for:** Older adults and their families  
**Style:** Respectful, unhurried, practical  
**Focus:** Fall risk, frailty, polypharmacy, cognitive changes, mobility  
**Special:** Addresses advance care planning, family huddles

### **6. EmotionalSupport**
**Who it's for:** People feeling anxious or scared  
**Style:** Validating, fear-reducing, compassionate  
**Always:** Acknowledges emotions first, provides comfort  
**Focus:** Self-kindness, gentle next steps, reassurance

---

## 📊 **LAYERS - 3 Response Modes (PlainClinical Only)**

Your PlainClinical tone has **smart layers** that automatically adapt based on context:

### **Layer 1: QUICK MODE** ⚡
**Triggers When:**
- User sends a short message (< 12 words)
- No files/images attached
- Single symptom or simple question

**Example Input:** "headache"

**Response Format:**
- Under 5 sentences
- Empathy + 2-4 safe immediate actions
- 1 urgent red flag to watch for
- 1 follow-up question
- Gentle open-ended invitation

**Example Output:**
```
Headaches can be frustrating. Try resting in a quiet, dark room and staying hydrated. 
If you have a severe headache, vision changes, or stiff neck, seek care right away. 
Does that sound like what you're feeling?
```

**Word Count:** ~50-80 words  
**Tone:** Quick, empathetic, actionable

---

### **Layer 2: EXPLAIN MODE** 📖
**Triggers When:**
- User asks a general question (12+ words)
- No files/images attached
- Educational/informational query

**Example Input:** "What is high blood pressure and how do I manage it?"

**Response Format:**
- 2-4 sentences in plain language
- What it is
- Common signs
- Basic prevention/management
- No clinician notes
- Curious invitation to dig deeper

**Example Output:**
```
High blood pressure is when the force of blood against artery walls stays too high over time. 
Common signs include headaches, dizziness, or often no symptoms at all. 
You can help manage it with less salt, regular exercise, stress reduction, and taking medications as prescribed. 
Would you like me to go into daily tips or food choices that help?
```

**Word Count:** ~80-120 words  
**Tone:** Educational, conversational, inviting

---

### **Layer 3: FULL BREAKDOWN MODE** 📋
**Triggers When:**
- ANY file or image is uploaded
- Detailed description (multiple symptoms, history)
- Follow-up to QUICK mode (within 15 minutes)

**Example Input:** "headache for 3 days with nausea" OR [uploads medical file]

**Response Format:**
```
[1-2 sentence lead-in - no heading]

Common signs
• [3-5 bullet points]

What you can do
• [3-5 bullet points]

When to seek help
• [2-4 bullet points]

For clinicians (if relevant)
• [1-4 concise points]

[Warm conversational handoff question]
```

**Example Output:**
```
When a headache lasts several days and comes with nausea, it's worth paying attention.

Common signs
• Persistent throbbing pain, often on one side
• Nausea or sensitivity to light/sound
• May get worse with activity
• Can disrupt sleep and daily routines

What you can do
• Rest in a quiet, dark room
• Stay well-hydrated
• Try a cold compress on your forehead
• Avoid triggers like bright screens or loud noise
• Keep a headache diary to spot patterns

When to seek help
• If it's the worst headache of your life
• Sudden onset with confusion or vision changes
• Persistent vomiting or high fever
• Stiff neck or weakness on one side

Is this close to what you're noticing?
```

**Word Count:** ~150-300 words  
**Tone:** Comprehensive, structured, warm  
**No Markdown:** No **, ##, or formatting symbols

---

## 🏥 **CARE SETTINGS (Clinical & Caregiver Tones Only)**

When using Clinical or Caregiver tone, you can add **care setting context**:

### **1. Hospital (Inpatient/Discharge)** 🏥
**Context:** Hospital stays, discharge planning  
**Banner:** `[Inpatient / Discharge Handoff]`

**Sections:**
- Handoff Highlights (3-6 bullets)
- Discharge Plan (3-6 bullets)
- Safety & Red Flags (2-4 bullets)
- For Clinicians (1-4 points if relevant)

---

### **2. Ambulatory (Outpatient/Clinic)** 🏪
**Context:** Clinic visits, follow-ups  
**Banner:** `[Clinic Follow-Up]`

**Sections:**
- Clinic Snapshot (3-5 bullets)
- Today's Plan (3-6 bullets)
- What to Watch (2-4 bullets)

---

### **3. Urgent (Urgent Care/ER)** 🚨
**Context:** Urgent care, emergency triage  
**Banner:** `[Urgent Care Triage]`

**Sections:**
- Quick Triage Card (5-7 bullets)
- Immediate Steps (3-5 bullets)
- Return / ER Criteria (3-5 bullets)

---

## 🙏 **FAITH SETTINGS (Faith Tone Only)**

When using Faith tone, you can specify religious tradition:

### **Options:**
1. **General** - Spiritual but non-specific
2. **Christian** - May include Bible verses or prayers
3. **Muslim** - May include duas or Quran verses
4. **Hindu** - May include Bhagavad Gita wisdom
5. **Buddhist** - May include Dharma teachings
6. **Jewish** - May include Jewish tradition wisdom

**How It Works:**
- Base medical explanation stays the same
- Closing includes faith-appropriate comfort
- Respectful and optional

---

## 🌍 **LANGUAGE SUPPORT**

Language is handled separately from tone via the `lang` parameter in requests.

### **Supported Languages:**
- English (en-US) - Default
- Spanish (es-ES, es-MX)
- French (fr-FR)
- German (de-DE)
- Japanese (ja-JP)
- Korean (ko-KR)
- Arabic (ar-SA)
- And more (via standard language codes)

### **How It Works:**
1. Set `lang` parameter in your request (e.g., `"lang": "es-ES"`)
2. AI responds in the specified language
3. Tone and language work independently - you can use any tone with any language

**Note:** Language preference is separate from tone selection. The `lang` parameter controls the response language, while `tone` controls the style/personality of the response.

---

## 🧠 **SOFT MEMORY - Smart Context Tracking**

**Feature:** The system remembers recent conversation for 15 minutes

**How It Works:**

1. **User sends:** "headache" → Gets QUICK response
2. **Within 15 minutes, user sends:** "it's been 3 days" → Automatically upgrades to FULL mode
3. **Topic hint:** System remembers "headache" and gives more detailed info

**TTL:** 15 minutes  
**Upgrade:** QUICK → FULL automatically  
**Memory:** Last mode, last message, timestamp

---

## 🔄 **Complete Chat Flow**

### **Step 1: User Input Arrives**
```python
{
    "message": "headache",
    "tone": "PlainClinical",
    "language": "en-US",
    "care_setting": null,
    "faith_setting": null,
    "files[]": []  # No files
}
```

### **Step 2: System Classifies**
```python
# Message: "headache" (1 word)
# Has files: No
# Classification: QUICK MODE
mode = "QUICK"
```

### **Step 3: Build System Prompt**
```python
tone = "PlainClinical"
system_prompt = get_system_prompt(tone)
# Adds: "ResponseMode: QUICK" header
```

### **Step 4: Call OpenAI**
```python
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "system", "content": "ResponseMode: QUICK"},
    {"role": "user", "content": "headache"}
]

# First pass: Raw response
raw = gpt-4o.generate(messages)

# Second pass: Polish tone
polished = gpt-4o.polish(raw)
```

### **Step 5: Return to User**
```json
{
    "reply": "Headaches can be frustrating. Try resting in a quiet...",
    "session_id": "abc-123-def"
}
```

---

## 📐 **Response Design Format**

### **QUICK Mode Format:**
```
[Empathy sentence]
[Action 1]. [Action 2]. [Action 3].
[Red flag warning].
[Follow-up question]?
```

### **EXPLAIN Mode Format:**
```
[What it is - 1-2 sentences]
[Common signs - 1 sentence]
[Management - 1-2 sentences]
[Curious invitation]?
```

### **FULL Mode Format:**
```
[Lead-in paragraph - no heading]

Common signs
• [Point 1]
• [Point 2]
• [Point 3]

What you can do
• [Action 1]
• [Action 2]
• [Action 3]

When to seek help
• [Warning 1]
• [Warning 2]

For clinicians (if relevant)
• [Clinical point 1]

[Conversational question]?
```

### **Clinical Mode Format:**
```
🩺 SOAP Note:

Subjective:
[Patient presentation, symptoms, history]

Objective:
[Labs, vitals, exam findings with normal ranges]
[Abnormalities flagged: e.g., K+ 5.8 (↑ normal 3.5-5.0)]

Assessment:
[Clinical impression, differential considerations]

Plan:
[Confirmatory steps: repeat labs, ECG]
[Safety checks: bleeding precautions if thrombocytopenic]
[Escalation thresholds: urgent if K+ >6.0 or ECG changes]

---

⚡ Quick-Scan Card:

🔴 K+ 5.8 (↑) → Repeat CBC, Check osmolality, Obtain ECG
🟡 WBC 11.2 (↑) → CBC differential, Consider infection workup
🟢 Cr 0.9 (N) → Continue monitoring

[Want me to expand into a differential?]
```

---

## 🎯 **How Modes Auto-Select**

```python
def choose_mode(message, files):
    # Has files? → Always FULL
    if files:
        return "FULL"
    
    # Long/detailed message? → FULL
    if word_count(message) >= 12:
        return "FULL"
    
    # Short message? → QUICK
    if word_count(message) < 12:
        return "QUICK"
    
    # General question? → EXPLAIN
    return "EXPLAIN"
```

**Smart Upgrade:**
If user sends QUICK, then within 15 minutes sends more details → Auto-upgrades to FULL with context retention

---

## 📱 **For Your iOS App**

### **What to Send:**
```json
{
    "message": "User's message text",
    "tone": "PlainClinical",        // Optional, default: "PlainClinical"
    "language": "en-US",             // Optional, default: "en-US"
    "care_setting": "hospital",      // Optional, for Clinical/Caregiver only
    "faith_setting": "christian",    // Optional, for Faith only
    "session_id": "abc-123"          // Optional
}
```

### **What You Get Back:**
```json
{
    "id": "msg-uuid",
    "role": "assistant",
    "content": "AI response here...",
    "timestamp": "2025-10-24T14:01:16+00:00",
    "session_id": "abc-123",
    "metadata": null
}
```

### **Available Tone Values:**
```swift
enum Tone: String {
    case plainClinical = "PlainClinical"
    case caregiver = "Caregiver"
    case faith = "Faith"
    case clinical = "Clinical"
    case geriatric = "Geriatric"
    case emotionalSupport = "EmotionalSupport"
}
```

### **Available Care Settings** (Clinical/Caregiver only):
```swift
enum CareSetting: String {
    case hospital = "hospital"      // Default
    case ambulatory = "ambulatory"  // Outpatient/Clinic
    case urgent = "urgent"          // Urgent Care/ER
}
```

### **Available Faith Settings** (Faith only):
```swift
enum FaithSetting: String {
    case general = "general"        // Default
    case christian = "christian"
    case muslim = "muslim"
    case hindu = "hindu"
    case buddhist = "buddhist"
    case jewish = "jewish"
}
```

---

## 🔄 **Complete Tone Combinations**

### **Example 1: Plain Clinical (Default)**
```json
{
    "message": "headache",
    "tone": "PlainClinical"
}
```
**Response:** Quick, warm, actionable advice

---

### **Example 2: Clinical with Hospital Setting**
```json
{
    "message": "Patient with fever and elevated WBC",
    "tone": "Clinical",
    "care_setting": "hospital"
}
```
**Response:** SOAP note + Quick-Scan Card with discharge planning

---

### **Example 3: Faith with Christian Setting**
```json
{
    "message": "I'm worried about my diagnosis",
    "tone": "Faith",
    "faith_setting": "christian"
}
```
**Response:** Medical explanation + Bible verse/prayer for comfort

---

### **Example 4: Caregiver with Ambulatory Setting**
```json
{
    "message": "How do I help my mom with her medications?",
    "tone": "Caregiver",
    "care_setting": "ambulatory"
}
```
**Response:** Gentle clinic-focused guidance for caregivers

---

### **Example 5: Spanish Language with Caregiver Tone**
```json
{
    "message": "dolor de cabeza",
    "tone": "Caregiver",
    "lang": "es-ES"
}
```
**Response:** Warm, caregiver-style explanation in Spanish

---

## 🎨 **Design Principles**

### **All Tones Follow:**
1. ✅ **No markdown** - No **, ##, or formatting symbols
2. ✅ **Conversational** - Like talking to a helpful friend
3. ✅ **No robotic phrases** - Human and warm
4. ✅ **Always ends with question** - Keeps dialogue going
5. ✅ **Clear structure** - Easy to scan and read
6. ✅ **Actionable** - Always gives next steps
7. ✅ **Safe** - Highlights urgent warnings when needed

### **Formatting Rules:**
```
✅ DO use bullet points (•)
✅ DO use section headings (plain text)
✅ DO use clear paragraphs
✅ DO use emoji in Clinical mode Quick-Scan Cards

❌ DON'T use **bold** markdown
❌ DON'T use ## headers
❌ DON'T use technical jargon (unless Clinical mode)
❌ DON'T give disclaimers or robotic warnings
❌ DON'T write "Introduction" as a heading
```

---

## 🧪 **How to Test Different Tones in iOS**

### **Test 1: Quick Response**
```swift
let request = SendChatRequest(
    message: "headache",
    tone: "PlainClinical",
    sessionId: nil
)
// Expected: Short, quick advice (QUICK MODE)
```

### **Test 2: Detailed Response**
```swift
let request = SendChatRequest(
    message: "I've had a headache for 3 days with nausea and light sensitivity",
    tone: "PlainClinical",
    sessionId: nil
)
// Expected: Full breakdown with sections (FULL MODE)
```

### **Test 3: Clinical Mode**
```swift
let request = SendChatRequest(
    message: "Patient with K+ 5.8, Cr 1.2, WBC 11",
    tone: "Clinical",
    careSetting: "hospital",
    sessionId: nil
)
// Expected: SOAP note + Quick-Scan Card
```

### **Test 4: Faith Mode**
```swift
let request = SendChatRequest(
    message: "I'm scared about my surgery",
    tone: "Faith",
    faithSetting: "christian",
    sessionId: nil
)
// Expected: Comfort + Bible verse
```

---

## 🔧 **iOS Request Model**

### **Complete SendChatRequest:**
```swift
struct SendChatRequest: Codable {
    let message: String
    let tone: String?
    let language: String?
    let careSetting: String?
    let faithSetting: String?
    let sessionId: String?
    
    enum CodingKeys: String, CodingKey {
        case message
        case tone
        case language
        case careSetting = "care_setting"
        case faithSetting = "faith_setting"
        case sessionId = "session_id"
    }
    
    init(message: String, 
         tone: String? = nil,
         language: String? = nil,
         careSetting: String? = nil,
         faithSetting: String? = nil,
         sessionId: String? = nil) {
        self.message = message
        self.tone = tone
        self.language = language
        self.careSetting = careSetting
        self.faithSetting = faithSetting
        self.sessionId = sessionId
    }
}
```

---

## 📊 **Tone Comparison Matrix**

| Tone | Use Case | Length | Style | Special Features |
|------|----------|--------|-------|------------------|
| PlainClinical | General users | Variable (3 modes) | Warm, precise | Auto mode selection |
| Caregiver | Family caregivers | Medium | Gentle, reassuring | Caregiver focus |
| Faith | Spiritual comfort | Medium | Hopeful, peaceful | Scripture/prayers |
| Clinical | Healthcare pros | Long | Structured, medical | SOAP + Quick-Scan |
| Geriatric | Older adults | Medium-Long | Respectful, practical | Geriatric syndromes |
| EmotionalSupport | Anxious users | Medium | Validating, comforting | Emotion-first |

---

## 💡 **Backend AI Processing**

### **Two-Pass System:**

**Pass 1: Generate Raw Response**
```python
raw = openai.chat.completions.create(
    model="gpt-4o",
    temperature=0.6,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": "ResponseMode: QUICK"},
        {"role": "user", "content": user_message}
    ]
)
```

**Pass 2: Polish Tone**
```python
polished = openai.chat.completions.create(
    model="gpt-4o",
    temperature=0.3,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Rewrite warmly, clearly, confidently:\n\n{raw}"}
    ]
)
```

**Why Two Passes:**
- First pass: Get medically accurate content
- Second pass: Perfect the warm, conversational tone
- Result: Accurate AND human-feeling responses

---

## 🎯 **For Mobile API Implementation**

### **Current Status:**
```python
# In mobile_api/compat_views.py - send_chat()
# Currently returns STUB:
ai_response = f"Hello! You said: {message}"
```

### **To Connect Real AI:**
```python
# Import the real chat logic from myApp:
from myApp.views import (
    normalize_tone,
    get_system_prompt,
    _classify_mode,
    _now_ts
)

# In send_chat endpoint:
tone = normalize_tone(request.data.get("tone"))
mode, topic_hint = _classify_mode(user_message, has_files=False, session=request.session)

# Build messages
system_prompt = get_system_prompt(tone)
header = f"ResponseMode: {mode}"

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "system", "content": header},
    {"role": "user", "content": user_message}
]

# Call OpenAI (two-pass)
raw = client.chat.completions.create(
    model="gpt-4o", 
    temperature=0.6, 
    messages=messages
).choices[0].message.content

polished = client.chat.completions.create(
    model="gpt-4o",
    temperature=0.3,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Rewrite warmly:\n\n{raw}"}
    ]
).choices[0].message.content

return Response({
    "id": str(uuid.uuid4()),
    "role": "assistant",
    "content": polished,
    "timestamp": timezone.now().isoformat(),
    "session_id": session_id,
    "metadata": None
})
```

---

## 🎨 **UI Design Recommendations for iOS**

### **Tone Selector:**
```swift
Picker("Tone", selection: $selectedTone) {
    Text("Plain").tag("PlainClinical")
    Text("Caregiver").tag("Caregiver")
    Text("Faith").tag("Faith")
    Text("Clinical").tag("Clinical")
    Text("Geriatric").tag("Geriatric")
    Text("Emotional Support").tag("EmotionalSupport")
}
```

### **Care Setting (Show only if Clinical/Caregiver):**
```swift
if selectedTone == "Clinical" || selectedTone == "Caregiver" {
    Picker("Setting", selection: $careSetting) {
        Text("Hospital").tag("hospital")
        Text("Clinic").tag("ambulatory")
        Text("Urgent Care").tag("urgent")
    }
}
```

### **Faith Setting (Show only if Faith):**
```swift
if selectedTone == "Faith" {
    Picker("Faith", selection: $faithSetting) {
        Text("General").tag("general")
        Text("Christian").tag("christian")
        Text("Muslim").tag("muslim")
        Text("Hindu").tag("hindu")
        Text("Buddhist").tag("buddhist")
        Text("Jewish").tag("jewish")
    }
}
```

---

## 📋 **Summary**

### **6 Tones:**
PlainClinical, Caregiver, Faith, Clinical, Geriatric, EmotionalSupport

### **3 Response Modes** (PlainClinical):
QUICK, EXPLAIN, FULL (auto-selected)

### **3 Care Settings** (Clinical/Caregiver):
Hospital, Ambulatory, Urgent

### **6 Faith Settings** (Faith):
General, Christian, Muslim, Hindu, Buddhist, Jewish

### **Languages:**
Multiple languages supported via `lang` parameter (en-US, es-ES, fr-FR, de-DE, ja-JP, ko-KR, ar-SA, etc.)

### **Processing:**
Two-pass OpenAI (raw → polished)

### **Format:**
No markdown, conversational, bullet points, warm tone

---

**Your chat system is sophisticated with multiple layers and contexts!** 🎉

For iOS implementation, see: `IOS_BACKEND_INTEGRATION_GUIDE.md`

