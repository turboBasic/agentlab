from __future__ import annotations

from datetime import UTC, datetime

import aiosqlite
from pydantic import TypeAdapter

from agentlab.types import Message

_message_adapter: TypeAdapter[Message] = TypeAdapter(Message)


class SessionRepository:
    def __init__(self, connection: aiosqlite.Connection) -> None:
        self._connection = connection

    async def create_session(self, session_id: str) -> None:
        await self._connection.execute(
            "INSERT INTO sessions (id, created_at) VALUES (?, ?)",
            (session_id, datetime.now(UTC).isoformat()),
        )
        await self._connection.commit()

    async def append_message(self, session_id: str, seq: int, message: Message) -> None:
        payload = _message_adapter.dump_json(message).decode()
        await self._connection.execute(
            "INSERT INTO messages (session_id, seq, payload, created_at) VALUES (?, ?, ?, ?)",
            (session_id, seq, payload, datetime.now(UTC).isoformat()),
        )
        await self._connection.commit()

    async def load_messages(self, session_id: str) -> list[Message]:
        cursor = await self._connection.execute(
            "SELECT payload FROM messages WHERE session_id = ? ORDER BY seq",
            (session_id,),
        )
        rows = await cursor.fetchall()
        return [_message_adapter.validate_json(row[0]) for row in rows]
