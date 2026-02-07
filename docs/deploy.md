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

## Mobile

Use EAS Build (Expo) for iOS/Android distribution.
Set `API_BASE_URL` in `mobile/App.tsx` to the deployed backend URL.
