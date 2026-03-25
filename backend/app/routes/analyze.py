from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_profile_or_404, require_llm_config
from app.schemas import FitAnalysisRequest, FitAnalysisResponse
from app.services.fit_analysis import analyze_fit
from app.utils import format_profile_for_llm, profile_to_schema

router = APIRouter()


@router.post("/analyze/fit", response_model=FitAnalysisResponse)
def analyze_fit_endpoint(body: FitAnalysisRequest, db: Session = Depends(get_db)):
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
