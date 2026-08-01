import asyncio
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.exceptions import RateLimitError
from app.models import Base
from app.services import llm as llm_service
from app.services.credential_crypto import CredentialCipher
from app.services.provider_credential_rotation import (
    CredentialStrategy,
    update_credential_policy,
)
from app.services.provider_credential_vault import create_provider_credential


class FakeRateLimitError(Exception):
    status_code = 429
    retry_after = 12


class FakeAuthenticationError(Exception):
    status_code = 401


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _cipher() -> CredentialCipher:
    return CredentialCipher(Fernet.generate_key().decode())


def _response(text: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=None,
        cost=None,
        _response_ms=1,
    )


def _chunk(text: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=text))],
        usage=None,
    )


def _configure(db, cipher, strategy=CredentialStrategy.FAILOVER):
    create_provider_credential(
        db,
        provider_id="openai",
        label="Primary",
        secret="sk-primary",
        cipher=cipher,
        activate=True,
    )
    create_provider_credential(
        db,
        provider_id="openai",
        label="Backup",
        secret="sk-backup",
        cipher=cipher,
        activate=False,
    )
    update_credential_policy(
        db,
        "openai",
        strategy=strategy,
        max_attempts=2,
    )


def test_call_llm_fails_over_to_backup_credential(monkeypatch):
    db = _make_session()
    cipher = _cipher()
    _configure(db, cipher)
    attempted: list[str] = []

    def completion(**kwargs):
        attempted.append(kwargs["api_key"])
        if kwargs["api_key"] == "sk-primary":
            raise FakeRateLimitError("retry in 12s")
        return _response("backup worked")

    monkeypatch.setattr(llm_service.litellm, "completion", completion)
    try:
        result = llm_service.call_llm(
            "hello",
            provider="openai/gpt-5-mini",
            api_key="sk-primary",
            credential_db=db,
            credential_cipher=cipher,
        )
    finally:
        db.close()

    assert result == "backup worked"
    assert attempted == ["sk-primary", "sk-backup"]


def test_round_robin_is_applied_by_normal_llm_calls(monkeypatch):
    db = _make_session()
    cipher = _cipher()
    _configure(db, cipher, strategy=CredentialStrategy.ROUND_ROBIN)
    selected: list[str] = []

    def completion(**kwargs):
        selected.append(kwargs["api_key"])
        return _response("ok")

    monkeypatch.setattr(llm_service.litellm, "completion", completion)
    try:
        for _ in range(3):
            llm_service.call_llm(
                "hello",
                provider="openai/gpt-5-mini",
                api_key="sk-primary",
                credential_db=db,
                credential_cipher=cipher,
            )
    finally:
        db.close()

    assert selected == ["sk-primary", "sk-backup", "sk-primary"]


def test_streaming_can_fail_over_before_any_content_is_emitted(monkeypatch):
    db = _make_session()
    cipher = _cipher()
    _configure(db, cipher)
    attempted: list[str] = []

    class SuccessfulStream:
        def __aiter__(self):
            self.sent = False
            return self

        async def __anext__(self):
            if self.sent:
                raise StopAsyncIteration
            self.sent = True
            return _chunk("hello")

    async def acompletion(**kwargs):
        attempted.append(kwargs["api_key"])
        if kwargs["api_key"] == "sk-primary":
            raise FakeRateLimitError("retry in 12s")
        return SuccessfulStream()

    monkeypatch.setattr(llm_service.litellm, "acompletion", acompletion)

    async def collect():
        return [
            chunk
            async for chunk in llm_service.stream_llm(
                "hello",
                provider="openai/gpt-5-mini",
                api_key="sk-primary",
                credential_db=db,
                credential_cipher=cipher,
            )
        ]

    try:
        chunks = asyncio.run(collect())
    finally:
        db.close()

    assert chunks == ["hello"]
    assert attempted == ["sk-primary", "sk-backup"]


def test_streaming_never_retries_after_content_was_emitted(monkeypatch):
    db = _make_session()
    cipher = _cipher()
    _configure(db, cipher)
    attempted: list[str] = []

    class PartialStream:
        def __aiter__(self):
            self.index = 0
            return self

        async def __anext__(self):
            self.index += 1
            if self.index == 1:
                return _chunk("partial")
            raise FakeRateLimitError("retry in 12s")

    async def acompletion(**kwargs):
        attempted.append(kwargs["api_key"])
        return PartialStream()

    monkeypatch.setattr(llm_service.litellm, "acompletion", acompletion)

    async def collect():
        chunks = []
        async for chunk in llm_service.stream_llm(
            "hello",
            provider="openai/gpt-5-mini",
            api_key="sk-primary",
            credential_db=db,
            credential_cipher=cipher,
        ):
            chunks.append(chunk)
        return chunks

    try:
        with pytest.raises(RateLimitError):
            asyncio.run(collect())
    finally:
        db.close()

    assert attempted == ["sk-primary"]


def test_all_rate_limited_credentials_surface_safe_rate_limit_error(monkeypatch):
    db = _make_session()
    cipher = _cipher()
    _configure(db, cipher)

    def completion(**_kwargs):
        raise FakeRateLimitError("secret=sk-primary retry in 12s")

    monkeypatch.setattr(llm_service.litellm, "completion", completion)
    try:
        with pytest.raises(RateLimitError) as exc_info:
            llm_service.call_llm(
                "hello",
                provider="openai/gpt-5-mini",
                api_key="sk-primary",
                credential_db=db,
                credential_cipher=cipher,
            )
    finally:
        db.close()

    assert exc_info.value.retry_after == 12
    assert "sk-primary" not in exc_info.value.message
