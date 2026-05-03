from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sessions.repository import SessionRepository
from app.modules.sessions.schemas import SessionCreate, SessionRead, SessionListItem


class SessionService:
    def __init__(
        self,
        db: AsyncSession,
        repository: Optional[SessionRepository] = None,
    ) -> None:
        self.repository = repository or SessionRepository(db)

    async def create(self, data: SessionCreate) -> SessionRead:
        name = data.name.strip()
        if not name:
            raise HTTPException(
                status_code=422, detail="Session name cannot be empty"
            )
        session = await self.repository.create(name)
        return SessionRead.model_validate(session)

    async def get_all(self) -> list[SessionListItem]:
        rows = await self.repository.get_all()
        return [
            SessionListItem(
                id=session.id,
                name=session.name,
                created_at=session.created_at,
                updated_at=session.updated_at,
                message_count=count,
            )
            for session, count in rows
        ]

    async def get_by_id(self, session_id: str) -> SessionRead:
        session = await self.repository.get_by_id(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return SessionRead.model_validate(session)

    async def delete(self, session_id: str) -> None:
        deleted = await self.repository.delete(session_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Session not found")
