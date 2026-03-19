from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import RateLimitError
from app.exceptions.llm import APIKeyNotConfiguredError, LLMCallError
from app.models import Profile
from app.schemas import FitAnalysisRequest, FitAnalysisResponse
from app.services.fit_analysis import analyze_fit
from app.services.settings import get_llm_config
from app.utils import format_profile_for_llm, profile_to_schema

router = APIRouter()


@router.post("/analyze/fit", response_model=FitAnalysisResponse)
def analyze_fit_endpoint(body: FitAnalysisRequest, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter_by(id=body.profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Profile not found", "code": "PROFILE_NOT_FOUND"},
        )

    provider, api_key = get_llm_config(db)
    profile_data = profile_to_schema(profile)
    profile_json = format_profile_for_llm(profile_data)

    try:
        return analyze_fit(profile_json, body.job_description, provider, api_key)
    except APIKeyNotConfiguredError as e:
        raise HTTPException(
            status_code=400,
            detail={"detail": str(e), "code": "API_KEY_NOT_CONFIGURED"},
        )
    except RateLimitError as e:
        raise HTTPException(
            status_code=429,
            detail={
                "detail": str(e),
                "code": "RATE_LIMIT_EXCEEDED",
                "retry_after": e.details.get("retry_after"),
            },
        )
    except LLMCallError as e:
        raise HTTPException(
            status_code=502,
            detail={"detail": str(e), "code": "LLM_CALL_FAILED"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={
                "detail": f"Fit analysis failed: {e}",
                "code": "FIT_ANALYSIS_FAILED",
            },
        )
