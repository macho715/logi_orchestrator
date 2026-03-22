from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from app.core.exceptions import AuthorizationError, NotFoundError, StateTransitionError, ValidationError
from app.schemas.job import WebhookAck
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])
job_service = JobService()


def _actor(x_actor: str | None) -> str:
    return (x_actor or "admin").lstrip("@").strip()


@router.get("/{job_id}")
async def get_job(job_id: str) -> dict:
    try:
        job = job_service.get_job(job_id)
        return job.model_dump(mode="json")
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{job_id}/artifacts")
async def list_artifacts(job_id: str) -> dict:
    try:
        job = job_service.get_job(job_id)
        return {"job_id": job.job_id, "artifacts": job.artifacts}
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{job_id}/approve-plan", response_model=WebhookAck)
async def approve_plan(job_id: str, x_actor: str | None = Header(default="admin")) -> WebhookAck:
    try:
        job = await job_service.approve_plan(job_id, _actor(x_actor))
        return WebhookAck(message="plan approved", job_id=job.job_id, state=job.state, trace_id=job.trace_id)
    except (ValidationError, AuthorizationError, StateTransitionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{job_id}/approve-merge", response_model=WebhookAck)
async def approve_merge(job_id: str, x_actor: str | None = Header(default="admin")) -> WebhookAck:
    try:
        job = await job_service.approve_merge(job_id, _actor(x_actor))
        return WebhookAck(message="merge approved", job_id=job.job_id, state=job.state, trace_id=job.trace_id)
    except (ValidationError, AuthorizationError, StateTransitionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{job_id}/pause", response_model=WebhookAck)
async def pause_job(job_id: str, x_actor: str | None = Header(default="admin")) -> WebhookAck:
    try:
        job = job_service.pause(job_id, _actor(x_actor))
        return WebhookAck(message="job paused", job_id=job.job_id, state=job.state, trace_id=job.trace_id)
    except (ValidationError, AuthorizationError, StateTransitionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{job_id}/resume", response_model=WebhookAck)
async def resume_job(job_id: str, x_actor: str | None = Header(default="admin")) -> WebhookAck:
    try:
        job = job_service.resume(job_id, _actor(x_actor))
        return WebhookAck(message="job resumed", job_id=job.job_id, state=job.state, trace_id=job.trace_id)
    except (ValidationError, AuthorizationError, StateTransitionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{job_id}/abort", response_model=WebhookAck)
async def abort_job(job_id: str, x_actor: str | None = Header(default="admin")) -> WebhookAck:
    try:
        job = job_service.abort(job_id, _actor(x_actor))
        return WebhookAck(message="job aborted", job_id=job.job_id, state=job.state, trace_id=job.trace_id)
    except (ValidationError, AuthorizationError, StateTransitionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
