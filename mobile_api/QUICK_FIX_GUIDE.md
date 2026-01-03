# ⚡ Quick Fix Guide - iOS Login Issue

## 🎯 The Problem
Login shows: **"Failed to decode response"**

## 🔧 The Fix (Copy/Paste This)

### 1️⃣ Find Your User.swift File
Look for the User struct in your iOS project.

### 2️⃣ Replace It With This:

```swift
struct User: Codable, Identifiable {
    let id: Int
    let username: String
    let email: String
    let firstName: String?       // ← Changed from String to String?
    let lastName: String?        // ← Changed from String to String?
    let dateJoined: String       // ← Changed from Date to String
    let lastLogin: String?       // ← Changed from Date to String?
    let token: String?
    
    enum CodingKeys: String, CodingKey {
        case id, username, email, token
        case firstName = "first_name"
        case lastName = "last_name"
        case dateJoined = "date_joined"
        case lastLogin = "last_login"
    }
}
```

### 3️⃣ Fix Code That Uses These Fields

**Where you show names:**
```swift
// Before:
Text(user.firstName)

// After:
Text(user.firstName ?? "")
```

**Where you show dates:**
```swift
// Before:
Text(user.dateJoined, style: .date)

// After:
Text(user.dateJoined)  // Just show the string
```

### 4️⃣ Build and Test

1. Save (⌘S)
2. Clean (⌘⇧K)
3. Build (⌘B)
4. Run (⌘R)
5. Login with: `admin@gmail.com` / `admin`

## ✅ Expected Result

- No more "Failed to decode response"
- Login succeeds
- App navigates to main screen
- Token saved

## 🆘 Still Broken?

Check Xcode console for the exact error and share it.

---

**That's it!** 5 minutes and you're done! 🎉

