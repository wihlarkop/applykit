import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.routes.applications import create_application, update_application
from app.schemas import CreateApplicationRequest, UpdateApplicationRequest


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_create_application_persists_salary_range_excitement_and_dates():
    db = _make_session()
    try:
        req = CreateApplicationRequest(
            company_name="Acme",
            min_salary=120_000,
            max_salary=150_000,
            excitement=4,
            date_posted="2026-01-01",
            deadline="2026-02-01",
            follow_up="2026-01-15",
        )
        entry = create_application(req, db)

        assert entry.min_salary == 120_000
        assert entry.max_salary == 150_000
        assert entry.excitement == 4
        assert str(entry.date_posted) == "2026-01-01"
        assert str(entry.deadline) == "2026-02-01"
        assert str(entry.follow_up) == "2026-01-15"
    finally:
        db.close()


def test_update_application_patches_new_fields_independently():
    db = _make_session()
    try:
        created = create_application(CreateApplicationRequest(company_name="Acme"), db)

        updated = update_application(
            created.id, UpdateApplicationRequest(excitement=5), db
        )
        assert updated.excitement == 5
        assert updated.min_salary is None

        updated = update_application(
            created.id,
            UpdateApplicationRequest(min_salary=100_000, max_salary=130_000),
            db,
        )
        assert updated.min_salary == 100_000
        assert updated.max_salary == 130_000
        assert updated.excitement == 5  # untouched by the second patch
    finally:
        db.close()


@pytest.mark.parametrize("excitement", [0, 6, -1])
def test_excitement_rejects_out_of_range_values(excitement):
    with pytest.raises(ValidationError):
        CreateApplicationRequest(company_name="Acme", excitement=excitement)
