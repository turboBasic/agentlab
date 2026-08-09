from __future__ import annotations

from pathlib import Path

import aiosqlite

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    seq INTEGER NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, seq);
"""


async def connect(db_path: Path) -> aiosqlite.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return await _connect_and_init(str(db_path))


async def connect_in_memory() -> aiosqlite.Connection:
    return await _connect_and_init(":memory:")


async def _connect_and_init(target: str) -> aiosqlite.Connection:
    connection = await aiosqlite.connect(target)
    await connection.executescript(_SCHEMA)
    await connection.commit()
    return connection
