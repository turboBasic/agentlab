from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from agentlab.storage.repository import SessionRepository
from agentlab.types import Message


@dataclass
class Session:
    id: str
    repository: SessionRepository
    messages: list[Message] = field(default_factory=list[Message])
    next_seq: int = 0

    @classmethod
    async def create(cls, repository: SessionRepository) -> Session:
        session_id = str(uuid.uuid4())
        await repository.create_session(session_id)
        return cls(id=session_id, repository=repository)

    @classmethod
    async def resume(cls, repository: SessionRepository, session_id: str) -> Session:
        messages = await repository.load_messages(session_id)
        return cls(id=session_id, repository=repository, messages=messages, next_seq=len(messages))

    async def append(self, message: Message) -> None:
        self.messages.append(message)
        await self.repository.append_message(self.id, self.next_seq, message)
        self.next_seq += 1
