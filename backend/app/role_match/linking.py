from __future__ import annotations

from collections import defaultdict
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.role_match.dates import parse_profile_date
from app.role_match.domain import (
    EvidenceCatalogItem,
    EvidenceDepth,
    EvidenceLink,
    EvidenceRelationship,
    RequirementCluster,
)
from app.role_match.prompts import EVIDENCE_LINKING_SYSTEM_PROMPT
from app.role_match.structured import parse_json_model
from app.services.prompts import format_untrusted_input


class EvidenceLinkProposal(BaseModel):
    requirement_id: str
    evidence_id: str
    relationship: EvidenceRelationship
    depth: EvidenceDepth
    is_contradiction: bool = False
    explanation: str = ""


class EvidenceLinkingPayload(BaseModel):
    links: list[EvidenceLinkProposal]


class LinkingResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    valid_links: list[EvidenceLink] = []
    invalid_link_count: int = 0
    raw_output: str = ""


def _call_llm(**kwargs) -> str:
    from app.services.llm import call_llm

    return call_llm(**kwargs)


def _last_used(item: EvidenceCatalogItem) -> tuple[date | None, bool]:
    if item.source.value == "work_experience" and not item.end_date:
        return None, True
    return parse_profile_date(item.end_date, end_of_period=True), False


def link_candidate_evidence(
    clusters: list[RequirementCluster],
    catalog: list[EvidenceCatalogItem],
    provider: str,
    api_key: str,
    *,
    profile_id: int | None = None,
) -> LinkingResult:
    raw = _call_llm(
        user_prompt="\n".join(
            [
                format_untrusted_input(
                    "requirements",
                    [cluster.model_dump(mode="json") for cluster in clusters],
                ),
                format_untrusted_input(
                    "evidence_catalog",
                    [item.model_dump(mode="json") for item in catalog],
                ),
                "Link only supplied IDs and return JSON with a links array.",
            ]
        ),
        system=EVIDENCE_LINKING_SYSTEM_PROMPT,
        provider=provider,
        api_key=api_key,
        timeout=45,
        operation="role_match_evidence",
        profile_id=profile_id,
    )
    try:
        payload = parse_json_model(raw, EvidenceLinkingPayload)
    except Exception:
        return LinkingResult(raw_output=raw, invalid_link_count=1)

    requirement_map = {item.cluster_id: item for item in clusters}
    evidence_map = {item.evidence_id: item for item in catalog}
    seen_duplicate_keys: dict[str, set[str]] = defaultdict(set)
    valid: list[EvidenceLink] = []
    invalid = 0

    for proposal in payload.links:
        requirement = requirement_map.get(proposal.requirement_id)
        evidence = evidence_map.get(proposal.evidence_id)
        if requirement is None or evidence is None:
            invalid += 1
            continue
        duplicate_key = evidence.duplicate_key or evidence.evidence_id
        duplicate = duplicate_key in seen_duplicate_keys[requirement.cluster_id]
        seen_duplicate_keys[requirement.cluster_id].add(duplicate_key)
        last_used, is_current = _last_used(evidence)
        valid.append(
            EvidenceLink(
                requirement_id=requirement.cluster_id,
                evidence_id=evidence.evidence_id,
                source=evidence.source,
                relationship=proposal.relationship,
                depth=proposal.depth,
                volatility=requirement.volatility,
                last_used_date=last_used,
                is_current=is_current,
                is_duplicate=duplicate,
                is_contradiction=proposal.is_contradiction,
                explanation=proposal.explanation,
            )
        )

    return LinkingResult(
        valid_links=valid,
        invalid_link_count=invalid,
        raw_output=raw,
    )
