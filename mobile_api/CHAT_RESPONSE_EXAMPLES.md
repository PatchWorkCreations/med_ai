# 📝 Chat Response Examples - What Your iOS App Will Receive

---

## 🎯 **Response Format (All Tones)**

```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "role": "assistant",
    "content": "[AI response text here]",
    "timestamp": "2025-10-24T14:01:16.000000+00:00",
    "session_id": "abc-123-def",
    "metadata": null
}
```

**Note:** Only `content` changes based on tone/mode. Structure stays the same!

---

## ⚡ **PlainClinical - QUICK MODE**

### Input:
```json
{
    "message": "headache",
    "tone": "PlainClinical"
}
```

### Response Content:
```
Headaches can be frustrating, especially when they disrupt your day. 
Try resting in a quiet, dark room, staying hydrated, and taking an 
over-the-counter pain reliever if needed. If this headache is the 
worst you've ever had, comes with a stiff neck, vision changes, or 
confusion, seek medical care right away. Does that sound like what 
you're feeling, or is there more going on?
```

**Length:** 4-5 sentences (~60-80 words)  
**Sections:** None (flowing text)  
**Style:** Conversational, empathetic, quick

---

## 📖 **PlainClinical - EXPLAIN MODE**

### Input:
```json
{
    "message": "What is high blood pressure and how do I manage it?",
    "tone": "PlainClinical"
}
```

### Response Content:
```
High blood pressure (hypertension) is when the force of blood against 
your artery walls stays elevated over time, which can strain your heart 
and blood vessels. Common signs include occasional headaches or dizziness, 
though many people have no symptoms at all. You can help manage it by 
reducing salt intake, staying physically active, maintaining a healthy 
weight, limiting alcohol, and taking any prescribed medications consistently. 
Would you like me to go into daily tips or specific foods that help lower 
blood pressure?
```

**Length:** 3-4 sentences (~100-120 words)  
**Sections:** None (flowing text)  
**Style:** Educational, clear, inviting

---

## 📋 **PlainClinical - FULL MODE**

### Input:
```json
{
    "message": "I've had a headache for 3 days with nausea and sensitivity to light",
    "tone": "PlainClinical"
}
```

### Response Content:
```
When a headache lasts several days and comes with nausea and light sensitivity, 
it's worth paying close attention to what your body is telling you.

Common signs
• Persistent throbbing pain, often on one side of the head
• Nausea or vomiting
• Sensitivity to light, sound, or smells
• Pain that gets worse with physical activity
• May disrupt sleep, appetite, and daily routines

What you can do
• Rest in a quiet, dark room when the headache hits
• Stay well-hydrated throughout the day
• Try a cold compress on your forehead or neck
• Avoid known triggers like bright screens, loud noise, or certain foods
• Keep a headache diary to identify patterns
• Consider over-the-counter pain relievers early when symptoms start

When to seek help
• If this is the worst headache you've ever experienced
• Sudden onset with confusion, vision loss, or difficulty speaking
• Accompanied by high fever, stiff neck, or weakness on one side
• Persistent vomiting or signs of dehydration
• No improvement after 3-5 days despite rest and self-care

Is this close to what you're noticing, or are there other symptoms I should know about?
```

**Length:** 200-300 words  
**Sections:** 4-5 clear sections with headings  
**Style:** Comprehensive, structured, warm

---

## 💝 **Caregiver Tone**

### Input:
```json
{
    "message": "How do I help my elderly mother with her medications?",
    "tone": "Caregiver"
}
```

### Response Content:
```
Helping a loved one manage medications can feel overwhelming, but you're doing 
something truly caring. Start by creating a simple daily checklist or using a 
pill organizer with labeled compartments for each day and time. Keep an updated 
list of all her medications, including doses and timing, where you both can easily 
see it—on the fridge or in her purse works well. If she's on multiple medications, 
ask her doctor or pharmacist to review them together to make sure there are no 
interactions and that everything is still needed. Be patient with yourself and 
with her—this takes time to build into a routine. What specific challenges are 
you noticing with her medications right now?
```

**Length:** Medium (~120-150 words)  
**Style:** Gentle, reassuring, practical  
**Ends with:** Invitation to share more

---

## 🙏 **Faith Tone (Christian)**

### Input:
```json
{
    "message": "I'm worried about my upcoming surgery",
    "tone": "Faith",
    "faith_setting": "christian"
}
```

### Response Content:
```
It's completely natural to feel worried before surgery. Your feelings are valid, 
and it's okay to acknowledge them. Medically, surgeons and their teams prepare 
extensively to ensure safety, and you'll be monitored closely throughout. In the 
days leading up, try to rest well, stay hydrated, and follow all pre-surgery 
instructions carefully. Know that you're not alone in this—lean on your faith 
community, family, and medical team for support. 

"Peace I leave with you; my peace I give you. I do not give to you as the 
world gives. Do not let your hearts be troubled and do not be afraid." 
— John 14:27

Would you like me to walk with you through what to expect or how to prepare?
```

**Length:** Medium (~140-180 words)  
**Style:** Peaceful, hopeful, medically sound  
**Includes:** Bible verse or brief prayer  
**Ends with:** Supportive invitation

---

## 🩺 **Clinical Tone**

### Input:
```json
{
    "message": "67F presents with fever, WBC 15.2, Cr 1.8, BP 88/52",
    "tone": "Clinical",
    "care_setting": "hospital"
}
```

### Response Content:
```
[Inpatient / Discharge Handoff]

🩺 SOAP Note:

Subjective:
67-year-old female presenting with fever and hemodynamic instability.

Objective:
• WBC 15.2 × 10⁹/L (↑ normal 4.0-11.0) – leukocytosis, suggests infection or stress response
• Creatinine 1.8 mg/dL (↑ baseline unknown, likely AKI if acute)
• BP 88/52 mmHg (↓ hypotensive)
• Fever (temp not specified)

Assessment:
Sepsis workup indicated given fever, leukocytosis, hypotension, and AKI. 
Consider urosepsis, pneumonia, intra-abdominal source. Hypotension suggests 
early septic shock.

Plan:
• Obtain blood cultures × 2, UA with culture, CXR
• Start empiric broad-spectrum antibiotics after cultures (e.g., ceftriaxone + metronidazole)
• IV fluid resuscitation (1-2L bolus, reassess)
• Repeat Cr, BUN, lactate in 4-6h
• Consider ICU consult if BP doesn't respond to fluids
• Escalate immediately if altered mental status, lactate >4, or worsening hypotension

───────────────────────────────────────────

⚡ Quick-Scan Card:

🔴 BP 88/52 → Fluid bolus 1-2L, Repeat q15min, Consider pressors if no response
🔴 WBC 15.2 (↑) → Cultures before abx, Start empiric abx, Repeat in 24h
🟡 Cr 1.8 (↑) → Check baseline, Repeat in 4-6h, Monitor I/O, Avoid nephrotoxins
🔴 Fever + Hypotension → Sepsis bundle, Lactate, Source control

Want me to expand into antibiotic selection or fluid management?
```

**Length:** 400-600 words  
**Format:** Highly structured, medical documentation  
**Audience:** Physicians, residents, medical students  
**Output:** SOAP + Quick-Scan Card

---

## 👴 **Geriatric Tone**

### Input:
```json
{
    "message": "My 85-year-old dad keeps falling at home",
    "tone": "Geriatric"
}
```

### Response Content:
```
Falls in older adults are concerning, and I'm glad you're looking into this. 
Falls often have multiple contributing factors—medications (especially blood 
pressure pills or sleep aids), vision changes, home hazards like loose rugs, 
muscle weakness, or balance issues. Start by scheduling a medication review 
with his doctor to see if anything increases fall risk. At home, improve 
lighting, remove tripping hazards, add grab bars in the bathroom, and consider 
a bedside commode if nighttime bathroom trips are risky. Physical therapy can 
help with strength and balance, and an occupational therapist can assess home 
safety. If he hasn't had his vision or hearing checked recently, that's worth 
doing too. Would you like me to suggest some specific home adjustments or talk 
about assistive devices that might help?
```

**Length:** Medium-Long (~160-200 words)  
**Focus:** Fall prevention, home safety, practical tips  
**Style:** Respectful, unhurried, comprehensive

---

## 💙 **EmotionalSupport Tone**

### Input:
```json
{
    "message": "I'm scared about my test results",
    "tone": "EmotionalSupport"
}
```

### Response Content:
```
I hear you, and it's completely okay to feel scared right now. Waiting for 
test results or hearing something unexpected can feel overwhelming, and those 
feelings are valid. Take a moment to breathe—whatever the results show, you'll 
have a path forward, and you won't have to walk it alone. If the results bring 
news you weren't hoping for, remember that having information is the first step 
toward understanding and addressing it. If they're reassuring, that's a relief 
you can hold onto. Either way, be gentle with yourself in this waiting space—
anxiety is hard, and you're doing your best. Lean on the people who care about 
you, and don't hesitate to ask your doctor questions when the time comes. 
Would you like me to walk with you through what the next steps might look like, 
or just sit with you in this moment?
```

**Length:** Medium (~140-180 words)  
**Style:** Validating, comforting, emotion-first  
**Focus:** Reducing fear, self-kindness, support

---

## 🌍 **Spanish Language with Caregiver Tone**

### Input:
```json
{
    "message": "dolor de cabeza",
    "tone": "Caregiver",
    "lang": "es-ES"
}
```

### Response Content:
```
Los dolores de cabeza pueden ser muy molestos, especialmente cuando 
interrumpen tu día. Intenta descansar en un lugar tranquilo y oscuro, 
mantente hidratado, y considera tomar un analgésico de venta libre 
si es necesario. Si el dolor de cabeza es el peor que hayas tenido, 
viene con rigidez en el cuello, cambios en la visión, o confusión, 
busca atención médica de inmediato.

¿Esto describe lo que estás sintiendo? ¿Quieres contarme un poco más sobre cómo te sientes?
```

**Format:** Response in Spanish (as specified by `lang` parameter)  
**Style:** Warm, caregiver tone maintained in Spanish

---

## 🎯 **iOS Implementation Guide**

### **1. Tone Picker:**
```swift
enum ChatTone: String, CaseIterable {
    case plain = "PlainClinical"
    case caregiver = "Caregiver"
    case faith = "Faith"
    case clinical = "Clinical"
    case geriatric = "Geriatric"
    case emotional = "EmotionalSupport"
    
    var displayName: String {
        switch self {
        case .plain: return "Plain"
        case .caregiver: return "Caregiver"
        case .faith: return "Faith"
        case .clinical: return "Clinical"
        case .geriatric: return "Geriatric"
        case .emotional: return "Emotional Support"
        }
    }
    
    var icon: String {
        switch self {
        case .plain: return "📝"
        case .caregiver: return "💝"
        case .faith: return "🙏"
        case .clinical: return "🩺"
        case .geriatric: return "👴"
        case .emotional: return "💙"
        }
    }
}
```

### **2. Dynamic Settings UI:**
```swift
struct ChatSettingsView: View {
    @State var tone: ChatTone = .plain
    @State var careSetting: String = "hospital"
    @State var faithSetting: String = "general"
    
    var body: some View {
        Form {
            Picker("Tone", selection: $tone) {
                ForEach(ChatTone.allCases, id: \.self) { tone in
                    Label(tone.displayName, systemImage: tone.icon)
                        .tag(tone)
                }
            }
            
            // Show only for Clinical/Caregiver
            if tone == .clinical || tone == .caregiver {
                Picker("Care Setting", selection: $careSetting) {
                    Text("Hospital").tag("hospital")
                    Text("Clinic").tag("ambulatory")
                    Text("Urgent Care").tag("urgent")
                }
            }
            
            // Show only for Faith
            if tone == .faith {
                Picker("Faith Tradition", selection: $faithSetting) {
                    Text("General").tag("general")
                    Text("Christian").tag("christian")
                    Text("Muslim").tag("muslim")
                    Text("Hindu").tag("hindu")
                    Text("Buddhist").tag("buddhist")
                    Text("Jewish").tag("jewish")
                }
            }
        }
    }
}
```

### **3. Send Request:**
```swift
func sendMessage(text: String) async throws {
    var request = SendChatRequest(message: text)
    request.tone = selectedTone.rawValue
    request.language = selectedLanguage
    
    // Add contextual settings
    if selectedTone == .clinical || selectedTone == .caregiver {
        request.careSetting = careSetting
    }
    if selectedTone == .faith {
        request.faithSetting = faithSetting
    }
    
    let response = try await apiService.sendChat(request)
    messages.append(response)
}
```

---

## 📊 **Response Length Guide**

```
QUICK Mode:         60-80 words    (< 5 sentences)
EXPLAIN Mode:       100-120 words  (2-4 sentences)
FULL Mode:          200-300 words  (structured sections)
Clinical Mode:      400-600 words  (SOAP + Quick-Scan)
Caregiver:          120-180 words
Faith:              140-200 words
Geriatric:          160-220 words
EmotionalSupport:   140-180 words
(Note: Language is handled separately via `lang` parameter, not as a tone)
```

---

## 🎨 **Visual Format Examples**

### **QUICK - Plain Text Flow:**
```
Sentence 1 (empathy).
Sentence 2 (action). Sentence 3 (action).
Sentence 4 (red flag warning).
Sentence 5 (question)?
```

### **FULL - Sectioned:**
```
Lead-in paragraph.

Section Heading
• Bullet point 1
• Bullet point 2
• Bullet point 3

Section Heading
• Bullet point 1
• Bullet point 2

Question to continue?
```

### **Clinical - Structured Medical:**
```
[Banner]

🩺 SOAP Note:

Subjective:
[Presentation]

Objective:
• Lab 1 (value, normal range, flag)
• Lab 2 (value, normal range, flag)

Assessment:
[Impression]

Plan:
[Steps]

───────────────────

⚡ Quick-Scan Card:

🔴 Critical finding → Action
🟡 Abnormal → Action
🟢 Normal → Monitor

[Question?]
```

---

## 🎯 **iOS Display Recommendations**

### **For All Modes:**
```swift
Text(response.content)
    .font(.body)
    .foregroundColor(.primary)
    .lineSpacing(4)
```

### **For FULL Mode (Preserve Structure):**
```swift
// Keep bullet points and sections
// Don't strip newlines
// Preserve spacing
ScrollView {
    Text(response.content)
        .font(.body)
        .lineSpacing(6)  // More spacing for readability
}
```

### **For Clinical Mode:**
```swift
// Consider monospace for Quick-Scan Card
if response.content.contains("Quick-Scan Card") {
    Text(response.content)
        .font(.system(.body, design: .monospaced))
} else {
    Text(response.content)
        .font(.body)
}
```

---

## 🔄 **Auto-Selection Logic (PlainClinical)**

```
User Message Analysis:

"headache"
├─ Words: 1
├─ Mode: QUICK ⚡
└─ Response: ~60 words

"what is diabetes"
├─ Words: 14
├─ Mode: EXPLAIN 📖
└─ Response: ~100 words

"headache for days with nausea"
├─ Words: 13 + detailed (multiple symptoms)
├─ Mode: FULL 📋
└─ Response: ~250 words

[Uploads medical file]
├─ Has file: Yes
├─ Mode: FULL 📋
└─ Response: ~300 words with file analysis
```

---

## 📝 **Complete Request/Response Examples**

### **Example 1: Simple Chat**
```json
// Request
{
    "message": "fever",
    "tone": "PlainClinical"
}

// Response
{
    "id": "msg-001",
    "role": "assistant",
    "content": "Fever is your body fighting an infection or illness...",
    "timestamp": "2025-10-24T14:30:00+00:00",
    "session_id": null,
    "metadata": null
}
```

### **Example 2: Clinical with Setting**
```json
// Request
{
    "message": "Patient hypertensive emergency BP 200/120",
    "tone": "Clinical",
    "care_setting": "urgent"
}

// Response
{
    "id": "msg-002",
    "role": "assistant",
    "content": "[Urgent Care Triage]\n\n🩺 SOAP Note:\n\nSubjective:...",
    "timestamp": "2025-10-24T14:31:00+00:00",
    "session_id": "session-abc",
    "metadata": null
}
```

### **Example 3: Faith with Tradition**
```json
// Request
{
    "message": "worried about diagnosis",
    "tone": "Faith",
    "faith_setting": "muslim"
}

// Response
{
    "id": "msg-003",
    "role": "assistant",
    "content": "Your worries are understandable... [includes dua]",
    "timestamp": "2025-10-24T14:32:00+00:00",
    "session_id": "session-def",
    "metadata": null
}
```

---

## 🎉 **Summary for iOS Developers**

**What to Know:**
1. **6 main tones** - Each with different personality
2. **3 auto modes** - QUICK, EXPLAIN, FULL (PlainClinical only)
3. **2 layer systems** - Care settings (3 options), Faith settings (6 options)
4. **No markdown** - Plain text with bullets and sections
5. **Same JSON structure** - Only `content` varies
6. **Smart memory** - 15-minute context retention
7. **Two-pass AI** - Raw then polished for warmth

**iOS Displays:**
- Show `content` as-is
- Preserve line breaks and bullets
- No special parsing needed
- Works with standard Text views

**Backend handles all the complexity. iOS just displays the result!** 🎨

