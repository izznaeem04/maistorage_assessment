from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, AsyncSessionLocal
from app.modules.chat.service import ChatService
from app.modules.chat.schemas import ChatRequest, MessageRead
from app.modules.sessions.repository import SessionRepository

router = APIRouter()


@router.post("/stream")
async def stream_chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    # Validate session exists before opening the stream (proper HTTP error response).
    session_repo = SessionRepository(db)
    session = await session_repo.get_by_id(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # The generator opens its own session so it outlives the request dependency lifecycle.
    async def _generate():
        async with AsyncSessionLocal() as stream_db:
            service = ChatService(stream_db)
            async for event in service.stream_response(
                request.session_id, request.content
            ):
                yield event

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/sessions/{session_id}/messages", response_model=list[MessageRead])
async def get_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = ChatService(db)
    return await service.get_history(session_id)
