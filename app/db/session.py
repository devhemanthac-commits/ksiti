"""
SQLAlchemy Session Factory
==========================
Creates the engine and provides a dependency-injectable session generator
for FastAPI route handlers.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import DATABASE_URL

# Handle SQLite conditionally
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )
else:
    # Optimised for scale and performance: higher connection pool size and recycling
    engine = create_engine(
        DATABASE_URL, 
        pool_pre_ping=True, 
        pool_size=20, 
        max_overflow=50,
        pool_recycle=1800,  # Recycle connections every 30 mins to avoid staleness
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session, auto-closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
