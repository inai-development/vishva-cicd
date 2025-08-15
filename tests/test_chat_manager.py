import pytest
from unittest.mock import MagicMock
from app.chat import ChatManager


@pytest.mark.asyncio
async def test_chat_with_groq_success(monkeypatch):
    # Mock config, modes, logger
    config = MagicMock()
    config.groq_api_key = "test_key"
    modes = MagicMock()
    modes.modes = {"friend": "system prompt"}
    logger = MagicMock()

    # Correct Mock Completion Response
    class MockCompletion:
        def __init__(self):
            self.choices = [MagicMock(message=MagicMock(content="Hello!"))]

    # Mock OpenAI client
    class MockCompletions:
        @staticmethod
        def create(**kwargs):
            return MockCompletion()

    class MockChat:
        completions = MockCompletions()

    class MockClient:
        chat = MockChat()

    monkeypatch.setattr("app.chat.OpenAI", lambda **kwargs: MockClient())

    chat_manager = ChatManager(config, modes, logger)
    reply = await chat_manager.chat_with_groq("user1", "friend", "Hi!")
    assert reply == "Hello!"


@pytest.mark.asyncio
async def test_chat_with_groq_error(monkeypatch):
    config = MagicMock()
    config.groq_api_key = "test_key"
    modes = MagicMock()
    modes.modes = {"friend": "system prompt"}
    logger = MagicMock()

    # Mock OpenAI client with error
    class MockCompletions:
        @staticmethod
        def create(**kwargs):
            raise Exception("API error")

    class MockChat:
        completions = MockCompletions()

    class MockClient:
        chat = MockChat()

    monkeypatch.setattr("app.chat.OpenAI", lambda **kwargs: MockClient())

    chat_manager = ChatManager(config, modes, logger)
    reply = await chat_manager.chat_with_groq("user1", "friend", "Hi!")
    assert "trouble" in reply  # Loose check, matches error reply