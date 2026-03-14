"""Pytest fixtures for setting up a test database and FastAPI test client."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.db.database import Base, get_db
from app.main import app

# Use an in-memory SQLite database for testing
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)  # pylint: disable=invalid-name


@pytest.fixture(scope="function")
def db():
    """Provide a fresh database session for each test function."""
    # Create the database
    Base.metadata.create_all(bind=engine)

    # Create a db session
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

    # Drop the database after the test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):  # pylint: disable=redefined-outer-name
    """Provide a FastAPI test client with the test database injected."""
    # Override the get_db dependency
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides = {}
