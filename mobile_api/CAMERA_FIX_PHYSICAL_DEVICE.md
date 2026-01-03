# 📷 Fix Camera Issues on Physical Device

## Problem
Camera works in simulator but fails on physical device with errors:
- `Error -12782`
- `Error -11800: The operation could not be completed`
- `Invalid frame dimension (negative or non-finite)`

## Solution: Fix Camera Permissions & Configuration

### Step 1: Add Camera Usage Description to Info.plist

Your `Info.plist` must include camera permission descriptions:

1. Open your Xcode project
2. Find `Info.plist` in the Project Navigator
3. Add these keys (if missing):

**Option A: Using Xcode UI**
- Right-click in Info.plist → "Add Row"
- Key: `Privacy - Camera Usage Description` (or `NSCameraUsageDescription`)
- Value: `"We need access to your camera to take photos for medical document analysis"`

**Option B: Edit Info.plist directly**
```xml
<key>NSCameraUsageDescription</key>
<string>We need access to your camera to take photos for medical document analysis</string>
```

### Step 2: Check Camera Permission Request Code

In your `ImagePicker.swift` or camera view, ensure you're requesting permission correctly:

```swift
import AVFoundation

// Check authorization status
let authStatus = AVCaptureDevice.authorizationStatus(for: .video)

switch authStatus {
case .authorized:
    // Camera is authorized, proceed
    break
case .notDetermined:
    // Request permission
    AVCaptureDevice.requestAccess(for: .video) { granted in
        DispatchQueue.main.async {
            if granted {
                // Permission granted, start camera
            } else {
                // Permission denied, show alert
            }
        }
    }
case .denied, .restricted:
    // Show alert to go to Settings
    break
@unknown default:
    break
}
```

### Step 3: Fix AVCaptureSession Configuration

The error `-12782` often indicates a session configuration issue. Update your camera setup:

```swift
import AVFoundation

class CameraManager: NSObject, ObservableObject {
    var captureSession: AVCaptureSession?
    var videoInput: AVCaptureDeviceInput?
    
    func setupCamera() {
        // Create session
        let session = AVCaptureSession()
        session.sessionPreset = .photo  // or .high
        
        // Get camera device
        guard let camera = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back) else {
            print("❌ Camera not available")
            return
        }
        
        do {
            // Create input
            let input = try AVCaptureDeviceInput(device: camera)
            
            // Add input to session
            if session.canAddInput(input) {
                session.addInput(input)
                self.videoInput = input
            }
            
            // Configure session on background queue
            DispatchQueue.global(qos: .userInitiated).async {
                session.startRunning()
            }
            
            self.captureSession = session
            
        } catch {
            print("❌ Error setting up camera: \(error)")
        }
    }
    
    func stopCamera() {
        captureSession?.stopRunning()
    }
}
```

### Step 4: Handle Camera Errors Gracefully

Add error handling in your camera view:

```swift
import AVFoundation

class ImagePicker: NSObject, ObservableObject {
    @Published var errorMessage: String?
    
    func handleCameraError(_ error: Error) {
        if let avError = error as? AVError {
            switch avError.code {
            case .deviceNotAvailable:
                errorMessage = "Camera is not available on this device"
            case .sessionConfigurationChanged:
                errorMessage = "Camera configuration changed. Please try again."
            case .mediaServicesWereReset:
                errorMessage = "Camera service was reset. Please restart the app."
            default:
                errorMessage = "Camera error: \(avError.localizedDescription)"
            }
        } else {
            errorMessage = "Camera error: \(error.localizedDescription)"
        }
    }
}
```

### Step 5: Check Device Capabilities

Ensure your device actually has a camera:

```swift
import AVFoundation

func checkCameraAvailability() -> Bool {
    // Check if camera is available
    if !UIImagePickerController.isSourceTypeAvailable(.camera) {
        print("❌ Camera not available on this device")
        return false
    }
    
    // Check if camera is available for video
    if AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back) == nil {
        print("❌ Video camera not available")
        return false
    }
    
    return true
}
```

### Step 6: Reset Camera Session on Error

If you get errors, reset the session:

```swift
func resetCameraSession() {
    // Stop current session
    captureSession?.stopRunning()
    
    // Remove all inputs
    captureSession?.inputs.forEach { input in
        captureSession?.removeInput(input)
    }
    
    // Remove all outputs
    captureSession?.outputs.forEach { output in
        captureSession?.removeOutput(output)
    }
    
    // Reconfigure
    setupCamera()
}
```

### Step 7: Test on Physical Device

1. **Clean Build:**
   - Product → Clean Build Folder (Shift+Cmd+K)
   - Product → Build (Cmd+B)

2. **Run on Device:**
   - Connect your iPhone
   - Select your device in Xcode
   - Run (Cmd+R)

3. **Grant Permissions:**
   - When prompted, tap "Allow" for camera access
   - If you previously denied, go to: Settings → Privacy & Security → Camera → Your App → Enable

### Step 8: Debug Camera Issues

Add logging to see what's happening:

```swift
func setupCamera() {
    print("📷 Starting camera setup...")
    
    let session = AVCaptureSession()
    print("📷 Session created")
    
    guard let camera = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back) else {
        print("❌ Camera device not found")
        return
    }
    
    print("📷 Camera device found: \(camera.localizedName)")
    
    do {
        let input = try AVCaptureDeviceInput(device: camera)
        print("📷 Input created")
        
        if session.canAddInput(input) {
            session.addInput(input)
            print("📷 Input added to session")
        } else {
            print("❌ Cannot add input to session")
        }
        
        DispatchQueue.global(qos: .userInitiated).async {
            session.startRunning()
            print("📷 Session started")
        }
        
        self.captureSession = session
        
    } catch {
        print("❌ Error: \(error)")
    }
}
```

## Common Issues & Solutions

### Issue 1: "Camera permission denied"
**Solution:** 
- Go to Settings → Privacy & Security → Camera
- Enable your app
- Or delete and reinstall the app

### Issue 2: "Camera not available"
**Solution:**
- Check if device has camera (all iPhones do, but check iPad models)
- Ensure camera isn't being used by another app
- Restart the device

### Issue 3: "Session configuration error"
**Solution:**
- Ensure you're configuring session on background queue
- Don't modify session while it's running
- Reset session if errors occur

### Issue 4: "Invalid frame dimension"
**Solution:**
- Check that preview layer frame is set correctly
- Ensure view bounds are not zero
- Set preview layer frame in `viewDidLayoutSubviews` or equivalent

## Quick Checklist

- [ ] `NSCameraUsageDescription` added to Info.plist
- [ ] Camera permission requested before use
- [ ] AVCaptureSession configured correctly
- [ ] Session started on background queue
- [ ] Error handling implemented
- [ ] Tested on physical device (not just simulator)
- [ ] Camera permission granted in Settings

## Testing

1. **First Launch:**
   - App should request camera permission
   - User taps "Allow"
   - Camera should work

2. **After Denying Permission:**
   - App should show alert to go to Settings
   - User enables in Settings
   - Camera should work after restarting app

3. **Error Recovery:**
   - If camera fails, app should show error message
   - User can retry or use photo library instead

## Additional Resources

- [Apple's Camera Documentation](https://developer.apple.com/documentation/avfoundation/cameras_and_media_capture)
- [AVCaptureSession Best Practices](https://developer.apple.com/documentation/avfoundation/avcapturesession)
- [Privacy Permissions](https://developer.apple.com/documentation/uikit/protecting_the_user_s_privacy)

