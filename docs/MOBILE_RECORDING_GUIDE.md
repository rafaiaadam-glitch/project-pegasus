# Mobile Recording Guide

## Audio Format Compatibility

### Recording Format
The Pegasus mobile app (iOS/Android) uses **Expo's HIGH_QUALITY preset**, which produces:
- **Format:** M4A (AAC encoded)
- **Quality:** High-quality audio suitable for speech recognition
- **File size:** Optimized for mobile devices

### Transcription Provider Compatibility

#### OpenAI Whisper (Default)
- **Supports:** M4A, MP3, WAV, FLAC, WEBM, and more (native M4A support)
- **Accuracy:** Excellent for mobile recordings
- **Setup:** Default transcription provider (`OPENAI_API_KEY` required)
- **File size limit:** 25MB (auto-compressed via ffmpeg for larger files)

```bash
POST /lectures/{lecture_id}/transcribe
# provider defaults to "openai", model defaults to "whisper-1"
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
3. **Automatic transcription** → Uses OpenAI Whisper (supports M4A natively)
4. **Artifact generation** → Uses OpenAI (gpt-4o-mini)

**Default configuration (works with mobile):**
```bash
POST /lectures/{lecture_id}/transcribe
# Provider defaults to "openai", Whisper handles M4A natively
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

3. **OpenAI rate limit exceeded**
   - Check usage at https://platform.openai.com/usage
   - Upgrade API tier if needed

---

## Audio Encoding Reference

### OpenAI Whisper Supported Formats

| Format | Extension | Mobile Compatible |
|--------|-----------|-------------------|
| MP3 | `.mp3` | ✅ |
| WAV | `.wav` | ✅ |
| FLAC | `.flac` | ✅ |
| M4A | `.m4a` | **✅ YES** |
| AAC | `.aac` | ✅ |
| OGG | `.ogg` | ✅ |
| WebM | `.webm` | ✅ |

Whisper supports M4A natively — no conversion needed for mobile recordings.

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
OPENAI_API_KEY=sk-...  # Required for Whisper + LLM + Chat
PLC_LLM_PROVIDER=openai
PLC_MAX_AUDIO_UPLOAD_MB=200  # Allow large lectures
PLC_INLINE_JOBS=1  # Process immediately (or use Redis for queue)

# Storage: Use Cloud Storage for production
STORAGE_MODE=gcs
GCS_BUCKET=your-bucket-name
GCS_PREFIX=pegasus
```

---

## Summary

- **OpenAI Whisper for transcription** (native M4A support)
- **OpenAI gpt-4o-mini for artifact generation**
- **Production URL in .env** for builds
- **Test on real devices** before launch

### Key Technical Details

- **Mobile recordings:** M4A (AAC) format
- **OpenAI Whisper:** Native M4A support, no conversion needed
- **File size limit:** 25MB (auto-compressed via ffmpeg for larger files)
- **Cost:** ~$0.006/minute (Whisper transcription)
