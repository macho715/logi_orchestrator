from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.telegram import router as telegram_router
from app.workers.worker import queue_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    await queue_worker.start()
    yield
    await queue_worker.stop()


app = FastAPI(
    title="HVDC Orchestrator",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(telegram_router)
app.include_router(jobs_router)
