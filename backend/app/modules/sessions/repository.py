import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session
from app.models.message import Message


class SessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, name: str) -> Session:
        session = Session(
            id=str(uuid.uuid4()),
            name=name,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_all(self) -> list[tuple[Session, int]]:
        stmt = (
            select(Session, func.count(Message.id).label("message_count"))
            .outerjoin(Message, Message.session_id == Session.id)
            .group_by(Session.id)
            .order_by(Session.updated_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.all())

    async def get_by_id(self, session_id: str) -> Optional[Session]:
        result = await self.db.execute(
            select(Session).where(Session.id == session_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, session_id: str) -> bool:
        session = await self.get_by_id(session_id)
        if not session:
            return False
        await self.db.delete(session)
        await self.db.commit()
        return True

    async def update_timestamp(self, session_id: str) -> None:
        session = await self.get_by_id(session_id)
        if session:
            session.updated_at = datetime.utcnow()
            await self.db.commit()
