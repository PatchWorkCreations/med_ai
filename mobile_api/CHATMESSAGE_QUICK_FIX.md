# ⚡ ChatMessage Quick Fix

## 🚨 Error:
```
Type 'ChatMessage' does not conform to protocol 'Decodable'
Type 'ChatMessage' does not conform to protocol 'Encodable'
```

## 🔧 Fix (1 Minute):

### ❌ BEFORE (Broken):
```swift
struct ChatMessage: Codable {
    let id: String
    let role: String
    let content: String
    let timestamp: String
    let sessionId: String?
    let metadata: [String: Any]?  // ← PROBLEM: Any isn't Codable
    
    enum CodingKeys: String, CodingKey {
        case id, role, content, timestamp
        case sessionId = "session_id"
        case metadata  // ← REMOVE THIS
    }
}
```

### ✅ AFTER (Fixed):
```swift
struct ChatMessage: Codable {
    let id: String
    let role: String
    let content: String
    let timestamp: String
    let sessionId: String?
    // metadata removed - backend returns null anyway
    
    enum CodingKeys: String, CodingKey {
        case id, role, content, timestamp
        case sessionId = "session_id"
        // metadata removed
    }
}
```

## 📝 Steps:
1. Find `ChatMessage` in `MedicalFile.swift`
2. Delete the `metadata` property line
3. Delete `metadata` from `CodingKeys`
4. Save (⌘S)
5. Build (⌘B)

## ✅ Done!

**Reason:** `[String: Any]` isn't `Codable` because `Any` can be anything. Backend returns `null` for metadata anyway, so just remove it!

---

For detailed explanation see: `FIX_CHATMESSAGE_ERROR.md`

