# Gemini 3 Pro SLO Alert Policies for Cloud Monitoring
# Deploy with: terraform apply -var="project_id=delta-student-486911-n5"

variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "delta-student-486911-n5"
}

variable "notification_channels" {
  description = "List of notification channel IDs (email, Slack, PagerDuty)"
  type        = list(string)
  default     = []
}

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = "us-central1"
}

# Alert: Success Rate Below 98%
resource "google_monitoring_alert_policy" "gemini_success_rate_slo" {
  display_name = "Gemini 3 Pro - Success Rate Below 98% (SLO Violation)"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "Success rate below 98%"

    condition_threshold {
      filter          = <<-EOT
        resource.type = "prometheus_target"
        AND metric.type = "prometheus.googleapis.com/pegasus_thinking_requests_total/counter"
        AND metric.label.model = "gemini-3-pro-preview"
      EOT
      duration        = "300s"
      comparison      = "COMPARISON_LT"
      threshold_value = 0.98

      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
        group_by_fields      = ["metric.label.status"]
      }

      trigger {
        count = 1
      }
    }
  }

  documentation {
    content   = <<-EOT
      ## Alert: Gemini 3 Pro Success Rate Below SLO

      **Severity**: Critical
      **SLO Target**: 98% success rate

      ### Immediate Actions:
      1. Check Cloud Logging for error patterns: `resource.type="cloud_run_revision" AND textPayload=~"Vertex AI Error"`
      2. Verify Gemini API quota and rate limits in GCP Console
      3. Check Cloud Run service health and error rates
      4. Review recent deployments or configuration changes

      ### Escalation:
      If success rate remains below 98% for >15 minutes, page on-call engineer.

      ### Runbook:
      See `docs/runbooks/gemini-failure-recovery.md`
    EOT
    mime_type = "text/markdown"
  }

  notification_channels = var.notification_channels

  alert_strategy {
    auto_close = "1800s"

    notification_rate_limit {
      period = "300s"
    }
  }

  severity = "CRITICAL"
}

# Alert: P95 Latency Above 45s
resource "google_monitoring_alert_policy" "gemini_latency_slo" {
  display_name = "Gemini 3 Pro - P95 Latency Above 45s (Performance SLO)"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "P95 latency > 45 seconds"

    condition_threshold {
      filter          = <<-EOT
        resource.type = "prometheus_target"
        AND metric.type = "prometheus.googleapis.com/pegasus_thinking_duration_seconds_avg/gauge"
        AND metric.label.model = "gemini-3-pro-preview"
        AND metric.label.status = "success"
      EOT
      duration        = "600s"
      comparison      = "COMPARISON_GT"
      threshold_value = 45.0

      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_MEAN"
        cross_series_reducer = "REDUCE_PERCENTILE_95"
      }

      trigger {
        count = 1
      }
    }
  }

  documentation {
    content   = <<-EOT
      ## Alert: Gemini 3 Pro Latency Exceeds Target

      **Severity**: Warning
      **SLO Target**: p95 latency < 45 seconds

      ### Context:
      Gemini 3 Pro uses extended reasoning, so some variance is expected. However, sustained high latency indicates:
      - Network issues to Vertex AI global endpoint
      - Model capacity constraints
      - Unusually complex input prompts

      ### Immediate Actions:
      1. Check current p95 latency trend in monitoring dashboard
      2. Review recent transcript sizes (unusually long transcripts increase reasoning time)
      3. Verify network latency to global Vertex AI endpoint
      4. Check for Vertex AI service incidents: https://status.cloud.google.com/

      ### Mitigation:
      If latency is consistently >60s, consider:
      - Splitting large transcripts into chunks
      - Adjusting max_output_tokens to reduce generation time
      - Reviewing prompt complexity

      ### Runbook:
      See `docs/runbooks/latency-investigation.md`
    EOT
    mime_type = "text/markdown"
  }

  notification_channels = var.notification_channels

  alert_strategy {
    auto_close = "1800s"

    notification_rate_limit {
      period = "600s"
    }
  }

  severity = "WARNING"
}

# Alert: High Error Rate
resource "google_monitoring_alert_policy" "gemini_error_rate" {
  display_name = "Gemini 3 Pro - High Error Rate (>2% errors)"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "Error rate > 2%"

    condition_threshold {
      filter          = <<-EOT
        resource.type = "prometheus_target"
        AND metric.type = "prometheus.googleapis.com/pegasus_thinking_requests_total/counter"
        AND metric.label.model = "gemini-3-pro-preview"
        AND metric.label.status = "error"
      EOT
      duration        = "600s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.02

      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
      }

      trigger {
        count = 1
      }
    }
  }

  documentation {
    content   = <<-EOT
      ## Alert: Gemini 3 Pro Error Rate Elevated

      **Severity**: Warning
      **Threshold**: >2% error rate over 10 minutes

      ### Common Error Types:
      - **ResourceExhausted**: Quota or rate limit exceeded
      - **DeadlineExceeded**: Request timeout (>300s)
      - **InvalidArgument**: Malformed prompt or generation config
      - **PermissionDenied**: API key or service account issue

      ### Immediate Actions:
      1. Check error breakdown in monitoring dashboard
      2. Review Cloud Logging for specific error messages
      3. Verify Vertex AI quotas: `gcloud alpha services quota list --service=aiplatform.googleapis.com`
      4. Check service account permissions for Cloud Run

      ### Recovery:
      See error-specific recovery steps in `docs/runbooks/gemini-failure-recovery.md`
    EOT
    mime_type = "text/markdown"
  }

  notification_channels = var.notification_channels

  alert_strategy {
    auto_close = "1800s"
  }

  severity = "WARNING"
}

# Outputs
output "alert_policy_ids" {
  description = "Alert policy resource IDs"
  value = {
    success_rate_slo = google_monitoring_alert_policy.gemini_success_rate_slo.id
    latency_slo      = google_monitoring_alert_policy.gemini_latency_slo.id
    error_rate       = google_monitoring_alert_policy.gemini_error_rate.id
  }
}
