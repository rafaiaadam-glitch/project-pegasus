# GCP Error Handling and Monitoring Guide

This document describes error handling, monitoring, and troubleshooting for Gemini (Vertex AI) and Google Speech-to-Text integrations in Pegasus.

## Table of Contents

1. [Error Handling Overview](#error-handling-overview)
2. [Gemini/Vertex AI Error Handling](#geminivertex-ai-error-handling)
3. [Google Speech-to-Text Error Handling](#google-speech-to-text-error-handling)
4. [Monitoring and Observability](#monitoring-and-observability)
5. [Rate Limiting](#rate-limiting)
6. [Cost Monitoring](#cost-monitoring)
7. [Troubleshooting Guide](#troubleshooting-guide)

---

## Error Handling Overview

### Retry Mechanism

Both Gemini and Google Speech-to-Text integrations use automatic retry with exponential backoff:

**Default Configuration (from environment):**
- `PLC_RETRY_MAX_ATTEMPTS`: Maximum retry attempts (default: 3)
- `PLC_RETRY_BASE_DELAY_SEC`: Base delay between retries (default: 2 seconds)
- `PLC_RETRY_MAX_DELAY_SEC`: Maximum delay between retries (default: 60 seconds)
- `PLC_RETRY_BACKOFF_MULTIPLIER`: Backoff multiplier (default: 2)

**Retryable Errors:**
- HTTP 429 (Rate Limited)
- HTTP 500, 502, 503, 504 (Server Errors)
- Network timeouts
- Transient connection errors

**Non-Retryable Errors:**
- HTTP 400 (Bad Request)
- HTTP 401 (Unauthorized)
- HTTP 403 (Forbidden)
- HTTP 404 (Not Found)
- Invalid API key
- Malformed requests

### Fallback Behavior

**Thread Detection Fallback:**
When Gemini API fails for thread detection, the system automatically falls back to keyword extraction:

```python
# In pipeline/thread_engine.py (lines 275-329)
try:
    result = _call_gemini(transcript, existing_threads, model)
except Exception:
    # Silently falls back to keyword-based thread extraction
    result = _extract_threads_from_keywords(transcript)
```

**Transcription (No Automatic Fallback):**
Google Speech-to-Text failures do NOT automatically fall back to Whisper. The job will fail and must be manually retried or switched to `provider=whisper`.

---

## Gemini/Vertex AI Error Handling

### Common Errors

#### 1. Missing API Key

**Error:**
```
RuntimeError: Missing required environment variable: GEMINI_API_KEY or GOOGLE_API_KEY
```

**Solution:**
Set one of the API keys in Cloud Run:
```bash
gcloud run services update pegasus-api \
  --region=us-west1 \
  --set-env-vars=GEMINI_API_KEY=your-key-here
```

Or use Secret Manager:
```bash
echo -n "YOUR_KEY" | gcloud secrets create gemini-api-key --data-file=-
gcloud run services update pegasus-api --region=us-west1 \
  --set-secrets=GEMINI_API_KEY=gemini-api-key:latest
```

#### 2. Rate Limiting (HTTP 429)

**Error:**
```
urllib.error.HTTPError: HTTP Error 429: Resource has been exhausted
```

**What Happens:**
- Automatic retry with exponential backoff
- After max retries: job fails with error logged to database

**Solution:**
- Request quota increase from Google Cloud Console
- Reduce concurrent requests
- Implement request queuing

**Current Quota Limits (Gemini 1.5 Flash):**
- Free tier: 15 requests/minute
- Paid tier: 1,000 requests/minute (can be increased)

#### 3. Invalid JSON Response

**Error:**
```
ValueError: LLM failed to return valid JSON: Expecting value: line 1 column 1 (char 0)
```

**What Happens:**
- Job fails immediately (non-retryable)
- Error logged to `jobs` table with full stack trace

**Possible Causes:**
- Model returned non-JSON text
- Response was truncated
- Model hallucinated invalid JSON

**Solution:**
- Retry job manually via `POST /jobs/{job_id}/replay`
- Check if prompt is too complex
- Try different model (e.g., `gemini-1.5-pro` for better reliability)

#### 4. Missing Required Artifacts

**Error:**
```
ValueError: Missing 'outline' in LLM response
```

**What Happens:**
- Job fails immediately
- Database records error

**Solution:**
- Replay job
- Verify prompt includes all required artifact types
- Check if model is appropriate for task

#### 5. Vertex AI Initialization Failure

**Error:**
```
google.auth.exceptions.DefaultCredentialsError: Could not automatically determine credentials
```

**What Happens:**
- Only occurs when using Vertex AI SDK (not REST API)
- Current implementation uses REST API, so this is rare

**Solution:**
- Ensure `GOOGLE_APPLICATION_CREDENTIALS` points to service account JSON
- On Cloud Run: service account is automatically configured

---

## Google Speech-to-Text Error Handling

### Common Errors

#### 1. Missing google-cloud-speech Library

**Error:**
```
RuntimeError: google-cloud-speech is required for provider=google.
Install with `pip install google-cloud-speech`.
```

**What Happens:**
- Job fails immediately (non-retryable)

**Solution:**
Ensure `google-cloud-speech` is in `backend/requirements.txt`:
```txt
google-cloud-speech==2.27.0
```

#### 2. Authentication Failure

**Error:**
```
google.auth.exceptions.DefaultCredentialsError: Could not automatically determine credentials
```

**What Happens:**
- Job fails immediately

**Solution:**
- **On Cloud Run:** Ensure service account has Speech-to-Text permissions
- **Local Development:** Set `GOOGLE_APPLICATION_CREDENTIALS`:
  ```bash
  export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
  ```

#### 3. Audio Format Not Supported

**Error:**
```
google.api_core.exceptions.InvalidArgument: Audio encoding not supported
```

**What Happens:**
- Job fails immediately (non-retryable)

**Solution:**
Convert audio to supported format:
- LINEAR16
- FLAC
- MP3
- OGG_OPUS
- WEBM_OPUS

#### 4. Audio Too Long

**Error:**
```
google.api_core.exceptions.InvalidArgument: Audio is too long
```

**What Happens:**
- Google Speech-to-Text has a 10-minute limit for synchronous recognition

**Current Limitation:**
- The implementation uses synchronous `recognize()` (not async `long_running_recognize()`)
- Maximum audio length: ~10 minutes

**Solution:**
- For longer audio, use `provider=whisper` instead
- Or implement async recognition in `backend/jobs.py`

#### 5. Quota Exceeded

**Error:**
```
google.api_core.exceptions.ResourceExhausted: Quota exceeded
```

**What Happens:**
- Automatic retry with backoff
- After retries: job fails

**Solution:**
- Check quota in GCP Console: APIs & Services → Speech-to-Text API → Quotas
- Request quota increase
- Default quota: 1,000 minutes/month (free tier)

---

## Monitoring and Observability

### Cloud Run Logs

**View logs for pegasus-api:**
```bash
gcloud run services logs read pegasus-api --region=us-west1 --limit=100
```

**Filter for Gemini errors:**
```bash
gcloud run services logs read pegasus-api --region=us-west1 \
  --filter="textPayload:Gemini OR textPayload:gemini" --limit=50
```

**Filter for Speech-to-Text errors:**
```bash
gcloud run services logs read pegasus-api --region=us-west1 \
  --filter="textPayload:speech OR textPayload:STT" --limit=50
```

### Structured Logging

**Job events are logged with structured fields:**
```json
{
  "message": "job.updated",
  "job_id": "job-123",
  "lecture_id": "lecture-456",
  "job_type": "generation",
  "status": "failed",
  "error": "Gemini API request failed: HTTP 429"
}
```

**Search logs for failed jobs:**
```bash
gcloud run services logs read pegasus-api --region=us-west1 \
  --filter='jsonPayload.status="failed"' --limit=50
```

### Dead Letter Queue

**List all failed jobs:**
```bash
curl https://pegasus-api-ui64fwvjyq-uw.a.run.app/jobs/dead-letter
```

**Replay failed jobs:**
```bash
# Replay all failed generation jobs
curl -X POST https://pegasus-api-ui64fwvjyq-uw.a.run.app/jobs/dead-letter/replay \
  -H "Content-Type: application/json" \
  -d '{"job_type": "generation", "limit": 10}'
```

See: `docs/runbooks/dead-letter-queue.md`

### Health Checks

**Basic health check:**
```bash
curl https://pegasus-api-ui64fwvjyq-uw.a.run.app/health
```

**Readiness check (includes database, storage):**
```bash
curl https://pegasus-api-ui64fwvjyq-uw.a.run.app/health/ready
```

### Metrics to Monitor

**Key Metrics:**
1. **Job Success Rate:** `completed_jobs / (completed_jobs + failed_jobs)`
2. **Average Job Duration:** Track `created_at` → `updated_at` span
3. **API Error Rate:** Count HTTP 4xx and 5xx responses
4. **Gemini API Latency:** Time spent in `_request_gemini()`
5. **Speech API Latency:** Time spent in `_transcribe_with_google_speech()`

**Database Queries:**
```sql
-- Failed jobs in last 24 hours
SELECT job_type, COUNT(*) as failures
FROM jobs
WHERE status = 'failed'
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY job_type;

-- Average job duration by type
SELECT job_type,
       AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_duration_sec
FROM jobs
WHERE status = 'completed'
GROUP BY job_type;
```

---

## Rate Limiting

### Gemini API Rate Limits

**Free Tier (Gemini 1.5 Flash):**
- 15 requests per minute
- 1,500 requests per day
- 1 million tokens per minute

**Paid Tier:**
- 1,000 requests per minute (default, can be increased)
- No daily limit
- 4 million tokens per minute

**Current Mitigation:**
- Retry with exponential backoff
- Jobs run sequentially (no concurrent generation)
- `PLC_INLINE_JOBS=1` ensures single-threaded execution

**Future Improvements:**
- Implement request queue with rate limiter
- Add request batching where possible

### Google Speech-to-Text Rate Limits

**Default Quota:**
- 1,000 minutes of audio per month (free tier)
- After free tier: Pay-as-you-go

**Request Rate:**
- 100 concurrent requests (default)

**Current Mitigation:**
- Sequential job processing
- No automatic retries for quota errors (job fails)

---

## Cost Monitoring

### Gemini Pricing

**Gemini 1.5 Flash (Recommended):**
- Free tier: 1,500 requests/day
- Paid (input): $0.075 per 1M tokens (~$0.000075 per request)
- Paid (output): $0.30 per 1M tokens

**Estimated Costs (Exam Mode):**
- Average transcript: 5,000 tokens input
- Average response: 2,000 tokens output
- Cost per lecture: ~$0.001 ($0.00037 input + $0.0006 output)
- 1,000 lectures: ~$1.00

### Speech-to-Text Pricing

**Standard Model:**
- First 60 minutes/month: FREE
- 60-1,000,000 minutes: $0.006/minute ($0.36/hour)

**Enhanced Models (latest_long, latest_short):**
- First 60 minutes/month: FREE
- 60-1,000,000 minutes: $0.009/minute ($0.54/hour)

**Estimated Costs:**
- Average lecture: 60 minutes
- Cost per lecture (enhanced): $0.54
- 100 lectures: $54.00

### Cost Alerts

**Set up billing alerts:**
```bash
# Create budget alert for $50/month
gcloud billing budgets create \
  --billing-account=YOUR_BILLING_ACCOUNT \
  --display-name="Pegasus Monthly Budget" \
  --budget-amount=50 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

**Monitor costs in GCP Console:**
- Billing → Reports
- Filter by Service: "Vertex AI API", "Speech-to-Text API"

---

## Troubleshooting Guide

### Problem: Jobs stuck in "queued" status

**Diagnosis:**
```bash
# Check job queue
curl https://pegasus-api-ui64fwvjyq-uw.a.run.app/jobs/dead-letter
```

**Possible Causes:**
1. Worker not running (if using Redis queue)
2. Redis connection failure
3. Jobs running but very slow

**Solution:**
- If using `PLC_INLINE_JOBS=1`: Jobs run immediately, shouldn't be queued
- If using Redis: Check worker is running and connected
- Check logs for errors

### Problem: All Gemini jobs failing

**Diagnosis:**
```bash
# Check API health
curl https://pegasus-api-ui64fwvjyq-uw.a.run.app/health

# Check environment variables
gcloud run services describe pegasus-api --region=us-west1 \
  --format="yaml" | grep -A 20 "env:"

# Test Gemini directly
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"role":"user","parts":[{"text":"test"}]}]}'
```

**Common Causes:**
- Invalid or missing API key
- API key quota exceeded
- Gemini API outage

**Solution:**
- Verify `GEMINI_API_KEY` is correct
- Check quota in GCP Console
- Check [Google Cloud Status Dashboard](https://status.cloud.google.com/)

### Problem: Google Speech-to-Text returning empty transcripts

**Diagnosis:**
```bash
# Check audio file exists
curl https://pegasus-api-ui64fwvjyq-uw.a.run.app/lectures/{lecture_id}

# Verify audio encoding
ffprobe /path/to/audio.mp3
```

**Common Causes:**
- Audio file is corrupted
- Audio format not recognized
- Audio is silent/empty

**Solution:**
- Re-upload audio
- Convert audio to FLAC or WAV
- Test with known-good audio file

### Problem: High costs

**Diagnosis:**
```bash
# Check API usage
gcloud services list --enabled --filter="speech OR aiplatform"

# Review billing
gcloud billing accounts list
```

**Common Causes:**
- Using expensive model (e.g., Gemini Pro instead of Flash)
- Processing very long audio files
- Many failed/retried requests

**Solution:**
- Switch to `gemini-1.5-flash` (cheapest)
- Use Whisper for transcription (free, local)
- Implement request caching
- Set billing alerts

### Problem: Jobs failing with timeout

**Diagnosis:**
```bash
# Check job error details
curl https://pegasus-api-ui64fwvjyq-uw.a.run.app/jobs/{job_id}
```

**Common Causes:**
- Very long transcripts (> 50,000 tokens)
- Slow API response
- Network issues

**Solution:**
- Increase timeout: Set higher `timeout` in `_request_gemini()`
- Split long transcripts into chunks
- Check network connectivity to GCP APIs

---

## Best Practices

1. **Always set billing alerts** to avoid surprise costs
2. **Monitor failed job rate** - should be < 5%
3. **Use Gemini 1.5 Flash** for cost efficiency
4. **Implement retry logic** for transient failures
5. **Log all API errors** with structured logging
6. **Test with small batches** before large-scale processing
7. **Use health checks** in deployment automation
8. **Keep dependencies updated** to get security fixes
9. **Cache responses** where appropriate (e.g., preset templates)
10. **Gracefully degrade** when APIs are unavailable

---

## Additional Resources

- [Gemini API Documentation](https://ai.google.dev/docs)
- [Vertex AI Quotas](https://cloud.google.com/vertex-ai/docs/quotas)
- [Speech-to-Text Quotas](https://cloud.google.com/speech-to-text/quotas)
- [Cloud Run Logging](https://cloud.google.com/run/docs/logging)
- [GCP Status Dashboard](https://status.cloud.google.com/)
- [Pegasus Backend README](/backend/README.md)
- [Dead Letter Queue Runbook](/docs/runbooks/dead-letter-queue.md)
