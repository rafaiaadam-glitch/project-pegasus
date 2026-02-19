from pathlib import Path


ALERT_RULES_PATH = Path(__file__).resolve().parents[2] / "ops" / "monitoring" / "prometheus-alert-rules.yml"


def _load_text() -> str:
    return ALERT_RULES_PATH.read_text(encoding="utf-8")


def test_alert_rules_file_exists() -> None:
    assert ALERT_RULES_PATH.exists(), f"missing alert rules file: {ALERT_RULES_PATH}"


def test_required_alerts_exist() -> None:
    content = _load_text()
    required = (
        "alert: PegasusQueueBacklogSustained",
        "alert: PegasusFailureRateSpike",
    )
    for name in required:
        assert name in content, f"missing required alert rule: {name}"


def test_rules_reference_exposed_prometheus_metrics() -> None:
    content = _load_text()
    assert "sum(pegasus_queue_depth) > 25" in content
    assert "pegasus_job_status_events_total" in content
    assert "pegasus_job_failures_total{job_type=\"generate\"}" in content
