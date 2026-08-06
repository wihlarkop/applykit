import json

from app.role_match.domain import (
    AnalysisState,
    EvidenceCatalogItem,
    EvidenceSource,
    RequirementCategory,
    RequirementCluster,
    RequirementImportance,
    TechnologyVolatility,
)
from app.role_match.extraction import extract_atomic_requirements
from app.role_match.linking import link_candidate_evidence


def valid_extraction_json() -> str:
    return json.dumps(
        {
            "requirements": [
                {
                    "source_id": "jd:1",
                    "text": "Production Python backend capability",
                    "canonical_key": "python-backend",
                    "primary_category": "relevant_competencies",
                    "importance": "critical",
                    "source_quote": "Strong Python experience is required",
                    "volatility": "evolving",
                    "tool_specificity": "capability",
                }
            ]
        }
    )


def cluster() -> RequirementCluster:
    return RequirementCluster(
        cluster_id="req:python-backend",
        canonical_requirement="Production Python backend capability",
        canonical_key="python-backend",
        primary_category=RequirementCategory.RELEVANT_COMPETENCIES,
        importance=RequirementImportance.CRITICAL,
        mention_count=1,
        importance_conflict=False,
        importance_mentions={
            RequirementImportance.CRITICAL: 1,
            RequirementImportance.IMPORTANT: 0,
            RequirementImportance.SUPPORTING: 0,
        },
        source_quotes=["Strong Python experience is required"],
        source_ids=["jd:1"],
        is_eligibility=False,
        is_trainable=False,
        volatility=TechnologyVolatility.EVOLVING,
        tool_specificity="capability",
    )


def test_extraction_retries_once_after_invalid_json(monkeypatch) -> None:
    outputs = iter(["not-json", valid_extraction_json()])
    monkeypatch.setattr("app.role_match.extraction._call_llm", lambda **_: next(outputs))
    result = extract_atomic_requirements("Python backend role", "openai", "secret", profile_id=1)
    assert result.state == AnalysisState.EXTRACTED
    assert len(result.requirements) == 1
    assert len(result.raw_outputs) == 2


def test_extraction_returns_review_state_after_two_invalid_outputs(monkeypatch) -> None:
    outputs = iter(["not-json", '{"requirements":"invalid"}'])
    monkeypatch.setattr("app.role_match.extraction._call_llm", lambda **_: next(outputs))
    result = extract_atomic_requirements("Python backend role", "openai", "secret", profile_id=1)
    assert result.state == AnalysisState.NEEDS_REVIEW
    assert result.failure_code == "invalid_requirement_extraction"
    assert len(result.raw_outputs) == 2


def test_linking_rejects_unknown_evidence_ids(monkeypatch) -> None:
    raw = json.dumps({"links": [{"requirement_id": "req:python-backend", "evidence_id": "work:9:bullet:9", "relationship": "exact", "depth": "production_ownership", "is_contradiction": False, "explanation": "Direct Python evidence"}]})
    monkeypatch.setattr("app.role_match.linking._call_llm", lambda **_: raw)
    result = link_candidate_evidence(
        [cluster()],
        [EvidenceCatalogItem(evidence_id="work:0:bullet:0", source=EvidenceSource.WORK_EXPERIENCE, text="Built FastAPI services", start_date="2024-01", end_date=None, duplicate_key="built fastapi services")],
        "openai",
        "secret",
        profile_id=1,
    )
    assert result.valid_links == []
    assert result.invalid_link_count == 1


def test_linking_uses_catalog_source_and_marks_duplicate(monkeypatch) -> None:
    raw = json.dumps({"links": [
        {"requirement_id": "req:python-backend", "evidence_id": "work:0:bullet:0", "relationship": "exact", "depth": "production_ownership", "is_contradiction": False, "explanation": "Direct evidence"},
        {"requirement_id": "req:python-backend", "evidence_id": "summary:0", "relationship": "exact", "depth": "hands_on_contribution", "is_contradiction": False, "explanation": "Repeated summary evidence"},
    ]})
    monkeypatch.setattr("app.role_match.linking._call_llm", lambda **_: raw)
    result = link_candidate_evidence(
        [cluster()],
        [
            EvidenceCatalogItem(evidence_id="work:0:bullet:0", source=EvidenceSource.WORK_EXPERIENCE, text="Built FastAPI services", start_date="2024-01", end_date=None, duplicate_key="built fastapi services"),
            EvidenceCatalogItem(evidence_id="summary:0", source=EvidenceSource.SKILLS_LIST, text="Built FastAPI services", duplicate_key="built fastapi services"),
        ],
        "openai",
        "secret",
        profile_id=1,
    )
    assert result.valid_links[0].source == EvidenceSource.WORK_EXPERIENCE
    assert result.valid_links[0].is_duplicate is False
    assert result.valid_links[1].source == EvidenceSource.SKILLS_LIST
    assert result.valid_links[1].is_duplicate is True
