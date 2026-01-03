# 📱 Xcode Changes for Local Testing

## What You Need to Change in Your iOS Project

### 1. Update APIConfig.swift

Find your `APIConfig.swift` file in Xcode and change the `baseURL`:

```swift
struct APIConfig {
    #if DEBUG
    // 👇 CHANGE THIS LINE:
    static let baseURL = "http://localhost:8000"  // For iOS Simulator
    // OR if testing on physical iPhone:
    // static let baseURL = "http://192.168.1.XXX:8000"  // Use your Mac's IP
    
    static let isLocalDevelopment = true
    #else
    static let baseURL = "https://neuromedai.org"
    static let isLocalDevelopment = false
    #endif
    
    static func printConfiguration() {
        print("🌐 API Base URL: \(baseURL)")
        print("🔧 Local Development: \(isLocalDevelopment)")
    }
}
```

### 2. Update Info.plist (Allow HTTP Connections)

In your project's `Info.plist`, add or update:

**Method 1 (Simple - Allows all local networking):**
```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsLocalNetworking</key>
    <true/>
</dict>
```

**Method 2 (More Specific):**
```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSExceptionDomains</key>
    <dict>
        <key>localhost</key>
        <dict>
            <key>NSExceptionAllowsInsecureHTTPLoads</key>
            <true/>
        </dict>
    </dict>
</dict>
```

### 3. No Other Changes Needed!

Your `APIService.swift` already:
- ✅ Handles JSON encoding/decoding
- ✅ Sends Token authentication
- ✅ Skips CSRF for `/api/` endpoints
- ✅ Has all the right endpoints

## 🔍 Finding Your Mac's IP Address (For Physical iPhone)

If testing on a real iPhone (not simulator), you need your Mac's IP:

**Option 1 - Terminal:**
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

**Option 2 - System Preferences:**
1. Open System Preferences
2. Click Network
3. Select your active connection (Wi-Fi or Ethernet)
4. Look for "IP Address: 192.168.1.XXX"

**Then update APIConfig.swift:**
```swift
static let baseURL = "http://192.168.1.XXX:8000"  // Your actual IP
```

⚠️ **Important**: Your iPhone must be on the **same Wi-Fi network** as your Mac!

## 🚀 Quick Start Steps

### Step 1: Start Django Backend
```bash
cd /Users/Julia/Downloads/med_ai
python manage.py runserver

# OR if testing on physical iPhone:
python manage.py runserver 0.0.0.0:8000
```

### Step 2: Update Xcode
- Change `baseURL` in `APIConfig.swift`
- Update `Info.plist` to allow HTTP

### Step 3: Build & Run
- Press ⌘R in Xcode
- Try signing up with a test account

### Step 4: Watch the Magic!
Check your Django terminal - you'll see requests coming in:
```
[18/Oct/2025 12:00:00] "POST /api/signup/ HTTP/1.1" 201 156
[18/Oct/2025 12:00:01] "POST /api/login/ HTTP/1.1" 200 152
```

## ✅ Testing Checklist

Before running your iOS app:

- [ ] Backend server is running (`python manage.py runserver`)
- [ ] You can access `http://localhost:8000/api/auth/status/` in your browser
- [ ] `APIConfig.swift` has correct `baseURL`
- [ ] `Info.plist` allows HTTP connections
- [ ] Xcode build configuration is Debug (not Release)

## 🐛 Common Issues

### "Failed to connect to localhost"

**If using iOS Simulator:**
- Use `http://localhost:8000` ✅
- Make sure backend is running

**If using Physical iPhone:**
- Cannot use `localhost` ❌
- Must use Mac's IP: `http://192.168.1.XXX:8000` ✅
- iPhone and Mac on same Wi-Fi ✅
- Backend started with `0.0.0.0:8000` ✅

### "The resource could not be loaded"

Check Info.plist - you need to allow insecure HTTP for local development.

### "CORS Error"

Already fixed! I enabled CORS for localhost in Django settings.

## 📝 Example Test Account

Try creating this test account in your iOS app:

```
Name: Test User
Email: test@example.com
Password: TestPassword123!
```

You should see it appear in your Django logs and the user will be created in the local SQLite database.

## 🎯 What You Should See

### In Xcode Console:
```
🌐 API Base URL: http://localhost:8000
🔧 Local Development: true
🌐 Making request to: http://localhost:8000/api/signup/
🌐 Request method: POST
🌐 Response status: 201
🌐 Response data: {"id":1,"username":"test",...}
✅ Token exists: abc123def456...
```

### In Django Terminal:
```
[18/Oct/2025 12:00:00] "POST /api/signup/ HTTP/1.1" 201 156
[18/Oct/2025 12:00:05] "GET /api/user/settings/ HTTP/1.1" 200 145
```

## 🎉 That's It!

Just these 2 changes in Xcode:
1. ✅ Update `baseURL` in `APIConfig.swift`
2. ✅ Add HTTP exception in `Info.plist`

Everything else is already configured and ready to go! 🚀

---

**Next**: See `LOCAL_TESTING_SETUP.md` for detailed testing instructions.

