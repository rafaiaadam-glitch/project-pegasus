# Mobile Recording Guide

## Audio Format Compatibility

### Recording Format
The Pegasus mobile app (iOS/Android) uses **Expo's HIGH_QUALITY preset**, which produces:
- **Format:** M4A (AAC encoded)
- **Quality:** High-quality audio suitable for speech recognition
- **File size:** Optimized for mobile devices

### Transcription Provider Compatibility

#### ✅ **Whisper (Recommended for Mobile)**
- **Supports:** M4A, MP3, WAV, FLAC, and more
- **Accuracy:** Excellent for mobile recordings
- **Setup:** Default transcription provider
- **Usage:** No special configuration needed

**Use Whisper for all mobile recordings:**
```bash
POST /lectures/{lecture_id}/transcribe
# provider defaults to "whisper" - M4A files work perfectly
```

#### ⚠️ **Google Speech-to-Text (Limited Mobile Support)**
- **Supports:** MP3, FLAC, OGG_OPUS, WEBM_OPUS, LINEAR16 (WAV)
- **Does NOT support:** M4A (AAC format from mobile)
- **Best for:** Server-uploaded audio in supported formats

**If using Google STT, convert M4A files first or use supported formats.**

---

## Production Setup

### Environment Configuration

**Mobile App (.env):**
```bash
# Production Cloud Run URL
EXPO_PUBLIC_API_URL=https://pegasus-api-988514135894.us-west1.run.app
```

**Important:** The mobile app uses this URL only in **production mode** (when `__DEV__` is false).

In development, it uses:
- iOS: `http://localhost:8000`
- Android: `http://10.0.2.2:8000` (emulator)
- Physical devices: Your computer's local IP

### Testing Production API in Development

To test the production API while in development mode, update `mobile/src/services/api.ts`:

```typescript
const getApiBaseUrl = () => {
  const productionUrl = process.env.EXPO_PUBLIC_API_URL;

  // Force production URL for testing
  if (productionUrl) {
    return productionUrl;
  }

  // ... rest of dev logic
};
```

Or build in production mode:
```bash
cd mobile
eas build --platform ios --profile production
# or
eas build --platform android --profile production
```

---

## Recording Permissions

### iOS
**Required:** Microphone access

The app automatically requests permission on first use. If denied:
1. User sees "Permission Required" alert
2. User must enable in Settings → Pegasus → Microphone

### Android
**Required:** `RECORD_AUDIO` permission

Automatically requested via app.json permissions. If denied:
1. User sees "Permission Required" alert
2. User must enable in Settings → Apps → Pegasus → Permissions

### Permission Flow
```typescript
1. App loads → requestAudioPermissions() called
2. User taps "Start Recording" → permission checked again
3. If granted → recording starts
4. If denied → alert shown with instructions
```

---

## Recommended Transcription Flow

### Mobile App → Backend → Processing

1. **User records audio** → M4A file created
2. **Upload to backend** → `POST /lectures/ingest`
3. **Automatic transcription** → Uses Whisper by default (supports M4A)
4. **Artifact generation** → Uses Gemini (default)

**Default configuration (works perfectly with mobile):**
```bash
# No special config needed - Whisper handles M4A automatically
POST /lectures/{lecture_id}/transcribe
# Provider defaults to "whisper"
```

**To use Google Speech-to-Text (requires supported format):**
```bash
# Only use if audio is in MP3, FLAC, OGG, WEBM, or WAV format
POST /lectures/{lecture_id}/transcribe?provider=google
```

---

## Troubleshooting

### Recording Button Does Nothing

**Possible causes:**
1. **Microphone permission denied**
   - Check: `Settings → Pegasus → Microphone`
   - Solution: Enable permission and restart app

2. **Web platform detected**
   - Recording only works on iOS/Android
   - Web shows: "Recording Not Available" alert

3. **Development mode + backend not running**
   - App tries to connect to `localhost:8000`
   - Solution: Start local backend or use production URL

### Upload Fails

**Possible causes:**
1. **API URL incorrect**
   - Check: `mobile/.env` has correct `EXPO_PUBLIC_API_URL`
   - Check: App is in production mode (or force production URL)

2. **Backend not responding**
   - Verify: `curl https://your-api.run.app/health`
   - Should return: `{"status":"ok"}`

3. **File too large**
   - Default limit: 200 MB
   - Check: `PLC_MAX_AUDIO_UPLOAD_MB` env var

### Transcription Fails with Google STT

**Most common cause:** M4A format not supported

**Solution:** Use Whisper instead:
```bash
# Let it default to Whisper
POST /lectures/{lecture_id}/transcribe

# Or explicitly specify
POST /lectures/{lecture_id}/transcribe?provider=whisper
```

---

## Audio Encoding Reference

### Google Speech-to-Text Supported Formats

| Format | Extension | Encoding | Mobile Compatible |
|--------|-----------|----------|-------------------|
| MP3 | `.mp3` | MP3 | ⚠️ Need conversion |
| FLAC | `.flac` | FLAC | ⚠️ Need conversion |
| OGG Opus | `.ogg` | OGG_OPUS | ⚠️ Need conversion |
| WebM Opus | `.webm` | WEBM_OPUS | ⚠️ Need conversion |
| WAV | `.wav` | LINEAR16 | ⚠️ Need conversion |
| **M4A** | `.m4a` | **AAC** | **❌ NOT SUPPORTED** |

### Whisper Supported Formats

| Format | Extension | Mobile Compatible |
|--------|-----------|-------------------|
| MP3 | `.mp3` | ✅ |
| WAV | `.wav` | ✅ |
| FLAC | `.flac` | ✅ |
| M4A | `.m4a` | **✅ YES** |
| AAC | `.aac` | ✅ |
| OGG | `.ogg` | ✅ |
| WebM | `.webm` | ✅ |

**Conclusion:** Use Whisper for mobile app recordings! ✅

---

## Production Checklist

- [ ] Mobile .env has production Cloud Run URL
- [ ] Build app in production mode
- [ ] Test recording permissions on actual devices
- [ ] Verify uploads reach backend successfully
- [ ] Confirm transcription works with Whisper (default)
- [ ] Test full lecture processing pipeline
- [ ] Monitor backend logs for errors
- [ ] Set up Cloud Run alerts for failures

---

## Backend Configuration for Mobile

**Recommended settings for mobile uploads:**

```bash
# Backend .env or Cloud Run environment
PLC_LLM_PROVIDER=gemini  # Fast and cost-effective
PLC_MAX_AUDIO_UPLOAD_MB=200  # Allow large lectures
PLC_INLINE_JOBS=1  # Process immediately (or use Redis for queue)

# Transcription: Whisper (default) - supports M4A from mobile
# No need to set provider - defaults to Whisper

# Storage: Use Cloud Storage for production
STORAGE_MODE=gcs
GCS_BUCKET=your-bucket-name
GCS_PREFIX=pegasus
```

**Do NOT set these for mobile apps:**
```bash
# Don't force Google STT - it won't work with M4A files
❌ PLC_DEFAULT_STT_PROVIDER=google  # Bad for mobile!
```

---

## Summary

✅ **Use Whisper for mobile recordings** (M4A format)
✅ **Use Gemini for artifact generation** (fast, cheap, accurate)
✅ **Production URL in .env** for builds
✅ **Test on real devices** before launch

Your mobile app is production-ready with this configuration! 🚀
