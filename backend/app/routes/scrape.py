from fastapi import APIRouter, HTTPException

from app.schemas import ScrapeJobRequest, ScrapeJobResponse
from app.services.scraper import scrape_job_url

router = APIRouter()


@router.post("/scrape/job", response_model=ScrapeJobResponse)
async def scrape_job(body: ScrapeJobRequest):
    try:
        result = await scrape_job_url(body.url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail="Could not extract job posting. Please paste the text manually.",
        )
    return ScrapeJobResponse(
        job_description=result.job_description,
        company_name=result.company_name,
        source=result.source,
    )
