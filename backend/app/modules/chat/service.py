import json
from typing import AsyncGenerator, Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.gemini import get_client
from app.models.message import Message
from app.modules.chat.repository import MessageRepository
from app.modules.sessions.repository import SessionRepository


def build_gemini_contents(history: list[Message], new_content: str) -> list[dict]:
    """Convert stored messages + new user input into Gemini content format."""
    contents = []
    for msg in history:
        role = "model" if msg.role == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": msg.content}]})
    contents.append({"role": "user", "parts": [{"text": new_content}]})
    return contents


class ChatService:
    def __init__(
        self,
        db: AsyncSession,
        message_repository: Optional[MessageRepository] = None,
        session_repository: Optional[SessionRepository] = None,
    ) -> None:
        self.message_repo = message_repository or MessageRepository(db)
        self.session_repo = session_repository or SessionRepository(db)

    async def get_history(self, session_id: str) -> list[Message]:
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return await self.message_repo.get_by_session(session_id)

    async def validate_session(self, session_id: str) -> None:
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

    async def stream_response(
        self,
        session_id: str,
        content: str,
    ) -> AsyncGenerator[str, None]:
        history = await self.message_repo.get_by_session(session_id)
        gemini_contents = build_gemini_contents(history, content)

        await self.message_repo.create(session_id, "user", content)
        await self.session_repo.update_timestamp(session_id)

        client = get_client()
        full_text = ""
        last_chunk = None

        try:
            async for chunk in await client.aio.models.generate_content_stream(
                model=settings.gemini_model,
                contents=gemini_contents,
            ):
                last_chunk = chunk
                token = chunk.text or ""
                full_text += token
                if token:
                    yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"
            return

        usage: Optional[dict] = None
        try:
            if last_chunk and last_chunk.usage_metadata:
                um = last_chunk.usage_metadata
                usage = {
                    "prompt_tokens": um.prompt_token_count,
                    "completion_tokens": um.candidates_token_count,
                    "total_tokens": um.total_token_count,
                }
        except Exception:
            pass

        assistant_msg = await self.message_repo.create(
            session_id=session_id,
            role="assistant",
            content=full_text,
            prompt_tokens=usage.get("prompt_tokens") if usage else None,
            completion_tokens=usage.get("completion_tokens") if usage else None,
            total_tokens=usage.get("total_tokens") if usage else None,
        )

        yield (
            f"event: done\ndata: "
            f"{json.dumps({'message_id': assistant_msg.id, 'usage': usage})}\n\n"
        )
