import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[3]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_readme_explains_role_evidence_match_and_limitations() -> None:
    source = read("README.md")
    for phrase in [
        "Role Evidence Match",
        "evidence-based",
        "eligibility",
        "confidence",
        "not a hiring probability",
        "guides/role-evidence-match.md",
    ]:
        assert phrase in source


def test_detailed_guide_documents_the_public_scoring_contract() -> None:
    source = read("guides/role-evidence-match.md")
    for phrase in [
        "30%",
        "Relevant competencies",
        "Source multipliers",
        "Relationship ceilings",
        "Technology volatility and recency",
        "shrink toward neutral",
        "Unsupported essential requirements",
        "45% known requirement coverage",
        "Fairness guardrails",
        "No reliable evidence, no authoritative score",
        "Versioned analysis snapshots",
        "Golden evaluation suite",
        "Legacy AI fit score",
        "not a hiring probability",
    ]:
        assert phrase in source


def test_upgrade_guide_covers_migration_and_legacy_history() -> None:
    source = read("guides/upgrading.md")
    assert "v1.3.0" in source
    assert "make migrate" in source
    assert "Legacy AI fit score" in source
    assert "not recalculated" in source
    assert "role_match_analysis" in source


def test_release_metadata_is_v1_3_0() -> None:
    backend = read("backend/pyproject.toml")
    frontend = json.loads(read("frontend/package.json"))
    lock = read("backend/uv.lock")
    changelog = read("CHANGELOG.md")

    assert re.search(r'^version = "1\.3\.0"$', backend, re.MULTILINE)
    assert frontend["version"] == "1.3.0"
    assert re.search(
        r'name = "backend"\nversion = "1\.3\.0"',
        lock,
        re.MULTILINE,
    )
    assert "## [1.3.0]" in changelog
    assert "[1.3.0]: https://github.com/wihlarkop/applykit/releases/tag/v1.3.0" in changelog
