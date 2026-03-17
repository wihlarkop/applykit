from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Profile
from app.schemas import FitAnalysisRequest, FitAnalysisResponse
from app.services.fit_analysis import analyze_fit
from app.services.llm import APIKeyNotConfiguredError, LLMCallError
from app.services.settings import get_llm_config
from app.utils import format_profile_for_llm, profile_to_schema

router = APIRouter()


@router.post("/analyze/fit", response_model=FitAnalysisResponse)
def analyze_fit_endpoint(body: FitAnalysisRequest, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter_by(id=body.profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")

    provider, api_key = get_llm_config(db)
    profile_data = profile_to_schema(profile)
    profile_json = format_profile_for_llm(profile_data)

    try:
        return analyze_fit(profile_json, body.job_description, provider, api_key)
    except APIKeyNotConfiguredError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LLMCallError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Fit analysis failed: {e}")
