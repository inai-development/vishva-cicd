# tests/conftest.py

import pytest
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to Python path so imports work correctly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture(scope="session")
def test_database_url():
    """Return the test database URL"""
    return "sqlite:///:memory:"

@pytest.fixture(scope="session") 
def test_engine_session():
    """Create a test database engine for the entire test session"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    return engine

@pytest.fixture(scope="function")
def clean_test_engine():
    """Create a fresh test database engine for each test function"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    return engine

# If you want to test with a persistent SQLite file during development
@pytest.fixture(scope="session")
def persistent_test_engine():
    """Create a persistent SQLite test database (useful for debugging)"""
    test_db_path = "test_database.db"
    engine = create_engine(f"sqlite:///{test_db_path}", echo=False)
    
    yield engine
    
    # Cleanup: remove test database file after tests
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

# Global test configuration
def pytest_configure(config):
    """Configure pytest settings"""
    # Add custom markers
    config.addinivalue_line(
        "markers", 
        "database: mark test as requiring database access"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test"
    )

# Set up test environment variables - UPDATED
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables"""
    # Set test environment flag FIRST
    os.environ["TESTING"] = "true"
    
    # Override database URL for tests
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    # Print for debugging
    print(f"✅ Test environment set: TESTING={os.environ.get('TESTING')}")
    print(f"✅ Test database URL: {os.environ.get('DATABASE_URL')}")
    
    yield
    
    # Cleanup environment variables after tests (optional)
    # Uncomment if you want to clean up:
    # if "TESTING" in os.environ:
    #     del os.environ["TESTING"]
    # if "DATABASE_URL" in os.environ:
    #     del os.environ["DATABASE_URL"]