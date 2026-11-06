"""Seed the database with sample data for development.

Usage:
    python -m app.seed           # Add seed data
    python -m app.seed --reset   # Drop all tables, recreate, and seed
"""
import argparse
from datetime import date, datetime, timedelta, timezone

from app.database import Base, SessionLocal, engine
from app.models import (
    Application,
    ApplicationStatus,
    Company,
    Note,
    StatusHistory,
    WorkMode,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _days_ago(n: int) -> datetime:
    """Return a UTC datetime `n` days in the past."""
    return _utcnow() - timedelta(days=n)


def _date_ago(n: int) -> date:
    """Return a date `n` days in the past."""
    return (_utcnow() - timedelta(days=n)).date()


def seed():
    """Insert sample companies, applications, notes and status history."""
    db = SessionLocal()
    try:
        # ---------- Companies ----------
        companies_data = [
            {"name": "Google", "website": "https://google.com", "location": "Mountain View, CA", "industry": "Technology"},
            {"name": "Meta", "website": "https://meta.com", "location": "Menlo Park, CA", "industry": "Technology"},
            {"name": "Stripe", "website": "https://stripe.com", "location": "San Francisco, CA", "industry": "Fintech"},
            {"name": "Spotify", "website": "https://spotify.com", "location": "Stockholm, Sweden", "industry": "Music / Tech"},
            {"name": "Notion", "website": "https://notion.so", "location": "San Francisco, CA", "industry": "Productivity"},
            {"name": "Airbnb", "website": "https://airbnb.com", "location": "San Francisco, CA", "industry": "Travel / Tech"},
            {"name": "Shopify", "website": "https://shopify.com", "location": "Ottawa, Canada", "industry": "E-commerce"},
            {"name": "Figma", "website": "https://figma.com", "location": "San Francisco, CA", "industry": "Design / Tech"},
        ]
        companies = []
        for data in companies_data:
            company = Company(**data)
            db.add(company)
            db.flush()
            companies.append(company)

        # ---------- Applications ----------
        # Spread across all 4 stages, some with old last_activity_at for follow-up testing
        apps_data = [
            # Applied – recent (no follow-up)
            {"company": companies[0], "job_title": "Senior Frontend Engineer", "status": ApplicationStatus.APPLIED,
             "applied_date": _date_ago(3), "location": "Mountain View, CA", "work_mode": WorkMode.HYBRID,
             "source": "LinkedIn", "last_activity_at": _days_ago(3), "job_url": "https://careers.google.com/jobs/1"},
            {"company": companies[4], "job_title": "Full Stack Developer", "status": ApplicationStatus.APPLIED,
             "applied_date": _date_ago(2), "location": "San Francisco, CA", "work_mode": WorkMode.REMOTE,
             "source": "Company site", "last_activity_at": _days_ago(2), "job_url": "https://notion.so/careers/1"},
            {"company": companies[6], "job_title": "React Developer", "status": ApplicationStatus.APPLIED,
             "applied_date": _date_ago(1), "location": "Ottawa, Canada", "work_mode": WorkMode.REMOTE,
             "source": "Referral", "last_activity_at": _days_ago(1)},

            # Applied – stale (should trigger follow-up)
            {"company": companies[1], "job_title": "Product Engineer", "status": ApplicationStatus.APPLIED,
             "applied_date": _date_ago(10), "location": "Menlo Park, CA", "work_mode": WorkMode.ONSITE,
             "source": "LinkedIn", "last_activity_at": _days_ago(10), "job_url": "https://metacareers.com/1"},
            {"company": companies[2], "job_title": "Backend Engineer", "status": ApplicationStatus.APPLIED,
             "applied_date": _date_ago(8), "location": "San Francisco, CA", "work_mode": WorkMode.HYBRID,
             "source": "Company site", "last_activity_at": _days_ago(8), "job_url": "https://stripe.com/jobs/1"},
            {"company": companies[3], "job_title": "Data Engineer", "status": ApplicationStatus.APPLIED,
             "applied_date": _date_ago(15), "location": "Stockholm, Sweden", "work_mode": WorkMode.REMOTE,
             "source": "LinkedIn", "last_activity_at": _days_ago(15)},
            {"company": companies[7], "job_title": "Design Engineer", "status": ApplicationStatus.APPLIED,
             "applied_date": _date_ago(9), "location": "San Francisco, CA", "work_mode": WorkMode.HYBRID,
             "source": "Referral", "last_activity_at": _days_ago(9), "job_url": "https://figma.com/careers/1"},

            # Interview
            {"company": companies[0], "job_title": "Software Engineer L4", "status": ApplicationStatus.INTERVIEW,
             "applied_date": _date_ago(20), "location": "New York, NY", "work_mode": WorkMode.ONSITE,
             "source": "Referral", "last_activity_at": _days_ago(2), "job_url": "https://careers.google.com/jobs/2",
             "salary_min": 150000, "salary_max": 200000},
            {"company": companies[5], "job_title": "Frontend Engineer", "status": ApplicationStatus.INTERVIEW,
             "applied_date": _date_ago(18), "location": "San Francisco, CA", "work_mode": WorkMode.HYBRID,
             "source": "LinkedIn", "last_activity_at": _days_ago(3), "job_url": "https://airbnb.com/careers/1",
             "salary_min": 140000, "salary_max": 180000},
            {"company": companies[2], "job_title": "Platform Engineer", "status": ApplicationStatus.INTERVIEW,
             "applied_date": _date_ago(14), "location": "San Francisco, CA", "work_mode": WorkMode.REMOTE,
             "source": "Company site", "last_activity_at": _days_ago(1)},
            {"company": companies[4], "job_title": "Senior Engineer", "status": ApplicationStatus.INTERVIEW,
             "applied_date": _date_ago(12), "location": "Remote", "work_mode": WorkMode.REMOTE,
             "source": "LinkedIn", "last_activity_at": _days_ago(4), "salary_min": 160000, "salary_max": 210000},
            {"company": companies[7], "job_title": "Staff Engineer", "status": ApplicationStatus.INTERVIEW,
             "applied_date": _date_ago(25), "location": "San Francisco, CA", "work_mode": WorkMode.HYBRID,
             "source": "Referral", "last_activity_at": _days_ago(5), "salary_min": 200000, "salary_max": 280000},
            {"company": companies[1], "job_title": "ML Engineer", "status": ApplicationStatus.INTERVIEW,
             "applied_date": _date_ago(16), "location": "Menlo Park, CA", "work_mode": WorkMode.ONSITE,
             "source": "LinkedIn", "last_activity_at": _days_ago(6)},

            # Offer
            {"company": companies[3], "job_title": "Senior Backend Engineer", "status": ApplicationStatus.OFFER,
             "applied_date": _date_ago(30), "location": "Stockholm, Sweden", "work_mode": WorkMode.REMOTE,
             "source": "LinkedIn", "last_activity_at": _days_ago(1), "salary_min": 130000, "salary_max": 160000},
            {"company": companies[5], "job_title": "Senior Full Stack Engineer", "status": ApplicationStatus.OFFER,
             "applied_date": _date_ago(28), "location": "San Francisco, CA", "work_mode": WorkMode.HYBRID,
             "source": "Referral", "last_activity_at": _days_ago(2), "salary_min": 170000, "salary_max": 220000},
            {"company": companies[6], "job_title": "Tech Lead", "status": ApplicationStatus.OFFER,
             "applied_date": _date_ago(22), "location": "Ottawa, Canada", "work_mode": WorkMode.REMOTE,
             "source": "Company site", "last_activity_at": _days_ago(3), "salary_min": 180000, "salary_max": 240000},

            # Rejected
            {"company": companies[0], "job_title": "Junior Developer", "status": ApplicationStatus.REJECTED,
             "applied_date": _date_ago(35), "location": "Mountain View, CA", "work_mode": WorkMode.ONSITE,
             "source": "Company site", "last_activity_at": _days_ago(20)},
            {"company": companies[1], "job_title": "iOS Engineer", "status": ApplicationStatus.REJECTED,
             "applied_date": _date_ago(40), "location": "Menlo Park, CA", "work_mode": WorkMode.HYBRID,
             "source": "LinkedIn", "last_activity_at": _days_ago(25)},
            {"company": companies[2], "job_title": "DevOps Engineer", "status": ApplicationStatus.REJECTED,
             "applied_date": _date_ago(32), "location": "San Francisco, CA", "work_mode": WorkMode.REMOTE,
             "source": "Other", "last_activity_at": _days_ago(22)},
            {"company": companies[5], "job_title": "Backend Developer", "status": ApplicationStatus.REJECTED,
             "applied_date": _date_ago(45), "location": "San Francisco, CA", "work_mode": WorkMode.ONSITE,
             "source": "LinkedIn", "last_activity_at": _days_ago(30)},
            {"company": companies[6], "job_title": "QA Engineer", "status": ApplicationStatus.REJECTED,
             "applied_date": _date_ago(38), "location": "Ottawa, Canada", "work_mode": WorkMode.HYBRID,
             "source": "Other", "last_activity_at": _days_ago(28)},
            {"company": companies[3], "job_title": "Frontend Developer", "status": ApplicationStatus.REJECTED,
             "applied_date": _date_ago(50), "location": "Stockholm, Sweden", "work_mode": WorkMode.REMOTE,
             "source": "LinkedIn", "last_activity_at": _days_ago(35)},

            # A few more Applied for variety
            {"company": companies[5], "job_title": "Growth Engineer", "status": ApplicationStatus.APPLIED,
             "applied_date": _date_ago(5), "location": "San Francisco, CA", "work_mode": WorkMode.HYBRID,
             "source": "LinkedIn", "last_activity_at": _days_ago(5)},
            {"company": companies[7], "job_title": "Creative Technologist", "status": ApplicationStatus.APPLIED,
             "applied_date": _date_ago(4), "location": "Remote", "work_mode": WorkMode.REMOTE,
             "source": "Company site", "last_activity_at": _days_ago(4), "job_url": "https://figma.com/careers/2"},
        ]

        applications = []
        for data in apps_data:
            company = data.pop("company")
            app = Application(company_id=company.id, **data)
            db.add(app)
            db.flush()
            applications.append(app)

            # Add initial status history entry
            history = StatusHistory(
                application_id=app.id,
                from_status=None,
                to_status=app.status.value,
                changed_at=app.created_at,
            )
            db.add(history)

        # Add extra status history for interview/offer/rejected apps
        # (they went through Applied first)
        for app in applications:
            if app.status != ApplicationStatus.APPLIED:
                # Went from applied to current status
                db.add(StatusHistory(
                    application_id=app.id,
                    from_status="applied",
                    to_status=app.status.value,
                    changed_at=app.last_activity_at,
                ))

        # ---------- Notes ----------
        notes_data = [
            {"app_idx": 0, "content": "Submitted through Google Careers portal. Heard back within a day!", "days_ago": 2},
            {"app_idx": 3, "content": "Applied via LinkedIn Easy Apply. No response yet.", "days_ago": 10},
            {"app_idx": 7, "content": "Phone screen went well. They want to schedule an onsite.", "days_ago": 5},
            {"app_idx": 7, "content": "Onsite scheduled for next Tuesday. 4 rounds.", "days_ago": 2},
            {"app_idx": 8, "content": "Recruiter reached out to schedule a technical interview.", "days_ago": 10},
            {"app_idx": 8, "content": "Technical round completed. Felt good about the system design question.", "days_ago": 3},
            {"app_idx": 9, "content": "First round was a take-home assignment. Submitted it.", "days_ago": 7},
            {"app_idx": 13, "content": "Received offer letter! Competitive salary and equity.", "days_ago": 1},
            {"app_idx": 14, "content": "Got the offer. Great team culture during interviews.", "days_ago": 2},
            {"app_idx": 14, "content": "Negotiating salary. They are open to discussion.", "days_ago": 1},
            {"app_idx": 16, "content": "Rejected after the final round. Got good feedback though.", "days_ago": 20},
            {"app_idx": 11, "content": "Panel interview went really well. Waiting for decision.", "days_ago": 5},
        ]
        for nd in notes_data:
            note = Note(
                application_id=applications[nd["app_idx"]].id,
                content=nd["content"],
                created_at=_days_ago(nd["days_ago"]),
                updated_at=_days_ago(nd["days_ago"]),
            )
            db.add(note)

        db.commit()
        print(f"✅ Seeded {len(companies)} companies, {len(applications)} applications, {len(notes_data)} notes")

    except Exception as e:
        db.rollback()
        print(f"❌ Seed failed: {e}")
        raise
    finally:
        db.close()


def reset():
    """Drop all tables, recreate them, and seed."""
    print("🗑️  Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("📦 Creating all tables...")
    Base.metadata.create_all(bind=engine)
    seed()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the job tracker database")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables before seeding")
    args = parser.parse_args()

    if args.reset:
        reset()
    else:
        # Ensure tables exist
        Base.metadata.create_all(bind=engine)
        seed()
