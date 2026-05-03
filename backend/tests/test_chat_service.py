import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from app.modules.chat.service import build_gemini_contents, ChatService


def _make_message(role: str, content: str) -> MagicMock:
    msg = MagicMock()
    msg.role = role
    msg.content = content
    return msg


# ---------------------------------------------------------------------------
# build_gemini_contents (pure function — no async needed)
# ---------------------------------------------------------------------------


def test_build_gemini_contents_no_history():
    result = build_gemini_contents([], "Hello")

    assert len(result) == 1
    assert result[0]["role"] == "user"
    assert result[0]["parts"][0]["text"] == "Hello"


def test_build_gemini_contents_preserves_order():
    history = [
        _make_message("user", "Hi"),
        _make_message("assistant", "Hello!"),
        _make_message("user", "How are you?"),
        _make_message("assistant", "Fine!"),
    ]
    result = build_gemini_contents(history, "Great!")

    assert len(result) == 5
    assert result[0] == {"role": "user", "parts": [{"text": "Hi"}]}
    assert result[1] == {"role": "model", "parts": [{"text": "Hello!"}]}
    assert result[4] == {"role": "user", "parts": [{"text": "Great!"}]}


def test_build_gemini_contents_assistant_converted_to_model():
    history = [_make_message("assistant", "I am the assistant")]
    result = build_gemini_contents(history, "ok")

    assert result[0]["role"] == "model"
    assert result[1]["role"] == "user"


def test_build_gemini_contents_user_role_unchanged():
    history = [_make_message("user", "question")]
    result = build_gemini_contents(history, "follow-up")

    assert result[0]["role"] == "user"


def test_build_gemini_contents_new_message_is_last():
    history = [_make_message("user", "a"), _make_message("assistant", "b")]
    result = build_gemini_contents(history, "c")

    assert result[-1]["parts"][0]["text"] == "c"
    assert result[-1]["role"] == "user"


# ---------------------------------------------------------------------------
# ChatService.get_history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_history_session_not_found_raises_404():
    mock_session_repo = AsyncMock()
    mock_session_repo.get_by_id.return_value = None
    mock_message_repo = AsyncMock()

    service = ChatService(
        db=MagicMock(),
        message_repository=mock_message_repo,
        session_repository=mock_session_repo,
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.get_history("nonexistent")

    assert exc_info.value.status_code == 404
    mock_message_repo.get_by_session.assert_not_called()


@pytest.mark.asyncio
async def test_get_history_returns_messages():
    mock_session_repo = AsyncMock()
    mock_session_repo.get_by_id.return_value = MagicMock(id="s-1")

    messages = [
        _make_message("user", "Hello"),
        _make_message("assistant", "Hi!"),
    ]
    mock_message_repo = AsyncMock()
    mock_message_repo.get_by_session.return_value = messages

    service = ChatService(
        db=MagicMock(),
        message_repository=mock_message_repo,
        session_repository=mock_session_repo,
    )

    result = await service.get_history("s-1")

    assert len(result) == 2
    mock_message_repo.get_by_session.assert_called_once_with("s-1")


# ---------------------------------------------------------------------------
# ChatService.validate_session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_session_raises_404_when_missing():
    mock_session_repo = AsyncMock()
    mock_session_repo.get_by_id.return_value = None

    service = ChatService(
        db=MagicMock(),
        message_repository=AsyncMock(),
        session_repository=mock_session_repo,
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.validate_session("ghost")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_validate_session_passes_when_found():
    mock_session_repo = AsyncMock()
    mock_session_repo.get_by_id.return_value = MagicMock(id="s-1")

    service = ChatService(
        db=MagicMock(),
        message_repository=AsyncMock(),
        session_repository=mock_session_repo,
    )

    await service.validate_session("s-1")  # must not raise
