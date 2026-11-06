"""Pydantic v2 schemas for request/response validation."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from urllib.parse import urlparse
import re


def _valid_http_url(value: str, label: str) -> str:
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"{label} must be a valid http(s) URL")
    return value


class AuthGoogleCredential(BaseModel):
    credential: str = Field(..., min_length=20, max_length=8192)


class AuthUserOut(BaseModel):
    id: int
    email: str

    model_config = {"from_attributes": True}


class AuthStatusOut(BaseModel):
    setup_required: bool


class AuthTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: AuthUserOut


# ---------- Company Schemas ----------

class CompanyCreate(BaseModel):
    """Schema for creating a company."""
    name: str = Field(..., min_length=1, max_length=200, description="Company name (unique, case-insensitive)")
    website: Optional[str] = Field(None, description="Company website URL")
    location: Optional[str] = Field(None, max_length=200, description="Company location")
    industry: Optional[str] = Field(None, max_length=100, description="Industry sector")

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Company name cannot be blank")
        return value

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            v = _valid_http_url(v, "Website")
        return v or None


class CompanyUpdate(BaseModel):
    """Schema for updating a company."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    website: Optional[str] = None
    location: Optional[str] = Field(None, max_length=200)
    industry: Optional[str] = Field(None, max_length=100)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Company name cannot be blank")
        return value

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            v = _valid_http_url(v, "Website")
        return v


class CompanyOut(BaseModel):
    """Schema for company in responses."""
    id: int
    name: str
    website: Optional[str] = None
    location: Optional[str] = None
    industry: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CompanyWithCount(CompanyOut):
    """Company with application count for listing."""
    application_count: int = 0


# ---------- Note Schemas ----------

class NoteCreate(BaseModel):
    """Schema for creating a note."""
    content: str = Field(..., min_length=1, max_length=2000, description="Note content")

    @field_validator("content")
    @classmethod
    def trim_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Note content cannot be blank")
        return value


class NoteUpdate(BaseModel):
    """Schema for updating a note."""
    content: str = Field(..., min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def trim_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Note content cannot be blank")
        return value


class NoteOut(BaseModel):
    """Schema for note in responses."""
    id: int
    application_id: int
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------- Status History Schemas ----------

class StatusHistoryOut(BaseModel):
    """Schema for status history entries."""
    id: int
    application_id: int
    from_status: Optional[str] = None
    to_status: str
    changed_at: datetime

    model_config = {"from_attributes": True}


# ---------- Application Schemas ----------

class CompanyInline(BaseModel):
    """Inline company creation when adding an application."""
    name: str = Field(..., min_length=1, max_length=200)
    website: Optional[str] = None
    location: Optional[str] = None
    industry: Optional[str] = None

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Company name cannot be blank")
        return value

    @field_validator("website")
    @classmethod
    def validate_website(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value.strip():
            return _valid_http_url(value, "Website")
        return None


class ApplicationCreate(BaseModel):
    """Schema for creating an application."""
    company_id: Optional[int] = Field(None, description="ID of existing company")
    company: Optional[CompanyInline] = Field(None, description="Create a new company inline")
    job_title: str = Field(..., min_length=1, max_length=120, description="Job title")
    status: str = Field("applied", description="Application status")
    applied_date: date = Field(..., description="Date the application was submitted")
    job_url: Optional[str] = Field(None, description="Job listing URL")
    location: Optional[str] = Field(None, max_length=200)
    work_mode: Optional[str] = Field(None, description="onsite, hybrid, or remote")
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    source: Optional[str] = Field(None, description="Where you found the job")

    @field_validator("job_title")
    @classmethod
    def trim_job_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Job title cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_company_ref(self):
        """Ensure exactly one of company_id or company is provided."""
        if self.company_id is None and self.company is None:
            raise ValueError("Either company_id or company must be provided")
        if self.company_id is not None and self.company is not None:
            raise ValueError("Provide either company_id or company, not both")
        return self

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid = {"applied", "interview", "offer", "rejected"}
        if v.lower() not in valid:
            raise ValueError(f"Status must be one of: {', '.join(sorted(valid))}")
        return v.lower()

    @field_validator("applied_date")
    @classmethod
    def validate_applied_date(cls, v: date) -> date:
        from datetime import timezone, datetime as dt
        today = dt.now(timezone.utc).date()
        if v > today:
            raise ValueError("Applied date cannot be in the future")
        return v

    @field_validator("job_url")
    @classmethod
    def validate_job_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            v = _valid_http_url(v, "Job URL")
        return v or None

    @field_validator("work_mode")
    @classmethod
    def validate_work_mode(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid = {"onsite", "hybrid", "remote"}
            if v.lower() not in valid:
                raise ValueError(f"Work mode must be one of: {', '.join(sorted(valid))}")
            return v.lower()
        return v

    @model_validator(mode="after")
    def validate_salary_range(self):
        """Ensure salary_min <= salary_max when both are provided."""
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min > self.salary_max:
                raise ValueError("Minimum salary must be less than or equal to maximum salary")
        return self


class ApplicationUpdate(BaseModel):
    """Schema for updating application fields."""
    job_title: Optional[str] = Field(None, min_length=1, max_length=120)
    applied_date: Optional[date] = None
    job_url: Optional[str] = None
    location: Optional[str] = Field(None, max_length=200)
    work_mode: Optional[str] = None
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    source: Optional[str] = None
    company_id: Optional[int] = None

    @field_validator("job_title")
    @classmethod
    def trim_job_title(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Job title cannot be blank")
        return value

    @field_validator("applied_date")
    @classmethod
    def validate_applied_date(cls, v: Optional[date]) -> Optional[date]:
        if v is not None:
            from datetime import timezone, datetime as dt
            today = dt.now(timezone.utc).date()
            if v > today:
                raise ValueError("Applied date cannot be in the future")
        return v

    @field_validator("job_url")
    @classmethod
    def validate_job_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            v = _valid_http_url(v, "Job URL")
        return v

    @field_validator("work_mode")
    @classmethod
    def validate_work_mode(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid = {"onsite", "hybrid", "remote"}
            if v.lower() not in valid:
                raise ValueError(f"Work mode must be one of: {', '.join(sorted(valid))}")
            return v.lower()
        return v

    @model_validator(mode="after")
    def validate_salary_range(self):
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min > self.salary_max:
                raise ValueError("Minimum salary must be less than or equal to maximum salary")
        return self


class StatusUpdate(BaseModel):
    """Schema for changing application status."""
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid = {"applied", "interview", "offer", "rejected"}
        if v.lower() not in valid:
            raise ValueError(f"Status must be one of: {', '.join(sorted(valid))}")
        return v.lower()


class ApplicationOut(BaseModel):
    """Schema for application in list responses (with company info)."""
    id: int
    company_id: int
    job_title: str
    status: str
    applied_date: date
    job_url: Optional[str] = None
    location: Optional[str] = None
    work_mode: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    source: Optional[str] = None
    last_activity_at: datetime
    snoozed_until: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    # Joined company data
    company_name: str
    company_website: Optional[str] = None
    company_industry: Optional[str] = None
    # Aggregated
    note_count: int = 0
    needs_follow_up: bool = False


class ApplicationDetail(ApplicationOut):
    """Full application detail with nested company, notes and history."""
    company: CompanyOut
    notes: list[NoteOut] = []
    history: list[StatusHistoryOut] = []


# ---------- Stats Schemas ----------

class StatsOut(BaseModel):
    """Quick stats from SQL COUNT queries."""
    total: int = 0
    applied: int = 0
    interviews: int = 0
    offers: int = 0
    rejected: int = 0
    response_rate: float = 0.0
    follow_ups_due: int = 0


# ---------- Follow-up Schemas ----------

class FollowUpOut(BaseModel):
    """A follow-up reminder item."""
    id: int
    job_title: str
    company_name: str
    company_id: int
    days_waiting: int
    applied_date: date
    location: Optional[str] = None


class SnoozeRequest(BaseModel):
    """Request to snooze a follow-up."""
    days: int = Field(3, ge=1, le=30, description="Number of days to snooze")
