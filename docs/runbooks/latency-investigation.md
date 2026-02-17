# Gemini 3 Pro Latency Investigation Runbook

**Last Updated**: 2026-02-17
**Owner**: Platform Team
**Severity**: Warning

## Overview

This runbook helps investigate and mitigate high latency in Gemini 3 Pro generation requests. Use when:
- p95 latency exceeds 45 seconds for >10 minutes
- Maximum latency spikes above 120 seconds
- Alert: "Gemini 3 Pro - P95 Latency Above 45s" fires

## Context: Expected Latency

Gemini 3 Pro Preview uses extended reasoning ("thinking time"), so latency is inherently variable:

| Metric | Typical Range | Alert Threshold | Critical Threshold |
|--------|---------------|-----------------|-------------------|
| p50 (median) | 15-25s | N/A | N/A |
| p95 | 30-45s | 45s | 60s |
| p99 | 45-70s | N/A | 90s |
| Max | 60-120s | N/A | 180s |

**Factors affecting latency**:
1. **Transcript length** - More content → more reasoning time
2. **Prompt complexity** - Detailed instructions → longer processing
3. **Model capacity** - High demand → queueing delays
4. **Network conditions** - Geographic distance to global endpoint

## Quick Diagnosis (5 minutes)

### 1. Check Current Latency Distribution

```bash
# View latency metrics
curl -s https://pegasus-api-988514135894.us-central1.run.app/metrics \
  | grep "pegasus_thinking_duration_seconds"

# Output example:
# pegasus_thinking_duration_seconds_avg{model="gemini-3-pro-preview",status="success"} 32.5
# pegasus_thinking_duration_seconds_max{model="gemini-3-pro-preview",status="success"} 87.3
```

### 2. Identify Outliers

```bash
# Find slowest recent requests
gcloud logging read 'resource.type="cloud_run_revision"
  AND textPayload=~"Generated.*characters of JSON in"
  AND timestamp>="2024-01-01T00:00:00Z"' \
  --limit 50 \
  --format json \
  | jq -r '.[] | {time: .timestamp, latency: (.textPayload | capture("in (?<sec>[\\d.]+)s").sec), chars: (.textPayload | capture("Generated (?<chars>[\\d]+)").chars)}' \
  | jq -s 'sort_by(.latency | tonumber) | reverse | .[0:10]'
```

### 3. Correlate with Transcript Size

```bash
# Check transcript sizes for recent lectures
gsutil ls -lh gs://delta-student-486911-n5-pegasus-storage/pegasus/transcripts/*.json \
  | sort -k1 -h -r \
  | head -20

# Calculate average transcript size
gsutil du -s gs://delta-student-486911-n5-pegasus-storage/pegasus/transcripts/ \
  | awk '{print "Average transcript size: " $1/$(gsutil ls gs://delta-student-486911-n5-pegasus-storage/pegasus/transcripts/*.json | wc -l) " bytes"}'
```

## Investigation Procedures

### Scenario 1: Consistent High Latency (All Requests Slow)

**Symptoms**: p95 stays elevated, no outliers

**Diagnosis Steps**:

1. **Check Vertex AI service health**:
   ```bash
   # Google Cloud status
   open "https://status.cloud.google.com/"

   # Test global endpoint response time
   time curl -s -o /dev/null -w "%{time_total}\n" \
     "https://global-aiplatform.googleapis.com/v1/projects/delta-student-486911-n5/locations/global/publishers/google/models/gemini-3-pro-preview"
   ```

2. **Measure network latency**:
   ```bash
   # From Cloud Run to Vertex AI
   gcloud run jobs create latency-test \
     --image=gcr.io/google.com/cloudsdktool/cloud-sdk \
     --region=us-central1 \
     --command=sh,-c,"time curl -s https://global-aiplatform.googleapis.com" \
     --execute-now
   ```

3. **Check for model throttling**:
   ```bash
   # Look for "RESOURCE_EXHAUSTED" or "RATE_LIMIT_EXCEEDED" in logs
   gcloud logging read 'resource.type="cloud_run_revision"
     AND (textPayload=~"RESOURCE_EXHAUSTED" OR textPayload=~"RATE_LIMIT")
     AND timestamp>="2024-01-01T00:00:00Z"' \
     --limit 20
   ```

**Mitigation**:

If Vertex AI is slow globally:
- **No immediate action needed** - Service degradation is external
- Monitor Google Cloud status page for updates
- Consider temporary fallback to Gemini 2.0 Flash (faster, less reasoning)

If network latency is high:
- Check Cloud Run region (should be us-central1, closest to global endpoint)
- Verify VPC peering if using private service connect

### Scenario 2: Latency Spikes (Intermittent Slowness)

**Symptoms**: Max latency >120s, but p95 remains acceptable

**Diagnosis Steps**:

1. **Find the slow requests**:
   ```bash
   # Extract lecture IDs with >90s generation time
   gcloud logging read 'resource.type="cloud_run_revision"
     AND textPayload=~"Generated.*characters of JSON in [9-9][0-9]\\."
     AND timestamp>="2024-01-01T00:00:00Z"' \
     --limit 20 \
     --format json \
     | jq -r '.[] | .jsonPayload.lectureId'
   ```

2. **Analyze those transcripts**:
   ```bash
   # Download and inspect slow transcripts
   gsutil cp gs://delta-student-486911-n5-pegasus-storage/pegasus/transcripts/LECTURE_ID.json - \
     | jq '{length: (.text | length), segments: (.segments | length)}'
   ```

3. **Check for patterns**:
   - Are slow requests all >50KB transcripts?
   - Do they all use the same preset (e.g., research-mode)?
   - Is there a specific time of day pattern?

**Mitigation**:

If transcript size is the issue:
```python
# Add to pipeline/llm_generation.py (before generation)
MAX_CHARS = 400_000  # ~100K tokens
if len(transcript) > MAX_CHARS:
    print(f"[LLM Generation] WARNING: Transcript too long ({len(transcript)} chars), truncating to {MAX_CHARS}")
    transcript = transcript[:MAX_CHARS] + "\n\n[Transcript truncated due to length. Summary may be incomplete.]"
```

If preset is the issue (e.g., research-mode requires more reasoning):
- Update preset documentation to warn about longer processing time
- Consider separate SLOs per preset complexity level
- Offer "fast mode" option that uses simpler prompts

### Scenario 3: Latency Increases Over Time (Trend)

**Symptoms**: p95 was 30s last week, now consistently 50s+

**Diagnosis Steps**:

1. **Check historical trends**:
   ```bash
   # View 7-day latency trend in monitoring
   open "https://console.cloud.google.com/monitoring/dashboards"
   ```

2. **Correlate with transcript growth**:
   ```bash
   # Average transcript size over time
   gsutil ls -l gs://delta-student-486911-n5-pegasus-storage/pegasus/transcripts/*.json \
     | awk '{sum+=$1; count++} END {print "Average size: " sum/count " bytes"}'
   ```

3. **Check for prompt drift**:
   ```bash
   # Review recent changes to generation prompts
   git log --since="7 days ago" -- pipeline/llm_generation.py backend/presets.py
   ```

**Root Causes**:
- Users uploading longer lectures over time
- Prompt complexity increased with recent preset updates
- Vertex AI model version change (preview models can update)

**Mitigation**:

1. **Implement adaptive truncation**:
   ```python
   # Smart truncation: Keep first 70% and last 30% of transcript
   def smart_truncate(text: str, max_chars: int = 400_000) -> str:
       if len(text) <= max_chars:
           return text
       keep_start = int(max_chars * 0.7)
       keep_end = int(max_chars * 0.3)
       return text[:keep_start] + "\n\n[... middle section truncated ...]\n\n" + text[-keep_end:]
   ```

2. **Add chunking for very long transcripts**:
   - Split transcript into semantic sections
   - Generate artifacts per section
   - Merge results intelligently

3. **Optimize prompts**:
   - Remove verbose instructions
   - Use more concise examples
   - Reduce special_instructions length

### Scenario 4: P99/Max Latency Acceptable but P95 High

**Symptoms**: Max ~60s (good), but p95 ~55s (high)

**Interpretation**: Most requests are slow, but no extreme outliers

**Diagnosis**:

This suggests systemic slowness, not transcript-specific issues.

1. **Check if it's time-of-day dependent**:
   ```bash
   # Group latency by hour
   gcloud logging read 'textPayload=~"Generated.*in"' \
     --format json \
     | jq -r '.[] | {hour: (.timestamp[11:13]), latency: (.textPayload | capture("in (?<sec>[\\d.]+)s").sec)}' \
     | jq -s 'group_by(.hour) | map({hour: .[0].hour, avg: (map(.latency | tonumber) | add / length)})'
   ```

2. **Check concurrent request patterns**:
   ```bash
   # Count requests per minute
   gcloud logging read 'textPayload=~"Generating via global Vertex AI"' \
     --format json \
     | jq -r '.[] | .timestamp[0:16]' \
     | sort | uniq -c
   ```

**Mitigation**:

If high concurrency is causing throttling:
- Implement request queuing with rate limiting
- Add exponential backoff between retries
- Request quota increase from Google

## Performance Optimization

### 1. Reduce Prompt Token Count

**Current prompt structure** (from `pipeline/llm_generation.py`):
- Base instructions: ~1,500 tokens
- Preset configuration: ~500 tokens
- Transcript: Variable (5K-50K tokens)
- Examples/schemas: ~1,000 tokens

**Optimization strategies**:

```python
# BEFORE: Verbose instructions
base_prompt = """
You are generating structured study artifacts for Pegasus Lecture Copilot.
Return STRICT JSON only. You MUST return a JSON OBJECT (not an array) with these exact keys:
summary, outline, key_terms, flashcards, exam_questions.

All artifacts must include: id, courseId, lectureId, presetId, artifactType, generatedAt, version.
"""

# AFTER: Concise instructions
base_prompt = """
Generate study artifacts as JSON object with keys: summary, outline, key_terms, flashcards, exam_questions.
Include metadata: id, courseId, lectureId, presetId, artifactType, generatedAt, version.
"""
```

### 2. Implement Streaming (Future Enhancement)

Gemini models support streaming responses. This doesn't reduce total latency but improves perceived performance:

```python
# Future: Stream response and process incrementally
response = generative_model.generate_content(
    [prompt, user_content],
    generation_config=generation_config,
    stream=True  # Enable streaming
)

for chunk in response:
    # Process partial results as they arrive
    partial_text += chunk.text
```

### 3. Cache Prompts (Future Enhancement)

For repeated generation with same preset, cache the system prompt:

```python
# Use Vertex AI caching (when available for Gemini 3)
from vertexai.preview.caching import CachedContent

cached_prompt = CachedContent.create(
    model_name="gemini-3-pro-preview",
    system_instruction=base_prompt,
    ttl=3600  # 1 hour cache
)
```

## Alerting Adjustments

If latency consistently stays in 45-60s range (above SLO but acceptable):

### Option 1: Adjust Alert Threshold

```hcl
# In monitoring/alerts.tf
threshold_value = 60.0  # Increase from 45s to 60s
```

### Option 2: Add Hysteresis

Require sustained high latency before alerting:

```hcl
duration = "900s"  # Increase from 600s to 900s (15 minutes)
```

### Option 3: Make Alert Less Sensitive

```hcl
trigger {
  count = 2  # Require 2 consecutive violations instead of 1
}
```

## Success Criteria

Latency is considered resolved when:
- [ ] p95 latency < 45 seconds (or adjusted target)
- [ ] No requests timeout (300s limit)
- [ ] p99 latency < 90 seconds
- [ ] Alert stops firing for >30 minutes

## Escalation

Escalate if:
- Latency >120s persists for >1 hour
- Requests timing out (300s)
- No clear transcript size correlation
- Vertex AI status page shows no issues

Contact: platform-oncall@example.com

## Related Runbooks

- [Gemini Failure Recovery](./gemini-failure-recovery.md)
- [Quota Management](./quota-management.md)
- [Performance Tuning](./performance-tuning.md)

## References

- [Vertex AI Latency Best Practices](https://cloud.google.com/vertex-ai/docs/predictions/optimize-latency)
- [Gemini Model Performance](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models)
- [Cloud Run Performance Tuning](https://cloud.google.com/run/docs/tips/general)
