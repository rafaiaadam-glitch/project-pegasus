# Mobile Recording Guide

## Audio Format Compatibility

### Recording Format
The Pegasus mobile app (iOS/Android) uses **Expo's HIGH_QUALITY preset**, which produces:
- **Format:** M4A (AAC encoded)
- **Quality:** High-quality audio suitable for speech recognition
- **File size:** Optimized for mobile devices

### Transcription Provider Compatibility

#### ✅ **Google Speech-to-Text (Default)**
- **Supports:** MP3, FLAC, OGG_OPUS, WEBM_OPUS, LINEAR16 (WAV)
- **M4A Support:** ✅ **Automatic conversion** - Backend converts M4A → MP3
- **Accuracy:** Excellent, optimized for Google Cloud
- **Setup:** Default transcription provider
- **Usage:** No special configuration needed

**Use Google STT for all recordings (including mobile M4A):**
```bash
POST /lectures/{lecture_id}/transcribe
# provider defaults to "google" - M4A files automatically converted to MP3
```

#### 🔄 **Whisper (Alternative)**
- **Supports:** M4A, MP3, WAV, FLAC, and more (native M4A support)
- **Accuracy:** Excellent for mobile recordings
- **Best for:** Offline/local transcription

**To use Whisper instead:**
```bash
POST /lectures/{lecture_id}/transcribe?provider=whisper
```

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
3. **Automatic transcription** → Uses Google Speech-to-Text by default
   - M4A files automatically converted to MP3 using ffmpeg
4. **Artifact generation** → Uses Gemini (default)

**Default configuration (works perfectly with mobile):**
```bash
# No special config needed - Google STT handles M4A via auto-conversion
POST /lectures/{lecture_id}/transcribe
# Provider defaults to "google", M4A → MP3 conversion is automatic
```

**To use Whisper instead (native M4A support, no conversion):**
```bash
# Whisper supports M4A natively, no conversion needed
POST /lectures/{lecture_id}/transcribe?provider=whisper
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

### Transcription Fails

**Possible causes:**

1. **ffmpeg not installed** (for M4A conversion)
   - Check Docker container has ffmpeg
   - Should be in Dockerfile: `apt-get install ffmpeg`

2. **Audio file corrupted**
   - Verify file size > 0
   - Check upload completed successfully

3. **Google STT quota exceeded**
   - Check GCP Console → Speech-to-Text → Quotas
   - Default: 1,000 minutes/month free tier

**Alternative:** Use Whisper (no conversion needed):
```bash
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

# Transcription: Google Speech-to-Text (default)
# M4A files from mobile are automatically converted to MP3
# Requires ffmpeg in Docker container (already included)
PLC_GCP_STT_MODEL=latest_long  # High accuracy model
PLC_STT_LANGUAGE=en-US  # Default language

# Storage: Use Cloud Storage for production
STORAGE_MODE=gcs
GCS_BUCKET=your-bucket-name
GCS_PREFIX=pegasus
```

**Alternative: Use Whisper for local/offline transcription:**
```bash
# Set provider=whisper in API calls (not as env var)
# Whisper has native M4A support, no conversion needed
```

---

## Summary

✅ **Use Google Speech-to-Text for transcription** (M4A auto-converted to MP3)
✅ **Use Gemini for artifact generation** (fast, cheap, accurate)
✅ **Production URL in .env** for builds
✅ **ffmpeg in Docker** for M4A conversion
✅ **Test on real devices** before launch

Your mobile app is production-ready with this configuration! 🚀

### Key Technical Details

- **Mobile recordings:** M4A (AAC) format
- **Google STT:** Requires MP3/FLAC/WAV/OGG
- **Auto-conversion:** M4A → MP3 (ffmpeg)
- **Fallback:** Whisper supports M4A natively (no conversion)
- **Default:** Google Speech-to-Text for cloud accuracy
- **Cost:** ~$0.54/hour (Google STT enhanced model)
