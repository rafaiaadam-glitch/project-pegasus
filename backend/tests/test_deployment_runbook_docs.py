from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_canonical_deployment_guide_exists_with_required_scope() -> None:
    content = _read("docs/runbooks/deployment-guide.md")
    assert "Canonical Deployment Guide" in content
    assert "API + Worker + Storage" in content
    assert "Render" in content and "Railway" in content and "Fly.io" in content


def test_staging_parity_checklist_exists_with_signoff() -> None:
    content = _read("docs/runbooks/staging-environment-parity-checklist.md")
    assert "Staging Environment Parity Checklist" in content
    assert "## Sign-off template" in content
    assert "`/health/ready`" in content


def test_release_checklist_includes_rollback_procedure() -> None:
    content = _read("docs/runbooks/release-checklist.md")
    assert "Release Checklist with Rollback Procedure" in content
    assert "## Rollback procedure" in content
    assert "migration-rollback.md" in content
