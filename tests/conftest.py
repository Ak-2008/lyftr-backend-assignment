"""
Pytest configuration and fixtures
"""
import pytest
import os

# Ensure test environment variables are set
os.environ.setdefault("WEBHOOK_SECRET", "testsecret")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_app.db")
os.environ.setdefault("LOG_LEVEL", "INFO")

# Import after setting env vars
from app.storage import init_db
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Initialize the test database before running tests"""
    # Initialize database schema
    init_db()
    yield
    # Cleanup after all tests (optional)
    import os
    if os.path.exists("./test_app.db"):
        os.remove("./test_app.db")

@pytest.fixture(scope="module")
def client():
    """Create a test client"""
    return TestClient(app)