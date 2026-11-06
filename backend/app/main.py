"""FastAPI routes for the Job Application Tracker."""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Response, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import crud, models
from app.config import CORS_ORIGINS, GOOGLE_CLIENT_ID
from app.database import Base, engine, get_db
from app.security import create_bearer_token, token_digest
from app.schemas import (
    AuthGoogleCredential, AuthStatusOut, AuthTokenOut, AuthUserOut,
    ApplicationCreate, ApplicationDetail, ApplicationOut, ApplicationUpdate,
    CompanyCreate, CompanyOut, CompanyUpdate, CompanyWithCount, FollowUpOut,
    NoteCreate, NoteOut, NoteUpdate, SnoozeRequest, StatsOut, StatusUpdate,
)

Base.metadata.create_all(bind=engine)

bearer = HTTPBearer(auto_error=False)
PUBLIC_AUTH_PATHS = {"/api/v1/health", "/api/v1/auth/status", "/api/v1/auth/google"}
SESSION_TTL = timedelta(days=30)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _authenticate(credentials: HTTPAuthorizationCredentials | None, db: Session):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    session = db.query(models.AuthSession).filter_by(token_hash=token_digest(credentials.credentials)).first()
    if not session or session.revoked_at or session.expires_at <= _utcnow():
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.", headers={"WWW-Authenticate": "Bearer"})
    user = db.get(models.User, session.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.", headers={"WWW-Authenticate": "Bearer"})
    return user, session


def require_auth(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    if request.url.path not in PUBLIC_AUTH_PATHS and request.url.path.startswith("/api/v1/"):
        _authenticate(credentials, db)


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    return _authenticate(credentials, db)[0]


def _issue_token(db: Session, user: models.User) -> dict:
    now = _utcnow()
    token = create_bearer_token()
    session = models.AuthSession(user_id=user.id, token_hash=token_digest(token), created_at=now, expires_at=now + SESSION_TTL)
    db.add(session)
    _commit(db)
    return {"access_token": token, "expires_at": session.expires_at, "user": user}


app = FastAPI(title="Job Application Tracker", version="1.0.0", docs_url="/docs", redoc_url="/redoc", dependencies=[Depends(require_auth)])
app.add_middleware(
    CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_methods=["*"], allow_headers=["*"],
)


def _application_out(row: dict) -> dict:
    application = row["application"]
    return {
        **{key: getattr(application, key) for key in (
            "id", "company_id", "job_title", "status", "applied_date", "job_url",
            "location", "work_mode", "salary_min", "salary_max", "source",
            "last_activity_at", "snoozed_until", "created_at", "updated_at",
        )},
        "company_name": row["company_name"],
        "company_website": row["company_website"],
        "company_industry": row["company_industry"],
        "note_count": row["note_count"],
        "needs_follow_up": row["needs_follow_up"],
    }


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A record with these details already exists") from exc


def _get_application(db: Session, application_id: int):
    record = crud.get_application(db, application_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return record


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/v1/auth/status", response_model=AuthStatusOut)
def auth_status(db: Session = Depends(get_db)):
    return {"setup_required": db.get(models.User, 1) is None}


@app.post("/api/v1/auth/google", response_model=AuthTokenOut)
def auth_google(payload: AuthGoogleCredential, db: Session = Depends(get_db)):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured. Set GOOGLE_CLIENT_ID and VITE_GOOGLE_CLIENT_ID.")
    try:
        from google.auth.transport.requests import Request as GoogleRequest
        from google.oauth2 import id_token

        claims = id_token.verify_oauth2_token(payload.credential, GoogleRequest(), GOOGLE_CLIENT_ID)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Google credential is invalid or expired") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not verify the Google credential") from exc

    subject = claims.get("sub")
    email = claims.get("email", "").strip().lower()
    if not subject or not email or claims.get("email_verified") is not True:
        raise HTTPException(status_code=401, detail="Google account must have a verified email address")

    identity = db.query(models.GoogleIdentity).filter_by(subject=subject).first()
    user = db.get(models.User, 1)
    if identity:
        if not user or identity.user_id != user.id:
            raise HTTPException(status_code=403, detail="This Google account is not linked to this tracker")
        identity.email = email
    elif user:
        if user.email.lower() != email:
            raise HTTPException(status_code=403, detail="This tracker is already linked to another Google account")
        db.add(models.GoogleIdentity(user_id=user.id, subject=subject, email=email))
    else:
        user = models.User(id=1, email=email, password_hash="")
        db.add(user)
        db.flush()
        db.add(models.GoogleIdentity(user_id=user.id, subject=subject, email=email))
    db.flush()
    return _issue_token(db, user)


@app.get("/api/v1/auth/me", response_model=AuthUserOut)
def auth_me(user: models.User = Depends(current_user)):
    return user


@app.post("/api/v1/auth/logout", status_code=204)
def auth_logout(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    _, session = _authenticate(credentials, db)
    session.revoked_at = _utcnow()
    _commit(db)
    return Response(status_code=204)


@app.get("/api/v1/companies", response_model=list[CompanyWithCount])
def list_companies(q: str | None = None, db: Session = Depends(get_db)):
    return [{**CompanyOut.model_validate(row["company"]).model_dump(), "application_count": row["application_count"]}
            for row in crud.get_companies(db, q)]


@app.post("/api/v1/companies", response_model=CompanyOut, status_code=201)
def add_company(payload: CompanyCreate, db: Session = Depends(get_db)):
    if crud.get_company_by_name(db, payload.name.strip()):
        raise HTTPException(status_code=409, detail="A company with this name already exists")
    company = crud.create_company(db, payload.name.strip(), payload.website, payload.location, payload.industry)
    _commit(db)
    return company


@app.patch("/api/v1/companies/{company_id}", response_model=CompanyOut)
def edit_company(company_id: int, payload: CompanyUpdate, db: Session = Depends(get_db)):
    company = crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        if data["name"] is None:
            raise HTTPException(status_code=422, detail="Company name cannot be blank")
        data["name"] = data["name"].strip()
        other = crud.get_company_by_name(db, data["name"])
        if other and other.id != company_id:
            raise HTTPException(status_code=409, detail="A company with this name already exists")
    crud.update_company(db, company, data)
    _commit(db)
    return company


@app.delete("/api/v1/companies/{company_id}", status_code=204)
def remove_company(company_id: int, db: Session = Depends(get_db)):
    company = crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if crud.company_has_applications(db, company_id):
        raise HTTPException(status_code=409, detail="Company has applications and cannot be deleted")
    crud.delete_company(db, company)
    _commit(db)
    return Response(status_code=204)


@app.get("/api/v1/applications", response_model=list[ApplicationOut])
def list_applications(
    q: str | None = None,
    status: list[str] | None = Query(default=None),
    work_mode: str | None = None,
    source: str | None = None,
    needs_follow_up: bool = False,
    db: Session = Depends(get_db),
):
    statuses = [item.lower() for item in status] if status else None
    valid = {item.value for item in models.ApplicationStatus}
    if statuses and any(item not in valid for item in statuses):
        raise HTTPException(status_code=422, detail="Invalid application status")
    return [_application_out(row) for row in crud.get_applications(db, q, statuses, work_mode, source, needs_follow_up)]


@app.post("/api/v1/applications", response_model=ApplicationDetail, status_code=201)
def add_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"company", "company_id"})
    if payload.company_id is not None:
        company = crud.get_company(db, payload.company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
    else:
        company = crud.get_company_by_name(db, payload.company.name.strip())
        if company is None:
            company = crud.create_company(db, payload.company.name.strip(), payload.company.website,
                                          payload.company.location, payload.company.industry)
    record = crud.create_application(db, data, company.id)
    _commit(db)
    return _detail(db, record.id)


def _detail(db: Session, application_id: int):
    record = _get_application(db, application_id)
    rows = crud.get_applications(db)
    row = next((item for item in rows if item["application"].id == application_id), None)
    return {
        **_application_out(row), "company": record.company,
        "notes": crud.get_notes(db, application_id),
        "history": sorted(record.history, key=lambda item: item.changed_at, reverse=True),
    }


@app.get("/api/v1/applications/{application_id}", response_model=ApplicationDetail)
def get_application(application_id: int, db: Session = Depends(get_db)):
    return _detail(db, application_id)


@app.patch("/api/v1/applications/{application_id}", response_model=ApplicationDetail)
def edit_application(application_id: int, payload: ApplicationUpdate, db: Session = Depends(get_db)):
    record = _get_application(db, application_id)
    data = payload.model_dump(exclude_unset=True)
    if "company_id" in data:
        if data["company_id"] is None:
            raise HTTPException(status_code=422, detail="Company is required")
        if not crud.get_company(db, data["company_id"]):
            raise HTTPException(status_code=404, detail="Company not found")
    salary_min = data.get("salary_min", record.salary_min)
    salary_max = data.get("salary_max", record.salary_max)
    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        raise HTTPException(status_code=422, detail="Minimum salary must be less than or equal to maximum salary")
    crud.update_application(db, record, data)
    _commit(db)
    return _detail(db, application_id)


@app.patch("/api/v1/applications/{application_id}/status", response_model=ApplicationDetail)
def move_application(application_id: int, payload: StatusUpdate, db: Session = Depends(get_db)):
    record = _get_application(db, application_id)
    if record.status.value != payload.status:
        crud.update_application_status(db, record, payload.status)
        _commit(db)
    return _detail(db, application_id)


@app.delete("/api/v1/applications/{application_id}", status_code=204)
def remove_application(application_id: int, db: Session = Depends(get_db)):
    record = _get_application(db, application_id)
    crud.delete_application(db, record)
    _commit(db)
    return Response(status_code=204)


@app.post("/api/v1/applications/{application_id}/notes", response_model=NoteOut, status_code=201)
def add_note(application_id: int, payload: NoteCreate, db: Session = Depends(get_db)):
    _get_application(db, application_id)
    note = crud.create_note(db, application_id, payload.content.strip())
    _commit(db)
    return note


@app.patch("/api/v1/notes/{note_id}", response_model=NoteOut)
def edit_note(note_id: int, payload: NoteUpdate, db: Session = Depends(get_db)):
    note = crud.get_note(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    crud.update_note(db, note, payload.content.strip())
    _commit(db)
    return note


@app.delete("/api/v1/notes/{note_id}", status_code=204)
def remove_note(note_id: int, db: Session = Depends(get_db)):
    note = crud.get_note(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    crud.delete_note(db, note)
    _commit(db)
    return Response(status_code=204)


@app.get("/api/v1/follow-ups", response_model=list[FollowUpOut])
def list_follow_ups(db: Session = Depends(get_db)):
    return crud.get_follow_ups(db)


@app.post("/api/v1/follow-ups/{application_id}/done", response_model=NoteOut)
def follow_up_done(application_id: int, db: Session = Depends(get_db)):
    record = _get_application(db, application_id)
    note = crud.mark_follow_up_done(db, record)
    _commit(db)
    return note


@app.post("/api/v1/follow-ups/{application_id}/snooze", response_model=ApplicationDetail)
def snooze_follow_up(application_id: int, payload: SnoozeRequest, db: Session = Depends(get_db)):
    record = _get_application(db, application_id)
    crud.snooze_follow_up(db, record, payload.days)
    _commit(db)
    return _detail(db, application_id)


@app.get("/api/v1/stats", response_model=StatsOut)
def get_stats(q: str | None = None, status: list[str] | None = Query(default=None),
              work_mode: str | None = None, source: str | None = None,
              needs_follow_up: bool = False,
              db: Session = Depends(get_db)):
    statuses = [item.lower() for item in status] if status else None
    valid = {item.value for item in models.ApplicationStatus}
    if statuses and any(item not in valid for item in statuses):
        raise HTTPException(status_code=422, detail="Invalid application status")
    return crud.get_stats(db, q, statuses, work_mode, source, needs_follow_up)
