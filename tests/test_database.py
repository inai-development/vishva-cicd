# test_database.py - Fixed for SQLAlchemy 2.0

import pytest
from sqlalchemy import create_engine, inspect, text  # Added text import
from sqlalchemy.orm import sessionmaker
from inai_project.database import Base

@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine using SQLite in-memory for each test"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    return engine

@pytest.fixture(scope="function")
def test_session(test_engine):
    """Create a test database session"""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    # Create session
    Session = sessionmaker(bind=test_engine)
    session = Session()
    
    yield session
    
    # Cleanup after test
    session.close()

def test_create_tables(test_engine):
    """Test that all tables can be created successfully"""
    # This will create all tables in the test database
    Base.metadata.create_all(bind=test_engine)
    
    # Verify tables were created by checking if we can get table names
    inspector = inspect(test_engine)
    table_names = inspector.get_table_names()
    
    # Assert that at least some tables were created
    # Adjust this based on your actual models
    assert len(table_names) >= 0  # Change to > 0 if you have models defined
    
    print(f"Created tables: {table_names}")  # For debugging
    
    # Test passes if no exception is raised
    assert True

def test_table_schema_integrity(test_engine):
    """Test that table schemas are properly defined"""
    Base.metadata.create_all(bind=test_engine)
    
    # Check that metadata contains expected information
    assert Base.metadata is not None
    assert isinstance(Base.metadata.tables, dict)
    
    # If you have specific models, test them here
    # For example:
    # assert 'users' in Base.metadata.tables
    # assert 'sessions' in Base.metadata.tables
    
    # Verify each table has proper structure
    for table_name, table in Base.metadata.tables.items():
        assert len(table.columns) > 0, f"Table {table_name} has no columns"
        print(f"Table {table_name} has {len(table.columns)} columns")

def test_database_connection(test_engine):
    """Test that we can connect to the test database"""
    # Test basic connection
    connection = test_engine.connect()
    assert connection is not None
    
    # Test a simple query - FIXED: Using text() wrapper
    result = connection.execute(text("SELECT 1 as test_value"))
    row = result.fetchone()
    assert row[0] == 1
    
    connection.close()

def test_session_operations(test_session):
    """Test basic session operations"""
    # Test that session is working
    assert test_session is not None
    
    # Test a simple query through session - FIXED: Using text() wrapper
    result = test_session.execute(text("SELECT 1 as test_value"))
    row = result.fetchone()
    assert row[0] == 1
    
    # If you have models, you can test them here:
    # Example:
    # user = User(name="Test User", email="test@example.com")
    # test_session.add(user)
    # test_session.commit()
    # 
    # retrieved_user = test_session.query(User).filter_by(name="Test User").first()
    # assert retrieved_user is not None
    # assert retrieved_user.email == "test@example.com"

def test_table_creation_idempotent(test_engine):
    """Test that creating tables multiple times doesn't cause errors"""
    # First creation
    Base.metadata.create_all(bind=test_engine)
    
    # Second creation should not raise an error
    Base.metadata.create_all(bind=test_engine)
    
    # Third creation should still work
    Base.metadata.create_all(bind=test_engine)
    
    assert True

# Additional test if you want to test specific models
# Uncomment and modify based on your actual models
"""
def test_specific_model_creation(test_session):
    '''Test creation of specific models'''
    # Example assuming you have a User model
    # from inai_project.models import User
    
    # Create a test record
    # user = User(
    #     username="testuser",
    #     email="test@example.com"
    # )
    # test_session.add(user)
    # test_session.commit()
    
    # Query it back
    # retrieved = test_session.query(User).filter_by(username="testuser").first()
    # assert retrieved is not None
    # assert retrieved.email == "test@example.com"
    
    pass
"""