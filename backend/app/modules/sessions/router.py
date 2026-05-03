from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.sessions.service import SessionService
from app.modules.sessions.schemas import SessionCreate, SessionRead, SessionListItem

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db)) -> SessionService:
    return SessionService(db)


@router.get("/", response_model=list[SessionListItem])
async def list_sessions(service: SessionService = Depends(_get_service)):
    return await service.get_all()


@router.post("/", response_model=SessionRead, status_code=201)
async def create_session(
    body: SessionCreate,
    service: SessionService = Depends(_get_service),
):
    return await service.create(body)


@router.get("/{session_id}", response_model=SessionRead)
async def get_session(
    session_id: str,
    service: SessionService = Depends(_get_service),
):
    return await service.get_by_id(session_id)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    service: SessionService = Depends(_get_service),
):
    await service.delete(session_id)
