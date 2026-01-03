## Mobile Frontend Tone Integration Guide

This guide outlines how the mobile client should manage, persist, and transmit the user’s tone selection so the backend can generate responses in the requested voice.

---

### 1. Tone Vocabulary

The backend recognizes the following tone keys (case-insensitive when sent from the client):

- `PlainClinical` *(default fallback)*
- `Caregiver`
- `Faith`
- `Clinical`
- `Geriatric`
- `EmotionalSupport`

If you introduce new tones in the UI, make sure the backend is updated with matching prompt templates before shipping.

---

### 2. State Management Checklist

- **Shared State**: Maintain a single source of truth (e.g., `@ObservableObject` in SwiftUI) for the currently selected tone.
- **Persistence**: Store the tone in `UserDefaults` (or equivalent) so it survives app restarts.
- **Default Selection**: When launching, default to `PlainClinical` or the last saved value.
- **Session Reset**: When the user taps “New Chat”, reset the tone to their last saved default unless they explicitly change it.

---

### 3. Request Payload Requirements

Every POST to `/api/send-chat/` must include the tone string in the JSON body (or multipart form payload if sending files):

```json
{
  "message": "Can you explain fall risk for my dad?",
  "tone": "Geriatric",
  "lang": "en-US",
  "session_id": 12345
}
```

**Rules**
- `tone` must be the canonical key (see list above).
- `lang` defaults to `en-US`; include it if the user can override language.
- When uploading attachments, include `tone` in the same multipart payload alongside `files[]`.

---

### 4. Response Handling

The backend immediately applies the supplied tone to the system prompt for that request, so you don’t need to post-process the content.

Response schema (simplified):

```json
{
  "id": "ef5e8d02-6b8b-4c2b-8d6f-72c537f0d2f1",
  "role": "assistant",
  "content": "Hi there! Let’s look at fall risks together...",
  "timestamp": "2025-11-08T12:34:56.789012Z",
  "session_id": 12345,
  "metadata": null
}
```

Display `content` as-is; the backend already rewrites it to honor the requested tone.

---

### 5. Example SwiftUI Flow (Pseudo-Code)

```swift
final class ChatViewModel: ObservableObject {
    @Published var selectedTone: Tone = Tone(savedValue: UserDefaults.standard.string(forKey: "selectedTone"))
    @Published var messages: [ChatMessage] = []

    func send(_ text: String) async throws {
        let payload = SendChatRequest(
            message: text,
            tone: selectedTone.rawValue,
            lang: "en-US",
            sessionId: activeSessionId
        )

        let response = try await APIService.shared.sendChat(payload)
        DispatchQueue.main.async {
            self.messages.append(response)
        }
    }
}
```

```swift
struct TonePicker: View {
    @Binding var selectedTone: Tone

    var body: some View {
        Picker("Tone", selection: $selectedTone) {
            ForEach(Tone.allCases) { tone in
                Text(tone.displayName).tag(tone)
            }
        }
        .onChange(of: selectedTone) { tone in
            UserDefaults.standard.set(tone.rawValue, forKey: "selectedTone")
        }
    }
}
```

---

### 6. QA / Debug Tips

- **Verify Payload**: Log outgoing requests during QA to confirm the `tone` field is present.
- **API Logging**: The backend logs `Tone=<value>` for each request; check server logs if the UI sends the wrong key.
- **Tone Drift**: If replies look clinical, ensure you aren’t reusing a cached request body or omitting `tone` on retry logic.
- **Session Carryover**: The backend now re-seeds system prompts per request, so changing tone mid-session should take effect immediately.

---

### 7. Future Enhancements

- **Tone Metadata**: Extend the response schema to include the applied tone if you want to confirm or surface it in the UI.
- **Analytics**: Track tone selections client-side to understand user preferences.
- **A/B Testing**: Wrap tone defaults behind feature flags if you experiment with new profiles.

---

Keep this guide close when wiring new clients; as long as requests include the correct `tone` value, the backend will generate responses that match the user’s chosen voice.



