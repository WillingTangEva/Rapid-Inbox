from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParseTask:
    message_id: str


class ParseQueue:
    def __init__(self, worker: Callable[[ParseTask], Awaitable[None]]) -> None:
        self._worker = worker
        self._queue: asyncio.Queue[ParseTask | None] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        await self._queue.put(None)
        await self._task
        self._task = None

    async def enqueue(self, task: ParseTask) -> None:
        await self._queue.put(task)

    async def drain(self) -> None:
        await self._queue.join()

    async def _run(self) -> None:
        while True:
            task = await self._queue.get()
            try:
                if task is None:
                    return
                try:
                    await self._worker(task)
                except Exception:
                    continue
            finally:
                self._queue.task_done()
