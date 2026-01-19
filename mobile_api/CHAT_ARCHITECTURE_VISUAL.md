# 🏗️ NeuroMed Aira Chat Architecture - Visual Guide

---

## 🎨 **The Complete Tone System**

```
┌─────────────────────────────────────────────────────────────┐
│                    NeuroMed Aira TONES                        │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ PlainClinical│  │  Caregiver   │  │    Faith     │
│   (Default)  │  │              │  │              │
│              │  │              │  │              │
│ • 3 Modes    │  │ • Gentle     │  │ • Hopeful    │
│ • Auto adapt │  │ • Reassuring │  │ • Spiritual  │
│ • General    │  │ • Practical  │  │ • 6 faiths   │
└──────────────┘  └──────────────┘  └──────────────┘

┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Clinical   │  │  Geriatric   │  │  Emotional   │
│              │  │              │  │   Support    │
│ • SOAP notes │  │ • Older      │  │              │
│ • Quick-Scan │  │   adults     │  │ • Validates  │
│ • For MDs    │  │ • Caregivers │  │ • Reduces    │
│ • 3 settings │  │ • Practical  │  │   fear       │
└──────────────┘  └──────────────┘  └──────────────┘

Note: Language support is handled separately via the `lang` parameter.
      Any tone can be used with any supported language.
```

---

## 📊 **PlainClinical - The Smart Mode System**

```
USER INPUT → ANALYZER → MODE SELECTION → AI RESPONSE

┌─────────────────────────────────────────────────────────────┐
│                     INPUT ANALYZER                          │
└─────────────────────────────────────────────────────────────┘

Input: "headache"
├─ Word count: 1 (< 12)
├─ Files: None
├─ Detailed: No
└─ Result: QUICK MODE ⚡

Input: "What is diabetes?"
├─ Word count: 14 (≥ 12)
├─ Files: None
├─ Detailed: No
└─ Result: EXPLAIN MODE 📖

Input: "headache for 3 days with nausea"
├─ Word count: 13 (≥ 12)
├─ Files: None
├─ Detailed: Yes (multiple symptoms)
└─ Result: FULL MODE 📋

Input: [uploads medical file]
├─ Word count: Any
├─ Files: Yes
├─ Detailed: Auto yes
└─ Result: FULL MODE 📋
```

---

## ⚡ **QUICK MODE (< 5 sentences)**

```
┌─────────────────────────────────────────────┐
│ QUICK MODE STRUCTURE                        │
└─────────────────────────────────────────────┘

[1] Empathy sentence
    ↓
[2] 2-4 immediate safe actions
    ↓
[3] 1 urgent red flag warning
    ↓
[4] 1 follow-up question
    ↓
[5] Gentle invitation

Example:
─────────────────────────────────────────────
Headaches can be frustrating. Try resting 
in a quiet, dark room and staying hydrated. 
If you have a severe headache, vision changes, 
or stiff neck, seek care right away. 
Does that sound like what you're feeling?
─────────────────────────────────────────────

Word count: ~50-80 words
Response time: ~3-5 seconds
```

---

## 📖 **EXPLAIN MODE (2-4 sentences)**

```
┌─────────────────────────────────────────────┐
│ EXPLAIN MODE STRUCTURE                      │
└─────────────────────────────────────────────┘

[1] What it is (1-2 sentences)
    ↓
[2] Common signs (1 sentence)
    ↓
[3] Management basics (1-2 sentences)
    ↓
[4] Curious invitation

Example:
─────────────────────────────────────────────
High blood pressure is when the force of 
blood against artery walls stays too high. 
Common signs include headaches, dizziness, 
or often no symptoms at all. You can manage 
it with less salt, regular exercise, and 
prescribed medications. Would you like me 
to go into daily tips?
─────────────────────────────────────────────

Word count: ~80-120 words
Response time: ~4-6 seconds
```

---

## 📋 **FULL MODE (Structured Sections)**

```
┌─────────────────────────────────────────────┐
│ FULL BREAKDOWN MODE STRUCTURE               │
└─────────────────────────────────────────────┘

Lead-in (1-2 sentences, no heading)
    ↓
Common signs
• Point 1
• Point 2
• Point 3
• Point 4
• Point 5
    ↓
What you can do
• Action 1
• Action 2
• Action 3
• Action 4
• Action 5
    ↓
When to seek help
• Warning 1
• Warning 2
• Warning 3
• Warning 4
    ↓
For clinicians (if relevant)
• Clinical point 1
• Clinical point 2
• Clinical point 3
• Clinical point 4
    ↓
Conversational handoff question

Example:
─────────────────────────────────────────────
When a headache lasts several days and comes 
with nausea, it's worth paying attention.

Common signs
• Persistent throbbing pain, often on one side
• Nausea or sensitivity to light/sound
• May get worse with activity
• Can disrupt sleep and daily routines

What you can do
• Rest in a quiet, dark room
• Stay well-hydrated
• Try a cold compress
• Avoid bright screens
• Keep a headache diary

When to seek help
• Worst headache of your life
• Sudden onset with confusion
• Persistent vomiting
• Stiff neck or weakness

Is this close to what you're noticing?
─────────────────────────────────────────────

Word count: ~150-300 words
Response time: ~8-12 seconds
```

---

## 🩺 **CLINICAL MODE (SOAP + Quick-Scan)**

```
┌─────────────────────────────────────────────┐
│ CLINICAL MODE STRUCTURE                     │
└─────────────────────────────────────────────┘

🩺 SOAP Note:

Subjective:
[Patient presentation, symptoms, timeline]
    ↓
Objective:
[Labs with normal ranges]
[Vitals, exam findings]
[Abnormalities flagged: ↑ or ↓]
    ↓
Assessment:
[Clinical impression]
[Differential considerations]
    ↓
Plan:
[Confirmatory steps: repeat labs, imaging]
[Safety checks: ECG, bleeding precautions]
[Escalation thresholds: when to escalate]

─────────────────────────────────────────────

⚡ Quick-Scan Card:

🔴 K+ 5.8 (↑ N:3.5-5.0) → Repeat, ECG, Check osmolality
🟡 WBC 11.2 (↑) → Differential, Consider infection
🟢 Cr 0.9 (N) → Continue monitoring
🟡 Glucose 142 (↑) → Recheck fasting, A1C

─────────────────────────────────────────────

[Want me to expand into a differential?]

Word count: ~300-500 words
Format: Structured medical documentation
Audience: Healthcare professionals
```

---

## 🧠 **Smart Context Memory**

```
┌─────────────────────────────────────────────┐
│ SOFT MEMORY SYSTEM (15 minute TTL)         │
└─────────────────────────────────────────────┘

Time 0:00
User: "headache"
System: [QUICK MODE response]
Memory: Stores "headache" + mode + timestamp
    ↓
Time 0:05 (within 15 min)
User: "it's been getting worse for 3 days"
System: Detects soft memory
        Upgrades: QUICK → FULL
        Includes: "headache" context
        Response: Full breakdown with context
    ↓
Time 0:20 (after 15 min)
User: "what about nausea"
System: Memory expired
        Treats as new QUICK
        No context from "headache"

TTL: 15 minutes
Upgrade: QUICK → FULL only
Context: Last short message saved
```

---

## 🔄 **Complete Processing Flow**

```
┌───────────────────────────────────────────────────────────┐
│                    CHAT REQUEST FLOW                      │
└───────────────────────────────────────────────────────────┘

1. User Input
   ├─ Message text
   ├─ Tone selection
   ├─ Language preference
   ├─ Optional: care_setting
   ├─ Optional: faith_setting
   └─ Optional: files
         ↓
2. Tone Normalization
   ├─ "Plain" → "PlainClinical"
   ├─ "Science" → "PlainClinical"
   └─ Unknown → "PlainClinical" (default)
         ↓
3. Mode Classification (PlainClinical only)
   ├─ Has files? → FULL
   ├─ Detailed? (≥12 words) → FULL
   ├─ Short? (<12 words) → QUICK
   └─ General question? → EXPLAIN
         ↓
4. System Prompt Building
   ├─ Base prompt (tone)
   ├─ + Care setting (if Clinical/Caregiver)
   ├─ + Faith setting (if Faith)
   ├─ + Language instruction
   └─ + ResponseMode header
         ↓
5. OpenAI Processing
   ├─ Pass 1: Generate (temp: 0.6)
   └─ Pass 2: Polish (temp: 0.3)
         ↓
6. Response Formatting
   ├─ Add message ID
   ├─ Add timestamp
   ├─ Add session_id
   └─ Return JSON
         ↓
7. Storage (if authenticated)
   ├─ Save to ChatSession
   ├─ Update session title
   └─ Trim history (keep last 200)
```

---

## 🎯 **Your iOS App Should:**

### **1. Provide Tone Selection UI:**
```swift
// Segmented control or picker
Tone: [ Plain | Caregiver | Faith | Clinical | ... ]
```

### **2. Conditional Settings:**
```swift
// Only show if Clinical/Caregiver selected:
Setting: [ Hospital | Clinic | Urgent Care ]

// Only show if Faith selected:
Faith: [ General | Christian | Muslim | ... ]
```

### **3. Send Complete Request:**
```json
{
    "message": "user text",
    "tone": "PlainClinical",
    "language": "en-US",
    "care_setting": "hospital",    // if applicable
    "faith_setting": "christian",  // if applicable
    "session_id": "abc-123"        // if continuing conversation
}
```

### **4. Display Response:**
```swift
// Show AI response with proper formatting
// Preserve bullet points and sections
// No need to parse markdown (backend doesn't send it)
```

---

## 📊 **Tone Usage Recommendations**

```
General Public       → PlainClinical (default)
Family Caregivers    → Caregiver
Religious Users      → Faith
Healthcare Workers   → Clinical
Elderly/Families     → Geriatric
Anxious/Scared       → EmotionalSupport
Non-English          → Use `lang` parameter with any tone
```

---

## 🎉 **Summary**

**Tones:** 6 main options (language handled separately via `lang` parameter)  
**Modes:** 3 (QUICK, EXPLAIN, FULL) - auto-selected  
**Layers:** Tone → Mode → Care/Faith Setting → Language  
**Format:** No markdown, conversational, structured sections  
**Processing:** Two-pass AI (accuracy + warmth)  
**Memory:** 15-minute soft context for upgrades  

**Your chat system is incredibly sophisticated!** 🚀

