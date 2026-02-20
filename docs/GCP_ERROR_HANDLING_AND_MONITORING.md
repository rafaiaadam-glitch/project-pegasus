# OpenAI Error Handling and Monitoring Guide

This document describes error handling, monitoring, and troubleshooting for OpenAI integrations in Pegasus (Whisper transcription, Thread Engine LLM, and Chat).

## Table of Contents

1. [Error Handling Overview](#error-handling-overview)
2. [OpenAI LLM Error Handling](#openai-llm-error-handling)
3. [OpenAI Whisper Error Handling](#openai-whisper-error-handling)
4. [Monitoring and Observability](#monitoring-and-observability)
5. [Rate Limiting](#rate-limiting)
6. [Cost Monitoring](#cost-monitoring)
7. [Troubleshooting Guide](#troubleshooting-guide)

---

## Error Handling Overview

### Retry Mechanism

OpenAI integrations use automatic retry with exponential backoff:

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
- HTTP 401 (Unauthorized / invalid API key)
- HTTP 403 (Forbidden)
- Invalid JSON responses
- Malformed requests

### Fallback Behavior

**Thread Detection Fallback:**
When the OpenAI API fails for thread detection, the system automatically falls back to keyword extraction:

```python
# In pipeline/thread_engine.py
try:
    result = _call_openai(transcript, existing_threads, model)
except Exception:
    # Falls back to keyword-based thread extraction
    result = _extract_threads_from_keywords(transcript)
```

**Transcription (No Automatic Fallback):**
OpenAI Whisper failures will cause the job to fail. Retry via `POST /jobs/{job_id}/replay`.

---

## OpenAI LLM Error Handling

### Common Errors

#### 1. Missing API Key

**Error:**
```
RuntimeError: OPENAI_API_KEY is not set.
```

**Solution:**
Ensure `OPENAI_API_KEY` is set via Secret Manager in Cloud Run:
```bash
gcloud run services update pegasus-api --region=europe-west1 \
  --set-secrets=OPENAI_API_KEY=openai-api-key:latest
```

#### 2. Rate Limiting (HTTP 429)

**Error:**
```
NonRetryableError: OpenAI API returned HTTP 429: ...
```

**What Happens:**
- Automatic retry with exponential backoff
- After max retries: job fails with error logged to database

**Solution:**
- Check usage at https://platform.openai.com/usage
- Upgrade API tier for higher rate limits
- Reduce concurrent requests

#### 3. Invalid JSON Response

**Error:**
```
NonRetryableError: OpenAI returned non-JSON text: ...
```

**What Happens:**
- Job fails immediately (non-retryable)
- Error logged to `jobs` table

**Solution:**
- Retry job manually via `POST /jobs/{job_id}/replay`
- Check if prompt is too complex for the model

#### 4. Connection Failure

**Error:**
```
NonRetryableError: OpenAI API connection failed: ...
```

**Solution:**
- Check network connectivity from Cloud Run
- Verify OpenAI API status at https://status.openai.com

---

## OpenAI Whisper Error Handling

### Common Errors

#### 1. File Too Large

OpenAI Whisper has a 25MB file size limit. The system auto-compresses larger files via ffmpeg.

**Error (if compression fails):**
```
RuntimeError: Audio file too large for Whisper API after compression
```

**Solution:**
- Ensure ffmpeg is available in the container
- Check audio file isn't excessively long

#### 2. Unsupported Audio Format

Whisper supports: mp3, mp4, mpeg, mpga, m4a, wav, webm.

**Solution:**
- Convert audio to a supported format before upload
- The ingest pipeline handles common formats automatically

#### 3. Empty Transcript

**Error:**
```
ValueError: Transcript text is empty.
```

**Possible Causes:**
- Audio contains no speech (silence, music only)
- Audio is corrupted

**Solution:**
- Re-upload with audio containing clear speech

---

## Monitoring and Observability

### Cloud Run Logs

**View logs for pegasus-api:**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=pegasus-api AND resource.labels.location=europe-west1 AND severity>=INFO" --limit 20 --project=delta-student-486911-n5
```

**Filter for OpenAI errors:**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=pegasus-api AND textPayload:OpenAI" --limit=50 --project=delta-student-486911-n5
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
  "error": "OpenAI API returned HTTP 429"
}
```

### Dead Letter Queue

**List all failed jobs:**
```bash
curl https://pegasus-api-988514135894.europe-west1.run.app/jobs/dead-letter
```

**Replay failed jobs:**
```bash
curl -X POST https://pegasus-api-988514135894.europe-west1.run.app/jobs/dead-letter/replay \
  -H "Content-Type: application/json" \
  -d '{"job_type": "generation", "limit": 10}'
```

### Health Checks

```bash
curl https://pegasus-api-988514135894.europe-west1.run.app/health
curl https://pegasus-api-988514135894.europe-west1.run.app/health/ready
```

### Key Metrics

1. **Job Success Rate:** `completed_jobs / (completed_jobs + failed_jobs)`
2. **Average Job Duration:** Track `created_at` to `updated_at` span
3. **API Error Rate:** Count HTTP 4xx and 5xx responses
4. **OpenAI API Latency:** Time in `_call_openai()` and Whisper calls

---

## Rate Limiting

### OpenAI API Rate Limits

Rate limits vary by tier. Check your current limits at https://platform.openai.com/account/limits

**Typical Tier 1:**
- gpt-4o-mini: 500 RPM, 200K TPM
- whisper-1: 50 RPM

**Current Mitigation:**
- Retry with exponential backoff
- Jobs run sequentially (`PLC_INLINE_JOBS=1`)

---

## Cost Monitoring

### OpenAI Pricing

**gpt-4o-mini (Thread Engine + Chat):**
- Input: $0.15 per 1M tokens
- Output: $0.60 per 1M tokens

**Whisper (Transcription):**
- $0.006 per minute of audio

**Estimated Costs per Lecture:**
- Transcription (60 min): ~$0.36
- Thread Engine (~7K tokens): ~$0.005
- Total per lecture: ~$0.37

### Cost Alerts

Monitor usage at https://platform.openai.com/usage

Set spending limits in OpenAI dashboard: Settings > Limits

---

## Troubleshooting Guide

### Problem: Jobs stuck in "queued" status

**Solution:**
- With `PLC_INLINE_JOBS=1`: jobs run immediately, shouldn't be queued
- Check logs for errors during job execution

### Problem: All generation jobs failing

**Diagnosis:**
```bash
# Check recent failed jobs
curl https://pegasus-api-988514135894.europe-west1.run.app/jobs/dead-letter?job_type=generation

# Check environment
gcloud run services describe pegasus-api --region=europe-west1 \
  --format="yaml" | grep -A 20 "env:"
```

**Common Causes:**
- Invalid or expired `OPENAI_API_KEY`
- API rate limit exceeded
- OpenAI API outage

**Solution:**
- Verify API key: check Secret Manager value
- Check https://status.openai.com
- Check usage limits at https://platform.openai.com/usage

### Problem: Transcription returning empty text

**Solution:**
- Verify audio contains speech (not just silence/music)
- Check audio file isn't corrupted
- Re-upload and retry

### Problem: Jobs failing with timeout

**Common Causes:**
- Very long transcripts (> 50,000 tokens)
- Slow API response
- Network issues

**Solution:**
- The Thread Engine has a 90-second timeout by default
- Split very long transcripts into chunks
- Check network connectivity

---

## Best Practices

1. **Monitor failed job rate** — should be < 5%
2. **Set OpenAI spending limits** to avoid surprise costs
3. **Use `gpt-4o-mini`** for cost efficiency (default)
4. **Log all API errors** with structured logging
5. **Test with small batches** before large-scale processing
6. **Use health checks** in deployment automation

---

## Additional Resources

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [OpenAI Status](https://status.openai.com)
- [Cloud Run Logging](https://cloud.google.com/run/docs/logging)
- [Pegasus Backend README](/backend/README.md)
- [Dead Letter Queue Runbook](/docs/runbooks/dead-letter-queue.md)
