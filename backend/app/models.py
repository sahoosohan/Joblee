"""SQLAlchemy ORM models matching the PRD data model."""
import enum
from datetime import date, datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------- Enums ----------

class ApplicationStatus(str, enum.Enum):
    """The four stages an application can be in."""
    APPLIED = "applied"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"


class WorkMode(str, enum.Enum):
    """Where the job is performed."""
    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"


# ---------- Helpers ----------

def _utcnow() -> datetime:
    """Return the current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


def _today() -> date:
    """Return today's date in UTC."""
    return datetime.now(timezone.utc).date()


# ---------- Models ----------

class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(collation="NOCASE"), nullable=False, unique=True)
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    industry: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, server_default=func.now()
    )

    # Relationships
    applications: Mapped[list["Application"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Company id={self.id} name={self.name!r}>"


class User(Base):
    """The single account that owns this local tracker instance."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320, collation="NOCASE"), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    sessions: Mapped[list["AuthSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AuthSession(Base):
    """Revocable bearer session; only a hash of the token is stored."""
    __tablename__ = "auth_sessions"
    __table_args__ = (
        Index("idx_auth_sessions_token", "token_hash", unique=True),
        Index("idx_auth_sessions_expiry", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    user: Mapped["User"] = relationship(back_populates="sessions")


class GoogleIdentity(Base):
    """Google account bound to the single local tracker account."""
    __tablename__ = "google_identities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    user: Mapped["User"] = relationship()


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint("length(job_title) BETWEEN 1 AND 120", name="ck_title_len"),
        CheckConstraint(
            "status IN ('applied','interview','offer','rejected')",
            name="ck_status_valid",
        ),
        CheckConstraint(
            "work_mode IN ('onsite','hybrid','remote') OR work_mode IS NULL",
            name="ck_work_mode_valid",
        ),
        CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max",
            name="ck_salary_range",
        ),
        Index("idx_apps_status", "status"),
        Index("idx_apps_company", "company_id"),
        Index("idx_apps_activity", "last_activity_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id"), nullable=False
    )
    job_title: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=ApplicationStatus.APPLIED,
    )
    applied_date: Mapped[date] = mapped_column(Date, nullable=False)
    job_url: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    work_mode: Mapped[WorkMode | None] = mapped_column(
        Enum(WorkMode, values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow
    )
    snoozed_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # Relationships
    company: Mapped["Company"] = relationship(back_populates="applications")
    notes: Mapped[list["Note"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    history: Mapped[list["StatusHistory"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Application id={self.id} title={self.job_title!r} status={self.status}>"


class Note(Base):
    __tablename__ = "notes"
    __table_args__ = (
        CheckConstraint(
            "length(content) BETWEEN 1 AND 2000", name="ck_note_content_len"
        ),
        Index("idx_notes_app", "application_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # Relationships
    application: Mapped["Application"] = relationship(back_populates="notes")

    def __repr__(self) -> str:
        return f"<Note id={self.id} app_id={self.application_id}>"


class StatusHistory(Base):
    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String, nullable=True)
    to_status: Mapped[str] = mapped_column(String, nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow
    )

    # Relationships
    application: Mapped["Application"] = relationship(back_populates="history")

    def __repr__(self) -> str:
        return (
            f"<StatusHistory id={self.id} "
            f"{self.from_status}->{self.to_status}>"
        )
