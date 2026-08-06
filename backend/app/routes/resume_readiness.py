from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.resume_readiness.domain import (
    AnalysisMode,
    AnalysisStatus,
    OverallResult,
    ReadinessResult,
)
from app.resume_readiness.normalization import normalize_text
from app.resume_readiness.pipeline import AnalysisInput, analyze_generated_cv
from app.resume_readiness.presenter import present_analysis
from app.resume_readiness.repository import (
    create_analysis,
    get_analysis,
    get_generated_cv,
    get_latest_for_generated_cv,
    list_for_generated_cv,
)
from app.resume_readiness.schemas import (
    ResumeReadinessAnalyzeRequest,
    ResumeReadinessListResponse,
    ResumeReadinessResponse,
)
from app.role_match.repository import (
    get_analysis as get_role_match_analysis,
    serialize_analysis as serialize_role_match_analysis,
)

router = APIRouter()


def _failed_result(mode: AnalysisMode, code: str) -> ReadinessResult:
    overall = OverallResult.failed(code)
    return ReadinessResult(
        mode=mode,
        status=AnalysisStatus.FAILED,
        overall=overall,
        parseability=None,
        quality=None,
        tailoring=None,
        rule_results=(),
        extraction=None,
        coverage=None,
        failure_code=code,
    )


def _load_role_match(
    db: Session,
    *,
    role_match_analysis_id: int | None,
    generated_cv_profile_id: int | None,
    requested_job_description: str | None,
):
    if role_match_analysis_id is None:
        return None, requested_job_description, None

    analysis = get_role_match_analysis(db, role_match_analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Role Evidence Match analysis not found.")

    job_description = requested_job_description or analysis.job_description
    if (
        requested_job_description
        and normalize_text(requested_job_description)
        != normalize_text(analysis.job_description)
    ):
        raise HTTPException(
            status_code=422,
            detail="Role Evidence Match was created from a different job description.",
        )

    if generated_cv_profile_id is None:
        return None, job_description, None

    if analysis.profile_id is None or generated_cv_profile_id != analysis.profile_id:
        raise HTTPException(
            status_code=422,
            detail="Role Evidence Match belongs to a different career profile.",
        )

    return (
        serialize_role_match_analysis(db, analysis),
        job_description,
        analysis.id,
    )


@router.post(
    "/resume-readiness/analyses",
    response_model=ResumeReadinessResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_resume_readiness_analysis(
    request: ResumeReadinessAnalyzeRequest,
    db: Session = Depends(get_db),
):
    generated_cv = get_generated_cv(db, request.generated_cv_id)
    if generated_cv is None:
        raise HTTPException(status_code=404, detail="Generated resume not found.")

    role_match, job_description, effective_role_match_id = _load_role_match(
        db,
        role_match_analysis_id=request.role_match_analysis_id,
        generated_cv_profile_id=generated_cv.profile_id,
        requested_job_description=request.job_description,
    )
    mode = (
        AnalysisMode.JOB_SPECIFIC
        if job_description and job_description.strip()
        else AnalysisMode.GENERAL
    )

    try:
        profile_snapshot = json.loads(generated_cv.profile_snapshot)
        if not isinstance(profile_snapshot, dict):
            raise ValueError("profile snapshot is not an object")
    except (TypeError, ValueError, json.JSONDecodeError):
        result = _failed_result(mode, "INVALID_PROFILE_SNAPSHOT")
    else:
        result = analyze_generated_cv(
            AnalysisInput(
                generated_cv_id=generated_cv.id,
                profile_snapshot=profile_snapshot,
                job_description=job_description,
                role_match=role_match,
            )
        )

    saved = create_analysis(
        db,
        result=result,
        generated_cv=generated_cv,
        job_description_snapshot=job_description,
        role_match_analysis_id=effective_role_match_id,
    )
    return present_analysis(saved)


@router.get(
    "/resume-readiness/analyses/{analysis_id}",
    response_model=ResumeReadinessResponse,
)
def read_resume_readiness_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
):
    analysis = get_analysis(db, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Resume Readiness analysis not found.")
    return present_analysis(analysis)


@router.get(
    "/generated-cvs/{generated_cv_id}/resume-readiness/latest",
    response_model=ResumeReadinessResponse,
)
def read_latest_resume_readiness(
    generated_cv_id: int,
    db: Session = Depends(get_db),
):
    if get_generated_cv(db, generated_cv_id) is None:
        raise HTTPException(status_code=404, detail="Generated resume not found.")
    analysis = get_latest_for_generated_cv(db, generated_cv_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Resume has not been analyzed yet.")
    return present_analysis(analysis)


@router.get(
    "/generated-cvs/{generated_cv_id}/resume-readiness",
    response_model=ResumeReadinessListResponse,
)
def read_resume_readiness_history(
    generated_cv_id: int,
    db: Session = Depends(get_db),
):
    if get_generated_cv(db, generated_cv_id) is None:
        raise HTTPException(status_code=404, detail="Generated resume not found.")
    items = [present_analysis(item) for item in list_for_generated_cv(db, generated_cv_id)]
    return ResumeReadinessListResponse(items=items, total=len(items))
