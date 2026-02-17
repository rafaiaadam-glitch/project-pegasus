# Fix: Network Request Failed Error

## Problem
Mobile app shows: `API Error (/lectures?limit=10&offset=0): [TypeError: Network request failed]`

## Root Cause
Expo is **not loading** the `.env` file, so `EXPO_PUBLIC_API_URL` is undefined. The app falls back to `localhost`, which doesn't work.

## ✅ Solution (Choose One)

### Option 1: Quick Fix (Restart Expo Properly)

```bash
# 1. Kill all Expo processes
killall -9 node

# 2. Navigate to mobile directory
cd /Users/rafaiaadam/project-pegasus/temp-repo/mobile

# 3. Verify .env file exists and is correct
cat .env

# Should show:
# EXPO_PUBLIC_API_URL=https://pegasus-api-988514135894.us-central1.run.app

# 4. Start Expo with cache clear
npx expo start --clear

# 5. Reload app (press 'r' in terminal, or shake device)
```

### Option 2: Install dotenv (If Option 1 Doesn't Work)

Expo SDK 51+ should auto-load `.env`, but if it's not working:

```bash
cd /Users/rafaiaadam/project-pegasus/temp-repo/mobile

# Install dotenv package
npm install --save-dev dotenv

# Start Expo
npx expo start --clear
```

### Option 3: Hardcode URL Temporarily (Quick Test)

Edit `mobile/src/services/api.ts`:

```typescript
const getApiBaseUrl = () => {
  // TEMPORARY: Hardcode production URL
  return 'https://pegasus-api-988514135894.us-central1.run.app';

  // Original code (comment out for now):
  // const productionUrl = process.env.EXPO_PUBLIC_API_URL;
  // if (productionUrl) {
  //   return productionUrl;
  // }
  // ...
};
```

Then restart Expo.

---

## 🧪 Verify Fix

After applying fix, test in Expo terminal:

```bash
# Run diagnostic
node debug-connection.js

# All should pass:
# ✅ health
# ✅ presets
# ✅ courses
# ✅ lectures
```

Then in the mobile app, check console for:
```
API_BASE_URL: https://pegasus-api-988514135894.us-central1.run.app
```

If you see `localhost` or `10.0.2.2`, the env var isn't loaded.

---

## 🔍 Debug: Check What URL App Is Using

Add this to `mobile/src/services/api.ts` (line 37):

```typescript
const API_BASE_URL = getApiBaseUrl();

// ADD THIS LINE:
console.log('🔗 API_BASE_URL:', API_BASE_URL);
```

Restart app and check Expo terminal. You should see:
```
🔗 API_BASE_URL: https://pegasus-api-988514135894.us-central1.run.app
```

If you see:
```
🔗 API_BASE_URL: http://localhost:8000
```

Then `.env` is **not** being loaded.

---

## ⚡ Why This Happens

### Expo SDK 50+
Expo SDK 50+ auto-loads `.env` files if they use the `EXPO_PUBLIC_` prefix.

**BUT** it only loads them **when Metro bundler starts**.

### Common Issues:
1. **Created .env while Expo running** - Metro doesn't watch .env, so it never loads
2. **Cached bundle** - Old bundle still has undefined env vars
3. **Wrong Expo version** - SDK <49 needs manual dotenv config
4. **Typo in var name** - Must be `EXPO_PUBLIC_API_URL` exactly

---

## ✅ Final Checklist

- [ ] `.env` file exists in `mobile/` directory
- [ ] Contains `EXPO_PUBLIC_API_URL=https://pegasus-api-988514135894.us-central1.run.app`
- [ ] Killed all node processes (`killall -9 node`)
- [ ] Started Expo with `npx expo start --clear`
- [ ] Reloaded app (press 'r' or shake device)
- [ ] Console shows correct API URL (not localhost)
- [ ] Network error is gone

---

## 📱 Platform-Specific Notes

### iOS Simulator
- Uses `localhost:8000` by default
- Needs `.env` with production URL
- Must restart Metro bundler after creating `.env`

### Android Emulator
- Uses `10.0.2.2:8000` by default (host machine)
- Needs `.env` with production URL
- Same Metro restart requirement

### Physical Device
- **Cannot** use localhost
- **MUST** use production URL or local IP
- Ensure device on same WiFi (if using local backend)

---

## 🆘 Still Not Working?

### Check Expo Version
```bash
npx expo --version
# Should be >= 51.0.0
```

If version is old, upgrade:
```bash
npx expo install expo@latest
```

### Check Metro Bundler Logs
Look for this when Metro starts:
```
› Environment: development
› Using Expo Go
```

Should NOT show any .env errors.

### Check app.json Config
Open `mobile/app.json` and verify:
```json
{
  "expo": {
    "extra": {
      "eas": {
        "projectId": "..."
      }
    }
  }
}
```

No extra config needed for `.env` to work.

---

## 🎯 Expected Behavior After Fix

1. **Expo Terminal** should show:
   ```
   🔗 API_BASE_URL: https://pegasus-api-988514135894.us-central1.run.app
   ```

2. **Mobile App** should:
   - Load home screen
   - Show presets
   - Show courses (if any)
   - Allow upload without network error

3. **Upload Flow**:
   - Select file → Works ✅
   - Enter title → Works ✅
   - Tap Upload → Success! ✅
   - See "Lecture uploaded successfully" ✅

---

## 💡 Pro Tip: Development vs Production

Create multiple env files:

```bash
# Development (local backend)
.env.development
EXPO_PUBLIC_API_URL=http://localhost:8000

# Production (Cloud Run)
.env.production
EXPO_PUBLIC_API_URL=https://pegasus-api-988514135894.us-central1.run.app
```

Then copy the right one:
```bash
# For production
cp .env.production .env
npx expo start --clear
```

---

## Need Help?

1. Run diagnostic: `node debug-connection.js`
2. Check Expo logs for .env errors
3. Verify `.env` exists: `cat mobile/.env`
4. Try hardcode option as last resort
