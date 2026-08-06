import json

from app.role_match.domain import (
    EvidenceCatalogItem,
    EvidenceSource,
    RequirementCategory,
    RequirementCluster,
    RequirementImportance,
    TechnologyVolatility,
)
from app.role_match.extraction import extract_atomic_requirements
from app.role_match.linking import link_candidate_evidence


def requirement_cluster() -> RequirementCluster:
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


def test_role_match_uses_positional_llm_prompt_contract(monkeypatch) -> None:
    prompts: list[str] = []

    def strict_call_llm(
        prompt: str,
        *,
        system: str,
        provider: str,
        api_key: str,
        timeout: int,
        operation: str,
        profile_id: int | None,
    ) -> str:
        del system, provider, api_key, timeout, profile_id
        prompts.append(prompt)
        if operation == "role_match_extraction":
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
        return json.dumps(
            {
                "links": [
                    {
                        "requirement_id": "req:python-backend",
                        "evidence_id": "work:0:bullet:0",
                        "relationship": "exact",
                        "depth": "production_ownership",
                        "explanation": "Direct work evidence",
                    }
                ]
            }
        )

    monkeypatch.setattr("app.services.llm.call_llm", strict_call_llm)

    extraction = extract_atomic_requirements(
        "Strong Python experience is required",
        "openai",
        "secret",
        profile_id=1,
    )
    linking = link_candidate_evidence(
        [requirement_cluster()],
        [
            EvidenceCatalogItem(
                evidence_id="work:0:bullet:0",
                source=EvidenceSource.WORK_EXPERIENCE,
                text="Built production Python services",
            )
        ],
        "openai",
        "secret",
        profile_id=1,
    )

    assert len(extraction.requirements) == 1
    assert len(linking.valid_links) == 1
    assert len(prompts) == 2
    assert "job_description" in prompts[0]
    assert "evidence_catalog" in prompts[1]
