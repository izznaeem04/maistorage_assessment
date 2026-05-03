import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from app.modules.sessions.service import SessionService
from app.modules.sessions.schemas import SessionCreate


def _make_session(**kwargs) -> MagicMock:
    """Return a MagicMock that looks like a Session ORM object."""
    defaults = {
        "id": "session-1",
        "name": "Test Session",
        "created_at": datetime(2024, 1, 1, 12, 0, 0),
        "updated_at": datetime(2024, 1, 1, 12, 0, 0),
    }
    defaults.update(kwargs)
    session = MagicMock()
    for key, val in defaults.items():
        setattr(session, key, val)
    return session


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_session_success():
    mock_repo = AsyncMock()
    mock_repo.create.return_value = _make_session(name="My Chat")

    service = SessionService(db=MagicMock(), repository=mock_repo)
    result = await service.create(SessionCreate(name="My Chat"))

    mock_repo.create.assert_called_once_with("My Chat")
    assert result.name == "My Chat"


@pytest.mark.asyncio
async def test_create_session_strips_whitespace():
    mock_repo = AsyncMock()
    mock_repo.create.return_value = _make_session(name="Trimmed")

    service = SessionService(db=MagicMock(), repository=mock_repo)
    await service.create(SessionCreate(name="  Trimmed  "))

    mock_repo.create.assert_called_once_with("Trimmed")


@pytest.mark.asyncio
async def test_create_session_empty_name_raises_422():
    mock_repo = AsyncMock()
    service = SessionService(db=MagicMock(), repository=mock_repo)

    with pytest.raises(HTTPException) as exc_info:
        await service.create(SessionCreate(name="   "))

    assert exc_info.value.status_code == 422
    mock_repo.create.assert_not_called()


# ---------------------------------------------------------------------------
# get_all
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_all_returns_list():
    sessions = [_make_session(id=f"s-{i}", name=f"Session {i}") for i in range(3)]
    mock_repo = AsyncMock()
    mock_repo.get_all.return_value = [(s, i * 2) for i, s in enumerate(sessions)]

    service = SessionService(db=MagicMock(), repository=mock_repo)
    result = await service.get_all()

    assert len(result) == 3
    assert result[0].message_count == 0
    assert result[1].message_count == 2
    mock_repo.get_all.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_empty():
    mock_repo = AsyncMock()
    mock_repo.get_all.return_value = []

    service = SessionService(db=MagicMock(), repository=mock_repo)
    result = await service.get_all()

    assert result == []


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_by_id_found():
    session = _make_session()
    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = session

    service = SessionService(db=MagicMock(), repository=mock_repo)
    result = await service.get_by_id("session-1")

    assert result.id == "session-1"
    mock_repo.get_by_id.assert_called_once_with("session-1")


@pytest.mark.asyncio
async def test_get_by_id_not_found_raises_404():
    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = None

    service = SessionService(db=MagicMock(), repository=mock_repo)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_by_id("nonexistent")

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_success():
    mock_repo = AsyncMock()
    mock_repo.delete.return_value = True

    service = SessionService(db=MagicMock(), repository=mock_repo)
    await service.delete("session-1")  # must not raise

    mock_repo.delete.assert_called_once_with("session-1")


@pytest.mark.asyncio
async def test_delete_not_found_raises_404():
    mock_repo = AsyncMock()
    mock_repo.delete.return_value = False

    service = SessionService(db=MagicMock(), repository=mock_repo)

    with pytest.raises(HTTPException) as exc_info:
        await service.delete("nonexistent")

    assert exc_info.value.status_code == 404
