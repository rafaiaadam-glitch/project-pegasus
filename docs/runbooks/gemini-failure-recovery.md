# Gemini 3 Pro Failure Recovery Runbook

**Last Updated**: 2026-02-17
**Owner**: Platform Team
**Severity**: Critical

## Overview

This runbook covers recovery procedures when Gemini 3 Pro (gemini-3-pro-preview) generation requests fail or degrade. Use this when:
- Success rate drops below 98%
- Error rate exceeds 2%
- Alert: "Gemini 3 Pro - Success Rate Below 98%" fires

## Quick Diagnosis

### 1. Check Current Status (2 minutes)

```bash
# View monitoring dashboard
open "https://console.cloud.google.com/monitoring/dashboards"

# Check recent errors in Cloud Logging
gcloud logging read 'resource.type="cloud_run_revision"
  AND resource.labels.service_name="pegasus-api"
  AND textPayload=~"Vertex AI Error"
  AND timestamp>="2024-01-01T00:00:00Z"' \
  --limit 50 \
  --format json \
  | jq -r '.[] | .textPayload'

# Get current error rate
curl -s https://pegasus-api-ui64fwvjyq-uc.a.run.app/metrics \
  | grep "pegasus_thinking_errors_total"
```

### 2. Identify Error Pattern (3 minutes)

Common error types and their meanings:

| Error Code | Meaning | Typical Cause |
|------------|---------|---------------|
| `ResourceExhausted` | Quota or rate limit hit | API quota exceeded, too many concurrent requests |
| `DeadlineExceeded` | Request timeout | Generation took >300s, network issues |
| `InvalidArgument` | Malformed request | Bad prompt format, invalid generation config |
| `PermissionDenied` | Auth failure | Service account lacks IAM permissions |
| `FailedPrecondition` | Model unavailable | Gemini 3 model temporarily unavailable in global region |
| `Unavailable` | Service down | Vertex AI outage or maintenance |

## Recovery Procedures

### ResourceExhausted - Quota Limit Hit

**Symptoms**: Error message contains "Quota exceeded" or "RESOURCE_EXHAUSTED"

**Diagnosis**:
```bash
# Check current quota usage
gcloud alpha services quota list \
  --service=aiplatform.googleapis.com \
  --consumer=projects/delta-student-486911-n5 \
  --filter="quotaId:GenerateContentRequests" \
  --format=json

# Check rate limit metrics
gcloud monitoring time-series list \
  --filter='metric.type="aiplatform.googleapis.com/prediction/online/request_count"'
```

**Recovery Steps**:

1. **Immediate**: Request quota increase
   ```bash
   # Navigate to quota page
   open "https://console.cloud.google.com/apis/api/aiplatform.googleapis.com/quotas"

   # Request increase for GenerateContentRequests quota
   # Target: 60 requests/minute for production workload
   ```

2. **Short-term workaround**: Implement request throttling
   - Add rate limiting in backend/jobs.py
   - Queue requests instead of failing immediately
   - Use exponential backoff with jitter

3. **Verify recovery**:
   ```bash
   # Check if new requests succeed
   curl -X POST https://pegasus-api-ui64fwvjyq-uc.a.run.app/lectures/test-123/generate \
     -H "Authorization: Bearer $(gcloud auth print-identity-token)"
   ```

### DeadlineExceeded - Timeout

**Symptoms**: Error message contains "DEADLINE_EXCEEDED" or "timeout"

**Diagnosis**:
```bash
# Check p95 latency trend
curl -s https://pegasus-api-ui64fwvjyq-uc.a.run.app/metrics \
  | grep "pegasus_thinking_duration_seconds"

# Find slow requests in logs
gcloud logging read 'resource.type="cloud_run_revision"
  AND textPayload=~"Generated.*characters of JSON in"
  AND timestamp>="2024-01-01T00:00:00Z"' \
  --limit 20 \
  --format json \
  | jq -r '.[] | .textPayload' \
  | grep -oP 'in \K[\d.]+s'
```

**Root Causes**:
1. **Unusually long transcripts** - Gemini 3 reasoning time scales with input size
2. **Network latency** - Issues reaching global Vertex AI endpoint
3. **Model capacity** - Vertex AI scaling delays during high load

**Recovery Steps**:

1. **Check if transcripts are exceptionally long**:
   ```bash
   # Find recent transcripts and their sizes
   gsutil du -sh gs://delta-student-486911-n5-pegasus-storage/pegasus/transcripts/*.json \
     | sort -h -r | head -10
   ```

2. **If transcripts >50KB**: Implement chunking
   - Split large transcripts into manageable sections
   - Generate artifacts per section, merge results
   - Update `pipeline/llm_generation.py` with chunk logic

3. **If network latency**: Check Vertex AI status
   ```bash
   # Check Google Cloud status
   open "https://status.cloud.google.com/"

   # Measure latency to global endpoint
   time curl -s https://us-central1-aiplatform.googleapis.com/v1/health
   ```

4. **Increase Cloud Run timeout** (if consistently needed):
   ```bash
   gcloud run services update pegasus-api \
     --region=us-central1 \
     --timeout=600  # Increase from 300s to 600s (10 minutes)
   ```

### InvalidArgument - Malformed Request

**Symptoms**: Error message contains "INVALID_ARGUMENT" or "malformed"

**Diagnosis**:
```bash
# Get last failing request details
gcloud logging read 'resource.type="cloud_run_revision"
  AND jsonPayload.error_code="InvalidArgument"
  AND timestamp>="2024-01-01T00:00:00Z"' \
  --limit 5 \
  --format json \
  | jq -r '.[] | .jsonPayload'
```

**Common Causes**:
1. Prompt exceeds model's context window (typically 128K tokens)
2. Invalid generation_config parameters
3. Malformed JSON in system prompt

**Recovery Steps**:

1. **Verify generation config**:
   ```python
   # Check pipeline/llm_generation.py lines 182-186
   # Ensure GenerationConfig only uses supported parameters:
   # - response_mime_type
   # - temperature
   # - max_output_tokens
   ```

2. **Check prompt length**:
   ```bash
   # Count tokens in recent prompts (estimate: 1 token ≈ 4 chars)
   gcloud logging read 'textPayload=~"Generating via global Vertex AI"' \
     --limit 1 --format json \
     | jq -r '.[] | .jsonPayload.transcript_length'
   ```

3. **If prompt too long**: Implement truncation
   ```python
   # In pipeline/llm_generation.py
   MAX_TRANSCRIPT_CHARS = 400_000  # ~100K tokens
   if len(transcript) > MAX_TRANSCRIPT_CHARS:
       transcript = transcript[:MAX_TRANSCRIPT_CHARS] + "\n\n[Transcript truncated]"
   ```

### PermissionDenied - Auth Failure

**Symptoms**: Error message contains "PERMISSION_DENIED" or "403"

**Diagnosis**:
```bash
# Check Cloud Run service account
gcloud run services describe pegasus-api \
  --region=us-central1 \
  --format="value(spec.template.spec.serviceAccountName)"

# Verify service account has required roles
gcloud projects get-iam-policy delta-student-486911-n5 \
  --flatten="bindings[].members" \
  --filter="bindings.members:$(gcloud run services describe pegasus-api --region=us-central1 --format='value(spec.template.spec.serviceAccountName)')" \
  --format="table(bindings.role)"
```

**Required IAM Roles**:
- `roles/aiplatform.user` - Use Vertex AI Prediction and Online Prediction APIs
- `roles/ml.developer` - Access Vertex AI models

**Recovery Steps**:

1. **Grant missing permissions**:
   ```bash
   SERVICE_ACCOUNT=$(gcloud run services describe pegasus-api \
     --region=us-central1 \
     --format="value(spec.template.spec.serviceAccountName)")

   gcloud projects add-iam-policy-binding delta-student-486911-n5 \
     --member="serviceAccount:${SERVICE_ACCOUNT}" \
     --role="roles/aiplatform.user"
   ```

2. **Verify API is enabled**:
   ```bash
   gcloud services enable aiplatform.googleapis.com
   ```

3. **Test permissions**:
   ```bash
   # Impersonate service account and test API access
   gcloud auth print-access-token --impersonate-service-account="${SERVICE_ACCOUNT}" \
     | xargs -I {} curl -H "Authorization: Bearer {}" \
       "https://us-central1-aiplatform.googleapis.com/v1/projects/delta-student-486911-n5/locations/global/publishers/google/models/gemini-3-pro-preview"
   ```

### FailedPrecondition - Model Unavailable

**Symptoms**: Error message contains "FAILED_PRECONDITION" or "model not available"

**Context**: Gemini 3 Pro Preview models may have:
- Geographic restrictions (requires `location="global"`)
- Allowlist requirements for preview access
- Temporary unavailability during rollouts

**Diagnosis**:
```bash
# Check model availability
gcloud ai models list \
  --region=global \
  --filter="displayName:gemini-3-pro-preview"

# Verify allowlist status
gcloud alpha services vpc-peerings list \
  --service=aiplatform.googleapis.com
```

**Recovery Steps**:

1. **Verify location is set to "global"**:
   ```python
   # In pipeline/llm_generation.py line 172
   vertexai.init(project=project_id, location="global")
   ```

2. **Check if account has preview access**:
   - Navigate to Vertex AI console
   - Verify "gemini-3-pro-preview" appears in model catalog
   - If not: Request preview access via Google Cloud support

3. **Fallback to stable model** (temporary):
   ```bash
   # Update environment variable to use stable Gemini
   gcloud run services update pegasus-api \
     --region=us-central1 \
     --update-env-vars=PLC_LLM_MODEL=gemini-2.0-flash
   ```

### Unavailable - Service Outage

**Symptoms**: Error message contains "UNAVAILABLE" or "503"

**Diagnosis**:
```bash
# Check Google Cloud status page
open "https://status.cloud.google.com/"

# Check if it's a regional issue
curl -v https://us-central1-aiplatform.googleapis.com/v1/health 2>&1 | grep "HTTP/"
curl -v https://global-aiplatform.googleapis.com/v1/health 2>&1 | grep "HTTP/"
```

**Recovery Steps**:

1. **If Vertex AI is down globally**: Wait for service restoration
   - Subscribe to status updates: https://status.cloud.google.com/
   - ETA typically posted within 30 minutes of outage

2. **If regional issue**: Already using global endpoint (no action needed)

3. **Temporary fallback**: Use OpenAI provider
   ```bash
   # Update environment variable
   gcloud run services update pegasus-api \
     --region=us-central1 \
     --update-env-vars=PLC_LLM_PROVIDER=openai

   # Ensure OPENAI_API_KEY secret is configured
   gcloud run services update pegasus-api \
     --region=us-central1 \
     --update-secrets=OPENAI_API_KEY=openai-api-key:latest
   ```

## Escalation

### When to Escalate

Escalate to on-call engineer if:
- Success rate remains <98% for >15 minutes
- No recovery progress after 30 minutes of troubleshooting
- Multiple different error types occurring simultaneously
- Vertex AI status page shows no issues but errors persist

### Escalation Contacts

1. **Platform Team**: platform-oncall@example.com
2. **Google Cloud Support**: Open ticket via Cloud Console
3. **Vertex AI Support**: For model-specific issues

### Creating a Support Ticket

```bash
# Gather diagnostic bundle
gcloud logging read 'resource.type="cloud_run_revision"
  AND resource.labels.service_name="pegasus-api"
  AND severity>=ERROR
  AND timestamp>="2024-01-01T00:00:00Z"' \
  --limit 100 \
  --format json > /tmp/pegasus-errors-$(date +%Y%m%d-%H%M%S).json

# Include in ticket:
# - Error log bundle (/tmp/pegasus-errors-*.json)
# - Timeline of when errors started
# - Recent deployment changes
# - Quota limits and current usage
# - Monitoring dashboard screenshot
```

## Post-Incident

After recovery:

1. **Document in incident log**:
   - Root cause
   - Time to detect (TTD)
   - Time to resolve (TTR)
   - Actions taken

2. **Update monitoring**:
   - Adjust alert thresholds if needed
   - Add new metrics if gap identified

3. **Prevent recurrence**:
   - Add automated safeguards
   - Update this runbook with lessons learned
   - Consider implementing circuit breakers

## Related Runbooks

- [Latency Investigation](./latency-investigation.md)
- [Backup & Restore](./backup-restore.md)
- [Migration Rollback](./migration-rollback.md)

## References

- [Vertex AI Error Codes](https://cloud.google.com/vertex-ai/docs/reference/rest#error-codes)
- [Cloud Run Troubleshooting](https://cloud.google.com/run/docs/troubleshooting)
- [Gemini API Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models)
