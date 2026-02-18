# Mobile Recording Button Test Guide

## Quick Check: Is the Button Working?

### Step 1: Check Console Logs

When you press the record button, you should see in Metro logs:

```
[Recording] ===== START RECORDING BUTTON PRESSED =====
[Recording] Current state: { isRecording: false, recording: false, ... }
[Recording] Requesting audio permissions...
[Recording] Permission granted: true
[Recording] Setting audio mode...
[Recording] Creating Recording object...
[Recording] Recording started successfully!
```

**If you don't see these logs:** The button press isn't being registered.

### Step 2: Check What You See

Run the app and look for:
- ✅ "Tap to Start Recording" button visible?
- ✅ Button responds when tapped (visual feedback)?
- ✅ Permission alert appears if needed?

### Common Issues & Fixes

#### Issue 1: Button Not Visible
**Symptoms:** Can't see the record button at all

**Check:**
```tsx
// In RecordLectureScreen.tsx line 400:
{!selectedFile && !isRecording && (
  <TouchableOpacity style={styles.recordStartButton} onPress={startRecording}>
```

**Fix:** Make sure `selectedFile` is null and `isRecording` is false on initial render

#### Issue 2: Button Visible But Not Responding
**Symptoms:** Button shows but nothing happens when tapped

**Possible causes:**
1. **Overlay covering button** - Check z-index and layout
2. **TouchableOpacity disabled** - Verify no `disabled` prop
3. **Event handler not attached** - Verify `onPress={startRecording}`

**Quick test:**
Add this temporary button at the top of the render to verify touch works:
```tsx
<TouchableOpacity
  style={{ padding: 20, backgroundColor: 'red' }}
  onPress={() => {
    console.log('TEST BUTTON PRESSED!');
    Alert.alert('Test', 'Touch is working!');
  }}
>
  <Text>Test Touch</Text>
</TouchableOpacity>
```

#### Issue 3: Permission Denied Loop
**Symptoms:** Permission alert appears repeatedly

**Fix:**
1. Reset app permissions:
   - iOS: Settings > Privacy & Security > Microphone > Delete app
   - Android: Settings > Apps > Pegasus > Permissions > Clear
2. Reinstall app: `npm run ios` or `npm run android`
3. Grant permission when prompted

#### Issue 4: Recording Fails After Permission Granted
**Symptoms:** Permission granted but recording doesn't start

**Check logs for:**
```
[Recording] Error starting recording:
```

**Common errors:**
- **"Audio mode not set"** - Audio mode configuration failed
- **"Recording unavailable"** - Device doesn't support recording
- **"Already recording"** - Previous recording not cleaned up

**Fix:** Try clearing app state and restarting

### Testing Checklist

Run through this test sequence:

1. **Fresh start:**
   ```bash
   cd mobile
   npx expo start --clear
   ```

2. **Launch app on physical device** (not simulator for audio)

3. **Navigate to:** Home > Course > Record Lecture

4. **Observe console** while tapping record button

5. **Expected behavior:**
   - [ ] Console shows "START RECORDING BUTTON PRESSED"
   - [ ] Permission alert appears (first time only)
   - [ ] After granting permission, recording starts
   - [ ] Red dot appears and pulses
   - [ ] Duration counter starts incrementing
   - [ ] Pause/Stop buttons appear

6. **Stop recording:**
   - [ ] Tap Stop button
   - [ ] File preview appears
   - [ ] Upload button is enabled

### Debugging Commands

```bash
# Clear Metro bundler cache
npx expo start --clear

# Clear iOS build cache
cd ios && rm -rf build && cd ..

# Clear Android build cache
cd android && ./gradlew clean && cd ..

# Reinstall dependencies
rm -rf node_modules && npm install

# Check Expo AV version
npm list expo-av

# Update Expo AV if needed
npx expo install expo-av
```

### Platform-Specific Notes

#### iOS
- **Simulator:** Audio recording NOT supported (use physical device)
- **Permissions:** Set in Settings > Privacy & Security > Microphone
- **Background audio:** Enabled via `UIBackgroundModes` in app.json

#### Android
- **Emulator:** May work with virtual audio input
- **Permissions:** Declared in AndroidManifest.xml
- **Runtime permissions:** Requested when recording starts

### Still Not Working?

If the button still doesn't work after all checks:

1. **Verify app.json configuration:**
   ```json
   {
     "ios": {
       "infoPlist": {
         "NSMicrophoneUsageDescription": "This app needs access..."
       }
     },
     "android": {
       "permissions": ["RECORD_AUDIO"]
     },
     "plugins": [
       ["expo-av", {
         "microphonePermission": "Allow..."
       }]
     ]
   }
   ```

2. **Check expo-av installation:**
   ```bash
   npx expo install expo-av
   npx expo prebuild --clean
   ```

3. **Test on different device** - May be device-specific issue

4. **Check Metro logs** for any unhandled errors or warnings

### Success Indicators

When working correctly, you'll see:
- ✅ Button tap logs immediately
- ✅ Permission granted within 1-2 seconds
- ✅ Recording starts within 2-3 seconds
- ✅ UI updates to show recording state
- ✅ Audio file created when stopped
- ✅ File ready for upload

### Need More Help?

Share these logs:
1. Metro console output from button tap to error
2. Platform (iOS/Android) and version
3. Device model (physical/simulator)
4. Error message from alert (if any)
