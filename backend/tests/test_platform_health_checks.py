from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_render_web_service_has_readiness_health_check() -> None:
    render_yaml = _read("render.yaml")
    assert "healthCheckPath: /health/ready" in render_yaml


def test_railway_deploy_has_readiness_health_check() -> None:
    railway_toml = _read("railway.toml")
    assert 'healthcheckPath = "/health/ready"' in railway_toml
    assert "healthcheckTimeout = 180" in railway_toml


def test_fly_http_service_has_readiness_probe() -> None:
    fly_toml = _read("fly.toml")
    assert "[[http_service.checks]]" in fly_toml
    assert 'path = "/health/ready"' in fly_toml
