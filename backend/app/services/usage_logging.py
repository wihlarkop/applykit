import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable

from app.database import SessionLocal
from app.models import LlmUsageLog

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UsageRecord:
    operation: str
    provider: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None
    latency_ms: int = 0
    profile_id: int | None = None
    success: bool = True
    error_message: str | None = None


def split_model_identifier(model_identifier: str) -> tuple[str, str]:
    """Split a LiteLLM identifier into provider family and model name."""
    provider, separator, model = model_identifier.partition("/")
    if separator and provider and model:
        return provider, model
    return "unknown", model_identifier


def _write_usage(record: UsageRecord) -> None:
    with SessionLocal() as db:
        try:
            db.add(
                LlmUsageLog(
                    operation=record.operation,
                    provider=record.provider,
                    model=record.model,
                    prompt_tokens=record.prompt_tokens,
                    completion_tokens=record.completion_tokens,
                    total_tokens=record.total_tokens,
                    cost=record.cost,
                    latency_ms=record.latency_ms,
                    profile_id=record.profile_id,
                    success=record.success,
                    error_message=record.error_message,
                )
            )
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to persist LLM usage record")


class UsageLogDispatcher:
    """Serialize usage writes through a bounded worker pool."""

    def __init__(self, writer: Callable[[UsageRecord], None] = _write_usage):
        self._writer = writer
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="llm-usage",
        )

    def submit(self, record: UsageRecord) -> Future[None]:
        return self._executor.submit(self._writer, record)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True)


_dispatcher: UsageLogDispatcher | None = None
_dispatcher_lock = threading.Lock()


def _get_dispatcher() -> UsageLogDispatcher:
    global _dispatcher
    with _dispatcher_lock:
        if _dispatcher is None:
            _dispatcher = UsageLogDispatcher()
        return _dispatcher


def log_usage_background(
    *,
    operation: str,
    model_identifier: str,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    cost: float | None = None,
    latency_ms: int = 0,
    profile_id: int | None = None,
    success: bool = True,
    error_message: str | None = None,
) -> Future[None]:
    provider, model = split_model_identifier(model_identifier)
    return _get_dispatcher().submit(
        UsageRecord(
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
    )


def stop_usage_logger() -> None:
    """Flush pending usage records and release the worker on shutdown."""
    global _dispatcher
    with _dispatcher_lock:
        dispatcher = _dispatcher
        _dispatcher = None
    if dispatcher is not None:
        dispatcher.shutdown()
