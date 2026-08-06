from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.role_match.domain import (
    AnalysisState,
    AtomicRequirement,
    EvidenceDepth,
    EvidenceLink,
    EvidenceRelationship,
    RequirementCategory,
    RequirementImportance,
    TechnologyVolatility,
)
from app.role_match.extraction import ExtractionResult
from app.role_match.linking import LinkingResult
from app.role_match.models import (
    RoleMatchAnalysis,
    RoleMatchEvidence,
    RoleMatchRequirement,
)
from app.role_match.pipeline import analyze_role_match
from app.schemas import ProfileData


def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def profile() -> ProfileData:
    return ProfileData(
        id=1,
        name="Candidate",
        email="candidate@example.com",
        summary="Backend engineer",
        work_experience=[
            {
                "company": "Example",
                "role": "Backend Engineer",
                "start_date": "2023-01",
                "end_date": None,
                "bullets": ["Built production APIs using FastAPI."],
            }
        ],
        education=[],
        skills=["Python", "FastAPI"],
        projects=[],
        certifications=[],
    )


def extraction() -> ExtractionResult:
    return ExtractionResult(
        state=AnalysisState.EXTRACTED,
        requirements=[
            AtomicRequirement(
                source_id="jd:1",
                text="Production Python backend capability",
                canonical_key="python-backend",
                primary_category=RequirementCategory.RELEVANT_COMPETENCIES,
                importance=RequirementImportance.CRITICAL,
                source_quote="Strong Python experience is required",
                volatility=TechnologyVolatility.EVOLVING,
            ),
            AtomicRequirement(
                source_id="jd:2",
                text="Build production APIs",
                canonical_key="production-apis",
                primary_category=RequirementCategory.RELEVANT_WORK_TASKS,
                importance=RequirementImportance.CRITICAL,
                source_quote="Build production APIs",
                volatility=TechnologyVolatility.STABLE,
            ),
            AtomicRequirement(
                source_id="jd:3",
                text="Relevant backend experience",
                canonical_key="backend-experience",
                primary_category=RequirementCategory.ESSENTIAL_QUALIFICATIONS,
                importance=RequirementImportance.CRITICAL,
                source_quote="Relevant backend experience required",
                volatility=TechnologyVolatility.STABLE,
            ),
        ],
        raw_outputs=["{}"],
    )


def linking(clusters, catalog) -> LinkingResult:
    work = next(item for item in catalog if item.evidence_id == "work:0:bullet:0")
    links = [
        EvidenceLink(
            requirement_id=cluster.cluster_id,
            evidence_id=work.evidence_id,
            source=work.source,
            relationship=EvidenceRelationship.EXACT,
            depth=EvidenceDepth.PRODUCTION_OWNERSHIP,
            volatility=cluster.volatility,
            is_current=True,
            explanation="Direct production evidence",
        )
        for cluster in clusters
    ]
    return LinkingResult(valid_links=links, invalid_link_count=0, raw_output="{}")


def test_pipeline_persists_immutable_analysis(monkeypatch) -> None:
    db = db_session()
    monkeypatch.setattr(
        "app.role_match.pipeline.extract_atomic_requirements",
        lambda *args, **kwargs: extraction(),
    )
    monkeypatch.setattr(
        "app.role_match.pipeline.link_candidate_evidence",
        lambda clusters, catalog, *args, **kwargs: linking(clusters, catalog),
    )
    analysis = analyze_role_match(
        db=db,
        profile=profile(),
        job_description="Python backend role",
        provider="openai",
        api_key="secret",
        application_id=None,
        parent_analysis_id=None,
        analysis_date=date(2026, 8, 6),
    )
    assert analysis.state == "success"
    assert analysis.show_authoritative_score is True
    assert analysis.display_score is not None
    assert analysis.display_score % 5 == 0
    assert db.query(RoleMatchRequirement).count() == 3
    assert db.query(RoleMatchEvidence).count() == 3


def test_provider_failure_is_audited_without_guessed_score(monkeypatch) -> None:
    db = db_session()
    monkeypatch.setattr(
        "app.role_match.pipeline.extract_atomic_requirements",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("provider unavailable")
        ),
    )
    analysis = analyze_role_match(
        db=db,
        profile=profile(),
        job_description="Python backend role",
        provider="openai",
        api_key="secret",
        application_id=None,
        parent_analysis_id=None,
        analysis_date=date(2026, 8, 6),
    )
    assert analysis.state == "failed"
    assert analysis.show_authoritative_score is False
    assert analysis.raw_score is None
    assert analysis.display_score is None
    assert analysis.failure_code == "provider_failure"
    assert db.query(RoleMatchAnalysis).count() == 1
