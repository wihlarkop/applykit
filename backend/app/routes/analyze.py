from datetime import date

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_profile_or_404, require_llm_config
from app.exceptions import (
    RoleMatchAnalysisNotFoundError,
    RoleMatchProfileRequiredError,
)
from app.role_match.api_schemas import (
    RoleMatchAnalysisResponse,
    RoleMatchAnalyzeRequest,
    RoleMatchComparisonResponse,
    RoleMatchOverridesRequest,
    RoleMatchReanalyzeRequest,
    RoleMatchVersionsResponse,
)
from app.role_match.overrides import apply_user_overrides
from app.role_match.pipeline import analyze_role_match
from app.role_match.repository import (
    compare_analyses,
    get_analysis,
    list_versions,
    serialize_analysis,
)
from app.role_match.restore import restore_user_override
from app.schemas import FitAnalysisRequest, FitAnalysisResponse
from app.services.fit_analysis import analyze_fit
from app.utils import format_profile_for_llm, profile_to_schema

router = APIRouter()


@router.post("/analyze/fit", response_model=FitAnalysisResponse)
def analyze_fit_endpoint(
    body: FitAnalysisRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    response.headers["Warning"] = (
        '299 - "Deprecated fit analysis contract; use /api/analyze/role-match"'
    )
    profile = get_profile_or_404(body.profile_id, db)
    provider, api_key = require_llm_config(db)
    profile_data = profile_to_schema(profile)
    profile_json = format_profile_for_llm(profile_data)

    return analyze_fit(
        profile_json,
        body.job_description,
        provider,
        api_key,
        profile_id=body.profile_id,
    )


@router.post("/analyze/role-match", response_model=RoleMatchAnalysisResponse)
def analyze_role_match_endpoint(
    body: RoleMatchAnalyzeRequest,
    db: Session = Depends(get_db),
):
    profile = get_profile_or_404(body.profile_id, db)
    provider, api_key = require_llm_config(db)
    analysis = analyze_role_match(
        db=db,
        profile=profile_to_schema(profile),
        job_description=body.job_description,
        provider=provider,
        api_key=api_key,
        application_id=body.application_id,
        parent_analysis_id=body.parent_analysis_id,
        analysis_date=date.today(),
    )
    return serialize_analysis(db, analysis)


@router.get(
    "/analyze/role-match/{analysis_id}",
    response_model=RoleMatchAnalysisResponse,
)
def get_role_match_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
):
    analysis = get_analysis(db, analysis_id)
    if analysis is None:
        raise RoleMatchAnalysisNotFoundError(analysis_id)
    return serialize_analysis(db, analysis)


@router.get(
    "/analyze/role-match/{analysis_id}/versions",
    response_model=RoleMatchVersionsResponse,
)
def get_role_match_versions(
    analysis_id: int,
    db: Session = Depends(get_db),
):
    analysis = get_analysis(db, analysis_id)
    if analysis is None:
        raise RoleMatchAnalysisNotFoundError(analysis_id)
    return list_versions(db, analysis)


@router.get(
    "/analyze/role-match/{analysis_id}/compare/{other_analysis_id}",
    response_model=RoleMatchComparisonResponse,
)
def compare_role_match_analyses(
    analysis_id: int,
    other_analysis_id: int,
    db: Session = Depends(get_db),
):
    before = get_analysis(db, analysis_id)
    if before is None:
        raise RoleMatchAnalysisNotFoundError(analysis_id)
    after = get_analysis(db, other_analysis_id)
    if after is None:
        raise RoleMatchAnalysisNotFoundError(other_analysis_id)
    return compare_analyses(db, before, after)


@router.post(
    "/analyze/role-match/{analysis_id}/reanalyze",
    response_model=RoleMatchAnalysisResponse,
)
def reanalyze_role_match(
    analysis_id: int,
    body: RoleMatchReanalyzeRequest,
    db: Session = Depends(get_db),
):
    parent = get_analysis(db, analysis_id)
    if parent is None:
        raise RoleMatchAnalysisNotFoundError(analysis_id)
    profile_id = body.profile_id or parent.profile_id
    if profile_id is None:
        raise RoleMatchProfileRequiredError()
    profile = get_profile_or_404(profile_id, db)
    provider, api_key = require_llm_config(db)
    child = analyze_role_match(
        db=db,
        profile=profile_to_schema(profile),
        job_description=body.job_description or parent.job_description,
        provider=provider,
        api_key=api_key,
        application_id=(
            body.application_id
            if body.application_id is not None
            else parent.application_id
        ),
        parent_analysis_id=parent.id,
        analysis_date=date.today(),
    )
    return serialize_analysis(db, child)


@router.post(
    "/analyze/role-match/{analysis_id}/overrides",
    response_model=RoleMatchAnalysisResponse,
)
def apply_role_match_overrides(
    analysis_id: int,
    body: RoleMatchOverridesRequest,
    db: Session = Depends(get_db),
):
    child = apply_user_overrides(db, analysis_id, body.overrides)
    return serialize_analysis(db, child)


@router.delete(
    "/analyze/role-match/{analysis_id}/overrides/{override_id}",
    response_model=RoleMatchAnalysisResponse,
)
def restore_role_match_override(
    analysis_id: int,
    override_id: int,
    db: Session = Depends(get_db),
):
    restored = restore_user_override(db, analysis_id, override_id)
    return serialize_analysis(db, restored)
