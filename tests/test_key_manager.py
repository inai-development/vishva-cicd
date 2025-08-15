import pytest
from app import key_manager
from unittest.mock import patch
from datetime import datetime

@pytest.fixture(autouse=True)
def reset_state():
    # Reset global state before each test
    key_manager.user_sessions.clear()
    key_manager.user_token_usage.clear()
    key_manager.key_usage_count = {key: 0 for key in key_manager.api_keys}
    yield

def test_assign_key_to_user_creates_session():
    user_id = "test_user"
    result = key_manager.assign_key_to_user(user_id, task="Test Task")

    assert "api_key" in result
    assert user_id in key_manager.user_sessions
    session = key_manager.user_sessions[user_id]
    assert session["task"] == "Test Task"
    assert result["message"].startswith("✅ Assigned least-loaded key")

def test_assign_key_to_user_returns_same_key_if_already_assigned():
    user_id = "user_existing"
    first = key_manager.assign_key_to_user(user_id)
    second = key_manager.assign_key_to_user(user_id)

    assert first["api_key"] == second["api_key"]
    assert second["message"] == "Already assigned"

def test_release_key_for_user_decreases_key_usage():
    user_id = "user_release"
    assign_result = key_manager.assign_key_to_user(user_id)
    key = assign_result["api_key"]
    usage_before = key_manager.key_usage_count[key]

    release_result = key_manager.release_key_for_user(user_id)
    usage_after = key_manager.key_usage_count[key]

    assert release_result["message"].startswith("✅ Released")
    assert usage_after == max(0, usage_before - 1)

def test_release_key_for_nonexistent_user():
    result = key_manager.release_key_for_user("nonexistent_user")
    assert "error" in result
    assert result["error"].startswith("⚠️")

def test_update_last_active_and_sid():
    user_id = "active_user"
    sid = "sid123"
    key_manager.assign_key_to_user(user_id)
    key_manager.update_last_active(user_id, sid=sid)
    
    session = key_manager.user_sessions[user_id]
    assert session["sid"] == sid
    assert "last_active" in session

def test_get_monitor_data_structure():
    key_manager.assign_key_to_user("monitor_user")
    monitor_data = key_manager.get_monitor_data()

    assert "total_keys" in monitor_data
    assert "key_usage" in monitor_data
    assert "user_sessions" in monitor_data
    assert "token_usage_per_user" in monitor_data
    assert "monitor_user" in monitor_data["user_sessions"]