from __future__ import annotations

import asyncio

from app.schemas.job import JobTask


class QueueService:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[JobTask] = asyncio.Queue()

    async def enqueue(self, task: JobTask) -> None:
        await self._queue.put(task)

    async def dequeue(self) -> JobTask:
        return await self._queue.get()

    def task_done(self) -> None:
        self._queue.task_done()

    def size(self) -> int:
        return self._queue.qsize()


queue_service = QueueService()
