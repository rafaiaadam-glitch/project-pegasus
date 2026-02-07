# Deployment Notes (MVP)

This repo ships with local scripts, a FastAPI backend, and a React Native client.
To deploy the MVP, you will need:

- Postgres (Supabase recommended)
- S3-compatible storage (or Supabase Storage)
- OpenAI API key for LLM generation
- Whisper runtime (self-hosted or API)

## Backend

Suggested platforms: Render, Fly.io, Railway, or Supabase Edge Functions (if ported).

Environment variables:
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `STORAGE_MODE` (`local` or `s3`)
- `S3_BUCKET`, `S3_PREFIX` (if `STORAGE_MODE=s3`)
- `PLC_STORAGE_DIR` (optional)
- `REDIS_URL` (queue/worker)

### Supabase setup

1. Create a new Supabase project and copy the Postgres connection string into
   `DATABASE_URL`.
2. Enable the following tables (the backend auto-migrates on startup):
   - `courses`
   - `lectures`
   - `jobs`
   - `artifacts`
   - `threads`
   - `exports`
3. Create a storage bucket (e.g. `pegasus-assets`) and set:
   - `STORAGE_MODE=s3`
   - `S3_BUCKET=<bucket name>`
   - `S3_PREFIX=pegasus`
4. Ensure your service role or storage key is available to the backend
   environment so uploads can write to the bucket.

### Infra configuration

Sample configs are included for Render (`render.yaml`), Fly.io (`fly.toml`), and
Railway (`railway.toml`). Each points to `backend/Dockerfile`.

## Mobile

Use EAS Build (Expo) for iOS/Android distribution.

1. Install the EAS CLI: `npm install -g eas-cli`
2. Authenticate: `eas login`
3. Configure builds: `eas build:configure`
4. Run builds:
   - iOS: `eas build --platform ios`
   - Android: `eas build --platform android`

Set `API_BASE_URL` in `mobile/App.tsx` to the deployed backend URL.
