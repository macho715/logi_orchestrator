from __future__ import annotations

from fastapi import APIRouter

from app.workers.queue import queue_service

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, object]:
    return {
        "ok": True,
        "service": "hvdc-orchestrator",
        "queue_size": queue_service.size(),
    }
