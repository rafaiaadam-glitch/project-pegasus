import json
from pathlib import Path


DASHBOARD_PATH = Path(__file__).resolve().parents[2] / "ops" / "monitoring" / "grafana-pipeline-dashboard.json"


REQUIRED_PANEL_TITLES = {
    "Queue depth (all statuses)",
    "Per-stage average latency (ms)",
    "Per-stage max latency (ms)",
    "Failure rate by stage (15m)",
    "Retries by stage (15m)",
}


def test_dashboard_file_exists() -> None:
    assert DASHBOARD_PATH.exists(), f"missing dashboard config: {DASHBOARD_PATH}"


def test_dashboard_has_required_panels() -> None:
    dashboard = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))
    titles = {panel.get("title") for panel in dashboard.get("panels", [])}
    assert REQUIRED_PANEL_TITLES.issubset(titles)


def test_dashboard_queries_use_pegasus_metrics() -> None:
    dashboard = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))
    expressions = [
        target.get("expr", "")
        for panel in dashboard.get("panels", [])
        for target in panel.get("targets", [])
    ]
    assert any("pegasus_queue_depth" in expr for expr in expressions)
    assert any("pegasus_job_latency_ms_avg" in expr for expr in expressions)
    assert any("pegasus_job_latency_ms_max" in expr for expr in expressions)
    assert any("pegasus_job_status_events_total" in expr for expr in expressions)
    assert any("pegasus_job_retries_total" in expr for expr in expressions)
