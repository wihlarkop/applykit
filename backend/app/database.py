from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_settings = get_settings()


def configure_sqlite_security(dbapi_connection, _connection_record) -> None:
    """Enable SQLite deletion hardening and declared foreign-key actions."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA secure_delete=ON")
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


engine = create_engine(
    _settings.database_url, connect_args={"check_same_thread": False}
)
if _settings.database_url.startswith("sqlite"):
    event.listen(engine, "connect", configure_sqlite_security)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_context():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
