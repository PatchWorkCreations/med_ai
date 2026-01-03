# 📱 iOS Physical Device Setup Guide

## Problem
Your iOS app detects it's running on a physical device but doesn't have your Mac's IP address configured, so it falls back to production URL.

## Solution: Configure Mac IP Address

### Your Mac's IP Address
**`192.168.100.53`**

### Option 1: Set in UserDefaults (Recommended)

Add this code to your app initialization. Find your `App.swift` or main app file:

```swift
import SwiftUI

@main
struct NeuroMed_v2App: App {
    init() {
        // Configure Mac IP for physical device testing
        #if DEBUG
        // Set your Mac's IP address for local development
        UserDefaults.standard.set("192.168.100.53", forKey: "mac_ip_address")
        
        // OR set custom API base URL directly
        // UserDefaults.standard.set("http://192.168.100.53:8000", forKey: "custom_api_base_url")
        #endif
    }
    
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
```

### Option 2: Update APIConfig.swift

Find your `APIConfig.swift` file and update it:

```swift
struct APIConfig {
    #if DEBUG
    // Get Mac IP from UserDefaults, or use localhost for simulator
    static var baseURL: String {
        // Check if running on physical device
        #if targetEnvironment(simulator)
        return "http://localhost:8000"
        #else
        // Physical device - use Mac IP
        if let macIP = UserDefaults.standard.string(forKey: "mac_ip_address") {
            return "http://\(macIP):8000"
        } else if let customURL = UserDefaults.standard.string(forKey: "custom_api_base_url") {
            return customURL
        } else {
            // Fallback to production if not configured
            return "https://neuromedai.org"
        }
        #endif
    }
    
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

### Option 3: Hardcode for Testing (Quick Fix)

If you just want to test quickly, you can temporarily hardcode it:

```swift
struct APIConfig {
    #if DEBUG
    #if targetEnvironment(simulator)
    static let baseURL = "http://localhost:8000"
    #else
    // Physical device - hardcode your Mac's IP
    static let baseURL = "http://192.168.100.53:8000"
    #endif
    static let isLocalDevelopment = true
    #else
    static let baseURL = "https://neuromedai.org"
    static let isLocalDevelopment = false
    #endif
}
```

## Quick Setup Steps

1. **Open your Xcode project**
2. **Find `App.swift` or your main app file**
3. **Add the UserDefaults configuration in `init()`:**
   ```swift
   init() {
       #if DEBUG
       UserDefaults.standard.set("192.168.100.53", forKey: "mac_ip_address")
       #endif
   }
   ```
4. **Or update `APIConfig.swift`** with Option 2 code above
5. **Clean and rebuild** (Shift+Cmd+K, then Cmd+B)
6. **Run on your device** (Cmd+R)

## Verify It's Working

After making the change, you should see in the console:
```
🌐 API Base URL: http://192.168.100.53:8000
🔧 Local Development: true
```

Instead of:
```
⚠️ Physical device detected but no Mac IP configured.
🌐 Falling back to production URL: https://neuromedai.org
```

## Important Notes

1. **Same Wi-Fi Network:** Your Mac and iPhone must be on the same Wi-Fi network
2. **Firewall:** Make sure your Mac's firewall isn't blocking port 8000
3. **Server Running:** Ensure Django server is running: `python manage.py runserver 0.0.0.0:8000`
4. **IP May Change:** If your Mac's IP changes, update the value in UserDefaults

## Testing Connection

After configuration, test the connection:
1. Open Safari on your iPhone
2. Go to: `http://192.168.100.53:8000/api/config/`
3. You should see JSON response

If Safari can't connect, check:
- Mac and iPhone on same Wi-Fi
- Firewall settings on Mac
- Django server is running

## Troubleshooting

### Still getting production URL?
- Check that you're in DEBUG mode
- Verify UserDefaults key is set correctly
- Check APIConfig.swift logic

### Connection refused?
- Verify Django server is running: `lsof -i :8000`
- Check Mac firewall settings
- Ensure both devices on same network

### 404 errors?
- Make sure you're using `/api/` endpoints
- Check Django URLs configuration
- Verify CORS is enabled for your IP

