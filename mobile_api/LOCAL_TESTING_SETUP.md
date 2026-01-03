# 🏠 Local Testing Setup Guide

## Quick Start for Local Development

### Step 1: Enable CORS for Localhost (Django)

Open `/Users/Julia/Downloads/med_ai/myProject/settings.py` and find the CORS section (around line 245).

**Uncomment this line:**
```python
# CORS configuration (scoped to mobile API only)
# Matches both versioned API (/api/v1/mobile/) and compatibility routes (/api/, /auth/)
CORS_URLS_REGEX = r"^/(api|auth)/.*$"
CORS_ALLOWED_ORIGINS = [
    "https://neuromedai.org",
    "https://www.neuromedai.org",
]
# UNCOMMENT THIS LINE FOR LOCAL TESTING: 👇
CORS_ALLOWED_ORIGIN_REGEXES = [r"^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$"]
CORS_ALLOW_CREDENTIALS = True
```

### Step 2: Update Your iOS App (Xcode)

In your Xcode project, find `APIConfig.swift` and update it:

```swift
struct APIConfig {
    #if DEBUG
    // LOCAL TESTING - Point to your Mac's localhost
    static let baseURL = "http://localhost:8000"
    static let isLocalDevelopment = true
    #else
    // PRODUCTION - Point to deployed backend
    static let baseURL = "https://neuromedai.org"
    static let isLocalDevelopment = false
    #endif
    
    static func printConfiguration() {
        print("🌐 API Base URL: \(baseURL)")
        print("🔧 Local Development: \(isLocalDevelopment)")
    }
}
```

**If testing on physical iPhone (not simulator):**

You need to use your Mac's local IP address instead of `localhost`:

1. Find your Mac's IP address:
   ```bash
   # On Mac, run this in Terminal:
   ifconfig | grep "inet " | grep -v 127.0.0.1
   ```
   
2. Use that IP in your iOS app:
   ```swift
   #if DEBUG
   static let baseURL = "http://192.168.1.XXX:8000"  // Use your actual IP
   static let isLocalDevelopment = true
   #endif
   ```

### Step 3: Start Django Backend Server

```bash
cd /Users/Julia/Downloads/med_ai
python manage.py runserver

# Or if testing on physical iPhone, allow external connections:
python manage.py runserver 0.0.0.0:8000
```

You should see:
```
System check identified 1 issue (0 silenced).
Django version X.X, using settings 'myProject.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

### Step 4: Test Backend (Optional but Recommended)

In a new terminal window:

```bash
cd /Users/Julia/Downloads/med_ai

# Test that endpoints are responding
./mobile_api/test_frontend_compat.sh http://localhost:8000
```

Expected output:
```
✓ Auth status endpoint (GET /api/auth/status/)
✓ Sign up endpoint (POST /api/signup/)
✓ Login endpoint (POST /api/login/)
...
✓ All frontend compatibility tests passed!
```

### Step 5: Run Your iOS App

1. **In Xcode**: Build and Run (⌘R)
2. **Try signing up** with a test account
3. **Check Django terminal** - you should see API requests coming in:
   ```
   [18/Oct/2025 12:00:00] "POST /api/signup/ HTTP/1.1" 201 156
   [18/Oct/2025 12:00:01] "POST /api/login/ HTTP/1.1" 200 152
   [18/Oct/2025 12:00:02] "GET /api/user/settings/ HTTP/1.1" 200 145
   ```

## 🔍 Troubleshooting

### Issue: "Connection Failed" or Network Error

**Solution 1: Check Backend is Running**
```bash
# In terminal, you should see Django running
curl http://localhost:8000/api/auth/status/
# Should return: {"authenticated":false,"status":"ok",...}
```

**Solution 2: CORS Issue**
- Make sure you uncommented `CORS_ALLOWED_ORIGIN_REGEXES` in settings.py
- Restart Django server after changing settings

**Solution 3: iOS Simulator vs Physical Device**
- **Simulator**: Use `http://localhost:8000`
- **Physical iPhone**: Use your Mac's IP `http://192.168.1.XXX:8000`

### Issue: "Invalid Response" or Parsing Error

**Check Django Logs:**
Look at your terminal where Django is running. You'll see the actual requests and responses.

**Enable Verbose Logging in iOS:**
Your `APIService.swift` already has logging! Check Xcode console for:
```
🌐 Making request to: http://localhost:8000/api/login/
🌐 Request method: POST
🌐 Response status: 200
🌐 Response data: {...}
```

### Issue: "Token Authentication Failed"

After successful signup/login, your iOS app should:
1. Extract token from response
2. Save to UserDefaults: `UserDefaults.standard.string(forKey: "auth_token")`
3. Send in subsequent requests: `Authorization: Token YOUR_TOKEN`

**Check if token is saved:**
```swift
if let token = UserDefaults.standard.string(forKey: "auth_token") {
    print("✅ Token exists: \(token)")
} else {
    print("❌ No token found")
}
```

## 📱 Complete Local Testing Flow

### 1. Sign Up New User

**What happens:**
- iOS app sends: `POST /api/signup/` with name, email, password
- Backend creates user in SQLite database
- Backend returns user object + auth token
- iOS app saves token to UserDefaults

**What you'll see in Django logs:**
```
🌐 Making request to: http://localhost:8000/api/signup/
[18/Oct/2025 12:00:00] "POST /api/signup/ HTTP/1.1" 201 156
```

### 2. Login Existing User

**What happens:**
- iOS app sends: `POST /api/login/` with email, password
- Backend validates credentials
- Backend returns user object + auth token
- iOS app saves token

**What you'll see:**
```
[18/Oct/2025 12:00:05] "POST /api/login/ HTTP/1.1" 200 152
```

### 3. Get User Profile (Authenticated)

**What happens:**
- iOS app sends: `GET /api/user/settings/` with `Authorization: Token XXX`
- Backend validates token
- Backend returns user profile

**What you'll see:**
```
[18/Oct/2025 12:00:10] "GET /api/user/settings/ HTTP/1.1" 200 145
```

### 4. Send Chat Message (Authenticated)

**What happens:**
- iOS app sends: `POST /api/send-chat/` with message
- Backend returns response (currently stub)

**What you'll see:**
```
[18/Oct/2025 12:00:15] "POST /api/send-chat/ HTTP/1.1" 200 189
```

## 🗄️ Local Database

Your backend uses **SQLite** for local development:
- Database file: `/Users/Julia/Downloads/med_ai/db.sqlite3`
- All test users are stored there
- You can reset by deleting this file (you'll lose all data)

**To view your test users:**
```bash
cd /Users/Julia/Downloads/med_ai
python manage.py shell

# In Python shell:
from django.contrib.auth.models import User
User.objects.all()
# Shows all created users

# To see a specific user:
user = User.objects.get(email='test@example.com')
print(f"Name: {user.first_name} {user.last_name}")
print(f"Token: {user.auth_token.key}")
```

## 🔧 iOS App Settings Checklist

**For Simulator Testing:**
```swift
// APIConfig.swift
#if DEBUG
static let baseURL = "http://localhost:8000"
static let isLocalDevelopment = true
#endif
```

**For Physical iPhone Testing:**
```swift
// APIConfig.swift
#if DEBUG
static let baseURL = "http://192.168.1.XXX:8000"  // Your Mac's IP
static let isLocalDevelopment = true
#endif
```

**Info.plist Settings:**

Make sure your `Info.plist` allows local HTTP connections:

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsLocalNetworking</key>
    <true/>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

Or more specifically:
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

## ✅ Quick Test Commands

**Test backend is responding:**
```bash
curl http://localhost:8000/api/auth/status/
```

**Test signup:**
```bash
curl -X POST http://localhost:8000/api/signup/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com","password":"Test123!"}'
```

**Test login:**
```bash
curl -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!"}'
```

## 🎯 Success Checklist

Before running your iOS app, verify:

- [ ] Django server is running (`python manage.py runserver`)
- [ ] CORS regex is uncommented in settings.py
- [ ] Backend test passes (`./mobile_api/test_frontend_compat.sh`)
- [ ] iOS app `baseURL` points to `http://localhost:8000` (or your Mac's IP)
- [ ] Info.plist allows local HTTP connections
- [ ] Xcode is in Debug mode (not Release)

## 🚀 You're Ready!

1. **Terminal 1**: `python manage.py runserver`
2. **Terminal 2** (optional): Watch logs with verbose output
3. **Xcode**: Build and Run your iOS app
4. **Test**: Try signing up and logging in

You should see requests coming into your Django server immediately!

---

**Need more help?** Check the Django logs - they show every request and response.


