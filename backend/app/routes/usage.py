from datetime import date, datetime, timedelta, UTC
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LlmUsageLog
from app.schemas import LlmUsageEntry, LlmUsageListResponse, LlmUsageFilters

router = APIRouter()


@router.get("/usage", response_model=LlmUsageListResponse)
def get_llm_usage(
    operation: str | None = None,
    profile_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    success: bool | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Get LLM usage logs with optional filters."""
    query = db.query(LlmUsageLog)

    if operation:
        query = query.filter(LlmUsageLog.operation == operation)
    if profile_id:
        query = query.filter(LlmUsageLog.profile_id == profile_id)
    if date_from:
        query = query.filter(LlmUsageLog.created_at >= date_from)
    if date_to:
        query = query.filter(LlmUsageLog.created_at <= date_to)
    if success is not None:
        query = query.filter(LlmUsageLog.success == success)

    total = query.count()

    totals = (
        db.query(
            func.sum(LlmUsageLog.total_tokens).label("total_tokens"),
            func.sum(LlmUsageLog.cost).label("total_cost"),
        )
        .filter(LlmUsageLog.id.in_(query.limit(10000).with_entities(LlmUsageLog.id)))
        .first()
    )

    items = (
        query.order_by(LlmUsageLog.created_at.desc()).offset(offset).limit(limit).all()
    )

    return LlmUsageListResponse(
        items=[LlmUsageEntry.model_validate(item) for item in items],
        total=total,
        total_tokens=totals.total_tokens or 0,
        total_cost=float(totals.total_cost or 0.0),
    )


@router.get("/usage/stats")
def get_llm_usage_stats(db: Session = Depends(get_db)):
    """Get aggregated LLM usage statistics."""
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    today_stats = (
        db.query(
            func.count(LlmUsageLog.id).label("count"),
            func.sum(LlmUsageLog.total_tokens).label("tokens"),
            func.sum(LlmUsageLog.cost).label("cost"),
        )
        .filter(LlmUsageLog.created_at >= today_start)
        .first()
    )

    week_stats = (
        db.query(
            func.count(LlmUsageLog.id).label("count"),
            func.sum(LlmUsageLog.total_tokens).label("tokens"),
            func.sum(LlmUsageLog.cost).label("cost"),
        )
        .filter(LlmUsageLog.created_at >= week_start)
        .first()
    )

    by_operation = (
        db.query(
            LlmUsageLog.operation,
            func.count(LlmUsageLog.id).label("count"),
            func.sum(LlmUsageLog.total_tokens).label("tokens"),
            func.sum(LlmUsageLog.cost).label("cost"),
        )
        .group_by(LlmUsageLog.operation)
        .all()
    )

    return {
        "today": {
            "calls": today_stats.count or 0,
            "tokens": today_stats.tokens or 0,
            "cost": float(today_stats.cost or 0.0),
        },
        "this_week": {
            "calls": week_stats.count or 0,
            "tokens": week_stats.tokens or 0,
            "cost": float(week_stats.cost or 0.0),
        },
        "by_operation": [
            {
                "operation": op,
                "count": count,
                "tokens": tokens or 0,
                "cost": float(cost or 0.0),
            }
            for op, count, tokens, cost in by_operation
        ],
    }
