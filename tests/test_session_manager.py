import pytest
from app.session import UserSessionManager
from unittest.mock import MagicMock


def test_create_and_get_user_session():
    logger = MagicMock()
    manager = UserSessionManager(logger)
    user_id = "user1"
    sid = "sid1"
    manager.create_user_session(user_id, sid)
    session = manager.get_user_session(user_id)
    assert session is not None
    assert session["sid"] == sid


def test_cleanup_user_session():
    logger = MagicMock()
    manager = UserSessionManager(logger)
    user_id = "user2"
    sid = "sid2"
    manager.create_user_session(user_id, sid)
    manager.cleanup_user_session(user_id)
    assert manager.get_user_session(user_id) is None


def test_clear_all_sessions():
    logger = MagicMock()
    manager = UserSessionManager(logger)
    manager.create_user_session("user1", "sid1")
    manager.create_user_session("user2", "sid2")
    manager.clear_all_sessions()
    assert manager.get_user_session("user1") is None
    assert manager.get_user_session("user2") is None