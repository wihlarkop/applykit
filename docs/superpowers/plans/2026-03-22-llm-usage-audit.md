# LLM Usage Audit Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Track and audit all LLM API calls, capturing token usage, cost, latency, and operation metadata using litellm's built-in response metadata.

**Architecture:** 
- New `LlmUsageLog` database model to store audit records
- Wrapper layer in `llm.py` to capture usage metadata from litellm responses
- Async database writes via threading to avoid blocking LLM calls
- REST API endpoint to retrieve usage stats

**Tech Stack:** Python/litellm, SQLite/PostgreSQL, Alembic, Bun for FE

---

## File Structure

```
backend/
├── app/
│   ├── models.py              # Add LlmUsageLog model
│   ├── schemas.py             # Add LlmUsageEntry, LlmUsageListResponse, LlmUsageFilters
│   ├── services/
│   │   └── llm.py            # Add operation constants, logging helpers, update signatures
│   └── routes/
│       └── usage.py           # NEW: API endpoint for usage stats
├── migrations/
│   └── versions/
│       └── xxxxx_add_llm_usage_log.py  # NEW: migration
```

---

## Task 1: Add LlmUsageLog Model

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/migrations/versions/xxxxx_add_llm_usage_log.py`
- Modify: `backend/app/schemas.py`

- [ ] **Step 1: Add LlmUsageLog model to models.py**

Add after the existing model definitions:

```python
class LlmUsageLog(Base):
    __tablename__ = "llm_usage_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    
    # Operation context
    operation = Column(String, nullable=False)
    
    # LLM details
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    
    # Token usage (from litellm response.usage)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    
    # Cost (from litellm response._response_ms field)
    cost = Column(Float, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    
    # Context
    profile_id = Column(Integer, ForeignKey("profile.id", ondelete="SET NULL"), nullable=True)
    
    # Outcome
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
```

- [ ] **Step 2: Generate and run migration**

Run: `cd backend && uv run alembic revision --autogenerate -m "add_llm_usage_log"`
Run: `cd backend && uv run alembic upgrade head`
Expected: Migration created and applied successfully

- [ ] **Step 3: Add schemas to schemas.py**

```python
class LlmUsageEntry(BaseModel):
    id: int
    created_at: datetime
    operation: str
    provider: str
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    cost: float | None
    latency_ms: int | None
    profile_id: int | None
    success: bool
    error_message: str | None
    
    model_config = {"from_attributes": True}


class LlmUsageListResponse(BaseModel):
    items: list[LlmUsageEntry]
    total: int
    total_tokens: int
    total_cost: float


class LlmUsageFilters(BaseModel):
    operation: str | None = None
    profile_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    success: bool | None = None
```

---

## Task 2: Create Usage Logging Service

**Files:**
- Modify: `backend/app/services/llm.py`

- [ ] **Step 1: Add imports and operation constants**

Add at top of file:

```python
import threading
import time
from datetime import datetime, UTC
from sqlalchemy.orm import Session

from app.models import LlmUsageLog
from app.database import get_db_context
```

Add constants:

```python
# Operation types for LLM usage tracking
OPERATION_CV_GENERATION = "cv_generation"
OPERATION_COVER_LETTER = "cover_letter"
OPERATION_FIT_ANALYSIS = "fit_analysis"
OPERATION_JOB_PARSING = "job_parsing"
OPERATION_SUMMARY_GENERATION = "summary_generation"
OPERATION_BULLETS_GENERATION = "bullets_generation"
```

- [ ] **Step 2: Add logging helpers at end of file**

```python
def _log_usage_thread(
    operation: str,
    provider: str,
    model: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    total_tokens: int | None,
    cost: float | None,
    latency_ms: int,
    profile_id: int | None,
    success: bool,
    error_message: str | None,
) -> None:
    """Thread-safe database write for LLM usage logging."""
    db_gen = get_db_context()
    db = next(db_gen)
    try:
        log = LlmUsageLog(
            operation=operation,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            latency_ms=latency_ms,
            profile_id=profile_id,
            success=success,
            error_message=error_message,
        )
        db.add(log)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
```

- [ ] **Step 3: Update call_llm signature and implementation**

New signature:

```python
def call_llm(
    prompt: str,
    system: str | None = None,
    timeout: int = 30,
    provider: str = "",
    api_key: str = "",
    operation: str | None = None,
    profile_id: int | None = None,
) -> str:
```

After successful litellm response, add:

```python
# Extract usage metadata from litellm response
usage = getattr(response, "usage", None)
prompt_tokens = usage.prompt_tokens if usage else None
completion_tokens = usage.completion_tokens if usage else None
total_tokens = usage.total_tokens if usage else None
cost = getattr(response, "cost", None)
latency_ms = getattr(response, "_response_ms", None)

# Log usage asynchronously
if operation:
    threading.Thread(
        target=_log_usage_thread,
        args=(
            operation,
            provider,
            model,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            cost,
            latency_ms or 0,
            profile_id,
            True,
            None,
        ),
    ).start()
```

In the except block, add:

```python
# Log failed call
if operation:
    threading.Thread(
        target=_log_usage_thread,
        args=(
            operation,
            provider,
            model,
            None,
            None,
            None,
            None,
            int((time.time() - start_time) * 1000),
            profile_id,
            False,
            str(e),
        ),
    ).start()
```

- [ ] **Step 4: Update stream_llm signature and add completion logging**

New signature:

```python
async def stream_llm(
    prompt: str,
    system: str | None = None,
    provider: str = "",
    api_key: str = "",
    operation: str | None = None,
    profile_id: int | None = None,
) -> AsyncGenerator[str, None]:
```

Track usage by collecting chunks, and at the end add:

```python
# After stream completes, get usage from litellm
# Note: For streaming, litellm returns usage on the final chunk
if operation and hasattr(response, "usage"):
    usage = response.usage
    # Log usage
    threading.Thread(
        target=_log_usage_thread,
        args=(
            operation,
            provider,
            model,
            usage.prompt_tokens if usage else None,
            usage.completion_tokens if usage else None,
            usage.total_tokens if usage else None,
            getattr(response, "cost", None),
            getattr(response, "_response_ms", 0) or 0,
            profile_id,
            True,
            None,
        ),
    ).start()
```

---

## Task 3: Update All LLM Callers

**Files:**
- Modify: `backend/app/routes/generate.py`
- Modify: `backend/app/services/parse_job_description.py`
- Modify: `backend/app/services/fit_analysis.py`

- [ ] **Step 1: Update generate.py**

Find all `call_llm()` 
