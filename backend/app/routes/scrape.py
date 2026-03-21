from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions.llm import APIKeyNotConfiguredError, LLMCallError
from app.schemas import (
    ParseJobDescriptionRequest,
    ParseJobDescriptionResponse,
    ScrapeAnalyzeRequest,
    ScrapeAnalyzeResponse,
    ScrapeJobRequest,
    ScrapeJobResponse,
)
from app.services.parse_job_description import parse_job_description
from app.services.scraper import scrape_job_url
from app.services.settings import get_llm_config

router = APIRouter()


@router.post("/scrape/job", response_model=ScrapeJobResponse)
async def scrape_job(body: ScrapeJobRequest):
    try:
        result = await scrape_job_url(body.url)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={"detail": str(e), "code": "SCRAPE_VALUE_ERROR"},
        ) from e
    except Exception:
        raise HTTPException(
            status_code=422,
            detail={
                "detail": "Could not extract job posting. Please paste the text manually.",
                "code": "SCRAPE_FAILED",
            },
        ) from None
    return ScrapeJobResponse(
        job_description=result.job_description,
        company_name=result.company_name,
        role_title=result.role_title,
        location=result.location,
        salary=result.salary,
        source=result.source,
    )


@router.post("/scrape/parse", response_model=ParseJobDescriptionResponse)
def parse_job_description_endpoint(
    body: ParseJobDescriptionRequest, db: Session = Depends(get_db)
):
    provider, api_key = get_llm_config(db)
    if not provider or not api_key:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "LLM not configured. Set provider and API key in Settings.",
                "code": "API_KEY_NOT_CONFIGURED",
            },
        )
    try:
        return parse_job_description(body.text, provider, api_key)
    except APIKeyNotConfiguredError as e:
        raise HTTPException(
            status_code=400,
            detail={"detail": str(e), "code": "API_KEY_NOT_CONFIGURED"},
        )
    except LLMCallError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "detail": f"Failed to parse job description: {e}",
                "code": "LLM_CALL_FAILED",
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={
                "detail": f"Failed to parse job description: {e}",
                "code": "PARSE_FAILED",
            },
        )


@router.post("/scrape/analyze", response_model=ScrapeAnalyzeResponse)
async def scrape_analyze(body: ScrapeAnalyzeRequest, db: Session = Depends(get_db)):
    if not body.url and not body.text:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "Either url or text must be provided",
                "code": "INVALID_REQUEST",
            },
        )

    provider, api_key = get_llm_config(db)
    if not provider or not api_key:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "LLM not configured. Set provider and API key in Settings.",
                "code": "API_KEY_NOT_CONFIGURED",
            },
        )

    job_description = ""
    source = "jina"

    try:
        if body.url:
            scraped = await scrape_job_url(body.url)
            job_description = scraped.job_description
            source = scraped.source
            parsed = parse_job_description(job_description, provider, api_key)
        else:
            job_description = body.text
            parsed = parse_job_description(job_description, provider, api_key)

        return ScrapeAnalyzeResponse(
            company_name=parsed.company_name,
            role_title=parsed.role_title,
            location=parsed.location,
            salary=parsed.salary,
            job_description=job_description,
            source=source,
        )
    except APIKeyNotConfiguredError as e:
        raise HTTPException(
            status_code=400,
            detail={"detail": str(e), "code": "API_KEY_NOT_CONFIGURED"},
        )
    except LLMCallError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "detail": f"Failed to parse job description: {e}",
                "code": "LLM_CALL_FAILED",
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={"detail": str(e), "code": "SCRAPE_VALUE_ERROR"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={"detail": f"Failed to analyze job: {e}", "code": "ANALYZE_FAILED"},
        )
