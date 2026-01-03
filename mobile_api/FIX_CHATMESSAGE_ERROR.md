# 🔧 Fix ChatMessage Codable Errors

**Error:** Type 'ChatMessage' does not conform to protocol 'Decodable'/'Encodable'

**Cause:** You have a property that isn't `Codable` (likely `metadata: [String: Any]?`)

---

## 🎯 **The Problem**

Your ChatMessage probably looks like this:

```swift
struct ChatMessage: Codable {
    let id: String
    let role: String
    let content: String
    let timestamp: String
    let sessionId: String?
    let metadata: [String: Any]?  // ← THIS IS THE PROBLEM!
    
    enum CodingKeys: String, CodingKey {
        case id, role, content, timestamp
        case sessionId = "session_id"
        case metadata
    }
}
```

**Problem:** `Any` type doesn't conform to `Codable`!

---

## ✅ **Solution 1: Make Metadata Optional and Handle It Manually (Recommended)**

```swift
struct ChatMessage: Codable {
    let id: String
    let role: String
    let content: String
    let timestamp: String
    let sessionId: String?
    
    // Remove metadata or make it a different type
    // Backend currently returns null anyway
    
    enum CodingKeys: String, CodingKey {
        case id, role, content, timestamp
        case sessionId = "session_id"
        // Don't include metadata in CodingKeys
    }
}
```

**Why this works:**
- Backend returns `"metadata": null` currently
- You don't need to decode it yet
- Simpler and safer

---

## ✅ **Solution 2: Use a Codable Type for Metadata**

```swift
// Define what metadata actually contains
struct MessageMetadata: Codable {
    let attachments: [String]?
    let tone: String?
    let language: String?
    
    enum CodingKeys: String, CodingKey {
        case attachments, tone, language
    }
}

struct ChatMessage: Codable {
    let id: String
    let role: String
    let content: String
    let timestamp: String
    let sessionId: String?
    let metadata: MessageMetadata?  // ← Now Codable!
    
    enum CodingKeys: String, CodingKey {
        case id, role, content, timestamp
        case sessionId = "session_id"
        case metadata
    }
}
```

**Why this works:**
- `MessageMetadata` is a proper struct that conforms to `Codable`
- All its properties are `Codable` types
- Type-safe and clear

---

## ✅ **Solution 3: Ignore Metadata Completely (Simplest)**

```swift
struct ChatMessage: Codable {
    let id: String
    let role: String
    let content: String
    let timestamp: String
    let sessionId: String?
    
    enum CodingKeys: String, CodingKey {
        case id, role, content, timestamp
        case sessionId = "session_id"
        // metadata is NOT listed here, so it's ignored
    }
}
```

**Why this works:**
- Backend sends `"metadata": null` which you don't need
- By not including it in `CodingKeys`, it's ignored during decoding
- Simplest solution

---

## 🎯 **What Backend Actually Sends:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "assistant",
  "content": "Hello! You said: Hello, can you help me?",
  "timestamp": "2025-10-24T14:01:16.000000+00:00",
  "session_id": null,
  "metadata": null    // ← Currently always null!
}
```

Since `metadata` is `null`, you don't need to decode it yet!

---

## 📝 **Step-by-Step Fix:**

### **Step 1: Find Your ChatMessage Struct**

It's probably in a file called:
- `ChatMessage.swift`
- `Models.swift`
- `MedicalFile.swift` (based on your error)

### **Step 2: Apply Solution 3 (Simplest)**

**REMOVE** the metadata line:

```swift
// BEFORE (BROKEN):
struct ChatMessage: Codable {
    let id: String
    let role: String
    let content: String
    let timestamp: String
    let sessionId: String?
    let metadata: [String: Any]?  // ← REMOVE THIS LINE
    
    enum CodingKeys: String, CodingKey {
        case id, role, content, timestamp
        case sessionId = "session_id"
        case metadata  // ← REMOVE THIS LINE TOO
    }
}

// AFTER (FIXED):
struct ChatMessage: Codable {
    let id: String
    let role: String
    let content: String
    let timestamp: String
    let sessionId: String?
    // metadata removed
    
    enum CodingKeys: String, CodingKey {
        case id, role, content, timestamp
        case sessionId = "session_id"
        // metadata removed
    }
}
```

### **Step 3: Save and Build**

1. Save the file (⌘S)
2. Build (⌘B)
3. Errors should be gone!

---

## 🐛 **If You Still Get Errors:**

### **Check for Other Non-Codable Properties:**

Look for these problem types in your `ChatMessage`:
- ❌ `Any` type
- ❌ `AnyObject` type
- ❌ Closures `() -> Void`
- ❌ Functions
- ❌ Classes that don't conform to Codable

### **Make Sure All Properties Are:**
- ✅ `String`, `Int`, `Bool`, `Double`, `Float`
- ✅ `Optional` versions of above
- ✅ `Array` or `Dictionary` of Codable types
- ✅ Other `Codable` structs

---

## ✅ **Complete Working Example:**

```swift
struct ChatMessage: Codable, Identifiable {
    let id: String
    let role: String              // "user" or "assistant"
    let content: String           // The actual message text
    let timestamp: String         // ISO8601 date string
    let sessionId: String?        // Optional session ID
    
    enum CodingKeys: String, CodingKey {
        case id
        case role
        case content
        case timestamp
        case sessionId = "session_id"
    }
}
```

**This will work with your backend!**

---

## 🧪 **Test After Fix:**

```swift
// Test decoding a real backend response:
let json = """
{
    "id": "123",
    "role": "assistant",
    "content": "Hello!",
    "timestamp": "2025-10-24T14:01:16.000000+00:00",
    "session_id": null,
    "metadata": null
}
"""

let data = json.data(using: .utf8)!
let decoder = JSONDecoder()
decoder.keyDecodingStrategy = .convertFromSnakeCase

do {
    let message = try decoder.decode(ChatMessage.self, from: data)
    print("✅ Success: \(message.content)")
} catch {
    print("❌ Error: \(error)")
}
```

---

## 🎯 **Summary:**

**Problem:** `metadata: [String: Any]?` isn't `Codable`

**Solution:** Remove metadata field (backend returns null anyway)

**Time:** 1 minute

**Result:** ChatMessage compiles successfully ✅

---

## 📋 **Quick Checklist:**

- [ ] Find ChatMessage struct
- [ ] Remove `metadata` property
- [ ] Remove `metadata` from CodingKeys
- [ ] Save file
- [ ] Build project (⌘B)
- [ ] Errors gone ✅

---

**Backend returns `metadata: null` currently, so you don't need it yet!** 🚀

