from pathlib import Path

from cryptography.fernet import Fernet
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from app.database import configure_sqlite_security
from app.models import Base
from app.services.credential_crypto import CredentialCipher
from app.services.provider_credential_vault import (
    clear_provider_credentials,
    create_provider_credential,
    migrate_legacy_provider_credentials,
    replace_provider_credential_secret,
)
from app.services.settings import set_setting


def _database_bytes(database_path: Path) -> bytes:
    payload = bytearray(database_path.read_bytes())
    for suffix in ("-wal", "-journal"):
        sidecar = Path(f"{database_path}{suffix}")
        if sidecar.exists():
            payload.extend(sidecar.read_bytes())
    return bytes(payload)


def _file_session(tmp_path: Path):
    database_path = tmp_path / "applykit.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )
    event.listen(engine, "connect", configure_sqlite_security)
    Base.metadata.create_all(engine)
    return database_path, engine, sessionmaker(bind=engine)


def test_sqlite_connections_enable_secure_delete(tmp_path: Path) -> None:
    _, engine, _ = _file_session(tmp_path)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("PRAGMA secure_delete")).scalar() == 1
    finally:
        engine.dispose()


def test_save_replace_migrate_and_disconnect_leave_no_plaintext_canary(
    tmp_path: Path,
) -> None:
    old_secret = "applykit-secret-canary-old-41d2"
    new_secret = "applykit-secret-canary-new-8c63"
    legacy_secret = "applykit-secret-canary-legacy-94aa"
    database_path, engine, factory = _file_session(tmp_path)
    cipher = CredentialCipher(Fernet.generate_key())

    try:
        with factory() as db:
            credential = create_provider_credential(
                db,
                provider_id="openai",
                label="Primary",
                secret=old_secret,
                cipher=cipher,
            )
            replace_provider_credential_secret(
                db,
                "openai",
                credential.id,
                new_secret,
                cipher=cipher,
            )
            clear_provider_credentials(db, "openai")

            set_setting(db, "api_key_gemini", legacy_secret)
            assert migrate_legacy_provider_credentials(db, cipher=cipher) == 1
            clear_provider_credentials(db, "gemini")
    finally:
        engine.dispose()

    database_payload = _database_bytes(database_path)
    assert old_secret.encode() not in database_payload
    assert new_secret.encode() not in database_payload
    assert legacy_secret.encode() not in database_payload
