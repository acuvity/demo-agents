"""Database engine, session factory, and dependency helpers."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base  # pylint: disable=invalid-name

from app.core.config import settings

engine = create_engine(settings.SQLALCHEMY_DATABASE_URI or "")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)  # pylint: disable=invalid-name

Base = declarative_base()


# Dependency to get DB session
def get_db():
    """Yield a database session and ensure it is closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
