from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace

from sqlalchemy.orm import Session

from app.llm.catalog import provider_from_model, provider_requires_api_key
from app.models import AiReadinessTest
from app.readiness.schemas import (
    AiReadiness,
    AiReadinessStatus,
    ConnectionFailureCategory,
)
from app.services.provider_credential_vault import get_active_provider_credential
from app.services.settings import (
    get_provider_base_url,
    get_setting,
    normalize_provider_base_url,
)


@dataclass(frozen=True)
class ActiveAiConfiguration:
    provider_id: str
    model_id: str
    base_url: str | None
    credential_id: int | None
    credential_version: int | None


def _normalized_config(config: ActiveAiConfiguration) -> ActiveAiConfiguration:
    base_url = normalize_provider_base_url(config.provider_id, config.base_url)
    return replace(config, base_url=base_url)


def configuration_fingerprint(config: ActiveAiConfiguration) -> str:
    normalized = _normalized_config(config)
    payload = json.dumps(asdict(normalized), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def resolve_active_ai_configuration(
    db: Session,
) -> ActiveAiConfiguration | None:
    model_id = (get_setting(db, "llm_provider") or "").strip()
    if not model_id:
        return None

    provider_id = provider_from_model(model_id)
    if not provider_id:
        return None

    base_url = get_provider_base_url(db, provider_id)
    credential_id: int | None = None
    credential_version: int | None = None
    if provider_requires_api_key(provider_id):
        credential = get_active_provider_credential(db, provider_id)
        if credential is None:
            return None
        credential_id = credential.id
        credential_version = credential.version

    return ActiveAiConfiguration(
        provider_id=provider_id,
        model_id=model_id,
        base_url=base_url,
        credential_id=credential_id,
        credential_version=credential_version,
    )


def evaluate_ai_readiness(db: Session) -> AiReadiness:
    config = resolve_active_ai_configuration(db)
    if config is None:
        return AiReadiness(
            ready=False,
            status=AiReadinessStatus.NOT_CONFIGURED,
            message="Configure an AI provider and model to enable AI features.",
        )

    fingerprint = configuration_fingerprint(config)
    row = db.query(AiReadinessTest).filter_by(id=1).first()
    if row is None:
        return AiReadiness(
            ready=False,
            status=AiReadinessStatus.RETEST_REQUIRED,
            provider=config.provider_id,
            model=config.model_id,
            message=(
                "Test this connection once to confirm the current configuration."
            ),
            configuration_fingerprint=fingerprint,
        )

    if row.configuration_fingerprint != fingerprint:
        return AiReadiness(
            ready=False,
            status=AiReadinessStatus.CONFIGURATION_CHANGED,
            provider=config.provider_id,
            model=config.model_id,
            tested_at=row.tested_at,
            message=(
                "The AI configuration changed. Test the active connection again."
            ),
            configuration_fingerprint=fingerprint,
        )

    if row.status == "success":
        return AiReadiness(
            ready=True,
            status=AiReadinessStatus.READY,
            provider=config.provider_id,
            model=config.model_id,
            tested_at=row.tested_at,
            message=row.public_message,
            configuration_fingerprint=fingerprint,
        )

    try:
        category = ConnectionFailureCategory(
            row.failure_category or ConnectionFailureCategory.UNKNOWN_FAILURE.value
        )
    except ValueError:
        category = ConnectionFailureCategory.UNKNOWN_FAILURE
    return AiReadiness(
        ready=False,
        status=AiReadinessStatus(category.value),
        provider=config.provider_id,
        model=config.model_id,
        tested_at=row.tested_at,
        failure_category=category,
        message=row.public_message,
        configuration_fingerprint=fingerprint,
    )


def record_active_connection_result(
    db: Session,
    *,
    tested_config: ActiveAiConfiguration,
    ok: bool,
    public_message: str,
    failure_category: ConnectionFailureCategory | None = None,
) -> AiReadinessTest | None:
    active = resolve_active_ai_configuration(db)
    if active is None:
        return None

    tested_fingerprint = configuration_fingerprint(tested_config)
    active_fingerprint = configuration_fingerprint(active)
    if tested_fingerprint != active_fingerprint:
        return None

    row = db.query(AiReadinessTest).filter_by(id=1).first()
    if row is None:
        row = AiReadinessTest(id=1)
        db.add(row)

    row.provider_id = active.provider_id
    row.model_id = active.model_id
    row.base_url = active.base_url
    row.credential_id = active.credential_id
    row.credential_version = active.credential_version
    row.configuration_fingerprint = active_fingerprint
    row.status = "success" if ok else "failed"
    row.failure_category = None if ok else (
        failure_category or ConnectionFailureCategory.UNKNOWN_FAILURE
    ).value
    row.public_message = public_message
    db.commit()
    db.refresh(row)
    return row
