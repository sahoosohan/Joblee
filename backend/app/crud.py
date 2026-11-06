"""CRUD operations for all models."""
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, case, text, and_, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.config import FOLLOW_UP_DAYS
from app.models import Application, ApplicationStatus, Company, Note, StatusHistory, WorkMode


def _utcnow() -> datetime:
    # SQLite returns DateTime columns without tzinfo; keep CRUD comparisons in
    # naive UTC so persisted values and thresholds use the same representation.
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ==================== Companies ====================

def get_companies(db: Session, q: Optional[str] = None) -> list[dict]:
    """List companies with their application counts."""
    query = (
        db.query(
            Company,
            func.count(Application.id).label("application_count"),
        )
        .outerjoin(Application, Application.company_id == Company.id)
        .group_by(Company.id)
    )
    if q:
        query = query.filter(Company.name.ilike(f"%{q}%"))
    query = query.order_by(Company.name)
    results = query.all()
    return [
        {
            "company": company,
            "application_count": count,
        }
        for company, count in results
    ]


def get_company(db: Session, company_id: int) -> Optional[Company]:
    """Get a single company by ID."""
    return db.query(Company).filter(Company.id == company_id).first()


def get_company_by_name(db: Session, name: str) -> Optional[Company]:
    """Get a company by name (case-insensitive)."""
    return db.query(Company).filter(func.lower(Company.name) == name.lower()).first()


def create_company(db: Session, name: str, website: Optional[str] = None,
                   location: Optional[str] = None, industry: Optional[str] = None) -> Company:
    """Create a new company."""
    company = Company(name=name, website=website, location=location, industry=industry)
    db.add(company)
    db.flush()
    return company


def update_company(db: Session, company: Company, data: dict) -> Company:
    """Update a company's fields."""
    for key, value in data.items():
        setattr(company, key, value)
    db.flush()
    return company


def delete_company(db: Session, company: Company) -> None:
    """Delete a company (fails if it has applications)."""
    db.delete(company)
    db.flush()


def company_has_applications(db: Session, company_id: int) -> bool:
    """Check if a company has any applications."""
    return db.query(Application).filter(Application.company_id == company_id).first() is not None


# ==================== Applications ====================

def _is_follow_up_due(app: Application) -> bool:
    """Check if an application needs follow-up (Python-side for enrichment)."""
    if app.status != ApplicationStatus.APPLIED:
        return False
    threshold = _utcnow() - timedelta(days=FOLLOW_UP_DAYS)
    if app.last_activity_at > threshold:
        return False
    if app.snoozed_until is not None and app.snoozed_until > _utcnow().date():
        return False
    return True


def get_applications(
    db: Session,
    q: Optional[str] = None,
    statuses: Optional[list[str]] = None,
    work_mode: Optional[str] = None,
    source: Optional[str] = None,
    needs_follow_up: bool = False,
) -> list[dict]:
    """List applications with company data using a JOIN.
    
    Returns dicts with application, company info, note count and follow-up status.
    """
    # Build the query with a JOIN to companies
    note_count_subq = (
        db.query(func.count(Note.id))
        .filter(Note.application_id == Application.id)
        .correlate(Application)
        .scalar_subquery()
    )

    query = (
        db.query(
            Application,
            Company.name.label("company_name"),
            Company.website.label("company_website"),
            Company.industry.label("company_industry"),
            note_count_subq.label("note_count"),
        )
        .join(Company, Company.id == Application.company_id)
    )

    # Filters
    if q:
        search = f"%{q}%"
        query = query.filter(
            or_(
                Application.job_title.ilike(search),
                Company.name.ilike(search),
                Application.location.ilike(search),
            )
        )

    if statuses:
        query = query.filter(Application.status.in_(statuses))

    if work_mode:
        query = query.filter(Application.work_mode == work_mode)

    if source:
        query = query.filter(Application.source == source)

    if needs_follow_up:
        threshold = _utcnow() - timedelta(days=FOLLOW_UP_DAYS)
        query = query.filter(
            Application.status == ApplicationStatus.APPLIED.value,
            Application.last_activity_at <= threshold,
            or_(
                Application.snoozed_until.is_(None),
                Application.snoozed_until <= _utcnow().date(),
            ),
        )

    query = query.order_by(Application.updated_at.desc())
    results = query.all()

    apps = []
    for app, company_name, company_website, company_industry, note_count in results:
        apps.append({
            "application": app,
            "company_name": company_name,
            "company_website": company_website,
            "company_industry": company_industry,
            "note_count": note_count or 0,
            "needs_follow_up": _is_follow_up_due(app),
        })
    return apps


def get_application(db: Session, app_id: int) -> Optional[Application]:
    """Get an application with its company, notes and history eagerly loaded."""
    return (
        db.query(Application)
        .options(
            joinedload(Application.company),
            selectinload(Application.notes),
            selectinload(Application.history),
        )
        .filter(Application.id == app_id)
        .first()
    )


def create_application(db: Session, data: dict, company_id: int) -> Application:
    """Create a new application and record the initial status history."""
    now = _utcnow()
    app = Application(
        company_id=company_id,
        job_title=data["job_title"],
        status=data.get("status", "applied"),
        applied_date=data["applied_date"],
        job_url=data.get("job_url"),
        location=data.get("location"),
        work_mode=data.get("work_mode"),
        salary_min=data.get("salary_min"),
        salary_max=data.get("salary_max"),
        source=data.get("source"),
        last_activity_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(app)
    db.flush()

    # Record initial status
    history = StatusHistory(
        application_id=app.id,
        from_status=None,
        to_status=app.status.value if hasattr(app.status, 'value') else app.status,
        changed_at=now,
    )
    db.add(history)
    db.flush()

    return app


def update_application(db: Session, app: Application, data: dict) -> Application:
    """Update an application's fields."""
    now = _utcnow()
    for key, value in data.items():
        setattr(app, key, value)
    app.updated_at = now
    db.flush()
    return app


def update_application_status(db: Session, app: Application, new_status: str) -> Application:
    """Change an application's status and record the history."""
    now = _utcnow()
    old_status = app.status.value if hasattr(app.status, 'value') else app.status

    app.status = new_status
    app.last_activity_at = now
    app.updated_at = now

    # Clear snooze when leaving applied
    if old_status == "applied" and new_status != "applied":
        app.snoozed_until = None

    # Record history
    history = StatusHistory(
        application_id=app.id,
        from_status=old_status,
        to_status=new_status,
        changed_at=now,
    )
    db.add(history)
    db.flush()

    return app


def delete_application(db: Session, app: Application) -> None:
    """Delete an application (cascades to notes and history)."""
    db.delete(app)
    db.flush()


# ==================== Notes ====================

def get_notes(db: Session, app_id: int) -> list[Note]:
    """Get all notes for an application, newest first."""
    return (
        db.query(Note)
        .filter(Note.application_id == app_id)
        .order_by(Note.created_at.desc())
        .all()
    )


def get_note(db: Session, note_id: int) -> Optional[Note]:
    """Get a single note by ID."""
    return db.query(Note).filter(Note.id == note_id).first()


def create_note(db: Session, app_id: int, content: str) -> Note:
    """Create a note and update the application's last_activity_at."""
    now = _utcnow()
    note = Note(application_id=app_id, content=content, created_at=now, updated_at=now)
    db.add(note)

    # Update parent application's activity timestamp
    app = db.query(Application).filter(Application.id == app_id).first()
    if app:
        app.last_activity_at = now
        app.updated_at = now

    db.flush()
    return note


def update_note(db: Session, note: Note, content: str) -> Note:
    """Update a note's content."""
    note.content = content
    note.updated_at = _utcnow()
    db.flush()
    return note


def delete_note(db: Session, note: Note) -> None:
    """Delete a note."""
    db.delete(note)
    db.flush()


# ==================== Follow-ups ====================

def get_follow_ups(db: Session) -> list[dict]:
    """Get applications needing follow-up."""
    threshold = _utcnow() - timedelta(days=FOLLOW_UP_DAYS)
    today = _utcnow().date()

    results = (
        db.query(
            Application.id,
            Application.job_title,
            Company.name.label("company_name"),
            Company.id.label("company_id"),
            Application.applied_date,
            Application.location,
            Application.last_activity_at,
        )
        .join(Company, Company.id == Application.company_id)
        .filter(
            Application.status == ApplicationStatus.APPLIED.value,
            Application.last_activity_at <= threshold,
            or_(
                Application.snoozed_until.is_(None),
                Application.snoozed_until <= today,
            ),
        )
        .order_by(Application.last_activity_at.asc())
        .all()
    )

    follow_ups = []
    for row in results:
        days_waiting = (_utcnow() - row.last_activity_at).days
        follow_ups.append({
            "id": row.id,
            "job_title": row.job_title,
            "company_name": row.company_name,
            "company_id": row.company_id,
            "days_waiting": days_waiting,
            "applied_date": row.applied_date,
            "location": row.location,
        })
    return follow_ups


def mark_follow_up_done(db: Session, app: Application) -> Note:
    """Mark a follow-up as done by adding an auto note and resetting the timer."""
    return create_note(db, app.id, "Followed up")


def snooze_follow_up(db: Session, app: Application, days: int) -> Application:
    """Snooze a follow-up for the given number of days."""
    app.snoozed_until = (_utcnow() + timedelta(days=days)).date()
    app.updated_at = _utcnow()
    db.flush()
    return app


# ==================== Stats ====================

def get_stats(
    db: Session,
    q: Optional[str] = None,
    statuses: Optional[list[str]] = None,
    work_mode: Optional[str] = None,
    source: Optional[str] = None,
    needs_follow_up: bool = False,
) -> dict:
    """Get aggregate stats using COUNT/CASE queries."""
    query = (
        db.query(
            func.count(Application.id).label("total"),
            func.sum(case((Application.status == "applied", 1), else_=0)).label("applied"),
            func.sum(case((Application.status == "interview", 1), else_=0)).label("interviews"),
            func.sum(case((Application.status == "offer", 1), else_=0)).label("offers"),
            func.sum(case((Application.status == "rejected", 1), else_=0)).label("rejected"),
        )
        .join(Company, Company.id == Application.company_id)
    )

    # Apply the same filters as the list endpoint
    if q:
        search = f"%{q}%"
        query = query.filter(
            or_(
                Application.job_title.ilike(search),
                Company.name.ilike(search),
                Application.location.ilike(search),
            )
        )

    if statuses:
        query = query.filter(Application.status.in_(statuses))

    if work_mode:
        query = query.filter(Application.work_mode == work_mode)

    if source:
        query = query.filter(Application.source == source)

    threshold = _utcnow() - timedelta(days=FOLLOW_UP_DAYS)
    today = _utcnow().date()
    follow_up_filter = and_(
        Application.status == ApplicationStatus.APPLIED.value,
        Application.last_activity_at <= threshold,
        or_(Application.snoozed_until.is_(None), Application.snoozed_until <= today),
    )
    if needs_follow_up:
        query = query.filter(follow_up_filter)

    row = query.one()
    total = row.total or 0
    applied = row.applied or 0
    interviews = row.interviews or 0
    offers = row.offers or 0
    rejected = row.rejected or 0

    # Response rate: (interview + offer + rejected) / total
    response_rate = 0.0
    if total > 0:
        response_rate = round((interviews + offers + rejected) / total, 4)

    # Follow-ups due count
    follow_ups_query = db.query(func.count(Application.id)).join(
        Company, Company.id == Application.company_id
    ).filter(follow_up_filter)
    if q:
        search = f"%{q}%"
        follow_ups_query = follow_ups_query.filter(or_(
            Application.job_title.ilike(search), Company.name.ilike(search),
            Application.location.ilike(search),
        ))
    if statuses:
        follow_ups_query = follow_ups_query.filter(Application.status.in_(statuses))
    if work_mode:
        follow_ups_query = follow_ups_query.filter(Application.work_mode == work_mode)
    if source:
        follow_ups_query = follow_ups_query.filter(Application.source == source)
    follow_ups_due = follow_ups_query.scalar() or 0

    return {
        "total": total,
        "applied": applied,
        "interviews": interviews,
        "offers": offers,
        "rejected": rejected,
        "response_rate": response_rate,
        "follow_ups_due": follow_ups_due,
    }
