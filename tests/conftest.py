from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from agentlab.storage.db import connect_in_memory
from agentlab.storage.repository import SessionRepository


@pytest.fixture
async def repository() -> AsyncIterator[SessionRepository]:
    connection = await connect_in_memory()
    try:
        yield SessionRepository(connection)
    finally:
        await connection.close()
