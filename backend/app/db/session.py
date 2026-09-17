from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

# Create SQLAlchemy engine with connection pooling
# pool_pre_ping checks connections before handing them to requests, preventing stale connections
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

# SessionLocal is a factory for new database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session per request
    and ensures the session is cleanly closed after request execution.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
