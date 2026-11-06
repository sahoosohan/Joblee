"""Database engine, session and dependency."""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL

# For SQLite, check_same_thread=False is needed for FastAPI's threaded model
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine_options = {"connect_args": connect_args, "echo": False}
if DATABASE_URL.startswith("postgresql+"):
    # Discard dead connections after idle periods and respect the free database limit.
    engine_options.update(pool_pre_ping=True, pool_recycle=300, pool_size=1, max_overflow=0)

engine = create_engine(DATABASE_URL, **engine_options)

# Enable foreign keys for every SQLite connection
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _connection_record):
    """Turn on foreign key enforcement for SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
