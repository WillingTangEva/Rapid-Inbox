from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from app.db.connection import connect_database


T = TypeVar("T")


class DatabaseWriter:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._lock = asyncio.Lock()

    async def execute(self, operation: Callable[[sqlite3.Connection], T]) -> T:
        async with self._lock:
            with connect_database(self._database_path) as connection:
                try:
                    result = operation(connection)
                except Exception:
                    connection.rollback()
                    raise
                connection.commit()
                return result
