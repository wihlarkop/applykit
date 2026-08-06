from pathlib import Path

from app.role_match.models import (
    RoleMatchAnalysis,
    RoleMatchEvidence,
    RoleMatchOverride,
    RoleMatchRequirement,
)


def test_role_match_analysis_has_audit_columns() -> None:
    columns = RoleMatchAnalysis.__table__.columns
    for name in [
        "parent_analysis_id",
        "superseded_by_id",
        "analysis_date",
        "job_description_hash",
        "safe_profile_snapshot",
        "safe_profile_hash",
        "rules_version",
        "prompt_version",
        "raw_llm_output",
        "normalized_payload",
        "scoring_payload",
        "raw_score",
        "display_score",
        "confidence_score",
        "eligibility_status",
        "show_authoritative_score",
        "failure_code",
        "excluded_items",
    ]:
        assert name in columns


def test_child_tables_use_cascade_foreign_keys() -> None:
    assert next(iter(RoleMatchRequirement.__table__.foreign_keys)).ondelete == "CASCADE"
    evidence_deletes = {fk.ondelete for fk in RoleMatchEvidence.__table__.foreign_keys}
    assert "CASCADE" in evidence_deletes
    override_deletes = {fk.ondelete for fk in RoleMatchOverride.__table__.foreign_keys}
    assert "CASCADE" in override_deletes


def test_migration_is_based_on_current_head_and_reversible() -> None:
    source = (
        Path(__file__).parents[2]
        / "migrations/versions/c4a7e9f21b6d_add_role_match_analysis.py"
    ).read_text()
    assert 'down_revision: str | Sequence[str] | None = "f3a1b2c4d5e6"' in source
    assert 'op.create_table(\n        "role_match_analysis"' in source
    assert 'op.drop_table("role_match_analysis")' in source
