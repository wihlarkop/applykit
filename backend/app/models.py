from datetime import UTC, datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Profile(Base):
    __tablename__ = "profile"

    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String, nullable=False, default="Default")
    color = Column(String, nullable=False, default="#6366f1")
    icon = Column(String, nullable=False, default="💼")
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)
    github = Column(String, nullable=True)
    portfolio = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    work_experience = Column(Text, default="[]")
    education = Column(Text, default="[]")
    skills = Column(Text, default="[]")
    projects = Column(Text, default="[]")
    certifications = Column(Text, default="[]")
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class GeneratedCV(Base):
    __tablename__ = "generated_cv"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    enhanced = Column(Integer, default=0)  # 0 = false, 1 = true (SQLite bool)
    profile_snapshot = Column(Text, nullable=False)  # JSON string of ProfileData
    profile_id = Column(
        Integer, ForeignKey("profile.id", ondelete="SET NULL"), nullable=True
    )
    application_id = Column(
        Integer, ForeignKey("application.id", ondelete="SET NULL"), nullable=True
    )
    application_status = Column(String, nullable=True, default=None)


class GeneratedCoverLetter(Base):
    __tablename__ = "generated_cover_letter"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    company_name = Column(String, nullable=True)
    job_description = Column(Text, nullable=False)
    extra_context = Column(Text, nullable=True)
    cover_letter_text = Column(Text, nullable=False)
    profile_id = Column(
        Integer, ForeignKey("profile.id", ondelete="SET NULL"), nullable=True
    )
    application_id = Column(
        Integer, ForeignKey("application.id", ondelete="SET NULL"), nullable=True
    )
    job_url = Column(String, nullable=True)
    match_score = Column(Integer, nullable=True)
    fit_analysis = Column(Text, nullable=True)  # JSON string of FitAnalysisResponse
    tone = Column(String, nullable=False, default="professional")
    application_status = Column(String, nullable=True, default=None)


class Application(Base):
    __tablename__ = "application"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String, nullable=False)
    role_title = Column(String, nullable=False, default="")
    status = Column(String, nullable=False, default="applied")
    job_url = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    applied_date = Column(Date, nullable=True)
    profile_id = Column(
        Integer, ForeignKey("profile.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class AppSetting(Base):
    __tablename__ = "app_setting"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
