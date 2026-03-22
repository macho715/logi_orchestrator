from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.enums import JobCommand
from app.core.exceptions import AuthorizationError, NotFoundError, StateTransitionError, ValidationError
from app.schemas.job import JobCreatePayload, WebhookAck
from app.schemas.telegram import TelegramUpdate
from app.services.command_parser import parse_command
from app.services.job_service import JobService

router = APIRouter(prefix="/webhooks", tags=["telegram"])
job_service = JobService()


@router.post("/telegram", response_model=WebhookAck)
async def telegram_webhook(update: TelegramUpdate) -> WebhookAck:
    if update.message is None or not update.message.text:
        return WebhookAck(message="message.text 없음, 무시", trace_id=str(update.update_id))

    actor = update.message.from_user.username or update.message.from_user.first_name or "unknown"
    trace_id = f"tg-{update.update_id}"
    try:
        envelope = parse_command(
            raw_text=update.message.text,
            actor=actor,
            chat_id=update.message.chat.id,
            trace_id=trace_id,
        )
        if envelope.command == JobCommand.PROJECT_START:
            payload = JobCreatePayload(
                repo=envelope.args["repo"],
                base=envelope.args["base"],
                goal=envelope.args["goal"],
                ac=envelope.args["ac"],
                mode=envelope.args.get("mode", "default"),
                priority=envelope.args.get("priority", "normal"),
                requested_by=envelope.actor,
                chat_id=envelope.chat_id,
                trace_id=envelope.trace_id,
            )
            job = await job_service.create_job(payload)
            return WebhookAck(message="job created", job_id=job.job_id, state=job.state, trace_id=job.trace_id)

        if envelope.command == JobCommand.STATUS:
            job = job_service.get_job(envelope.args["job_id"])
            return WebhookAck(
                message=f"state={job.state.value}", job_id=job.job_id, state=job.state, trace_id=job.trace_id
            )

        if envelope.command == JobCommand.APPROVE_PLAN:
            job = await job_service.approve_plan(envelope.args["job_id"], envelope.actor)
            return WebhookAck(message="plan approved", job_id=job.job_id, state=job.state, trace_id=job.trace_id)

        if envelope.command == JobCommand.APPROVE_MERGE:
            job = await job_service.approve_merge(envelope.args["job_id"], envelope.actor)
            return WebhookAck(message="merge approved", job_id=job.job_id, state=job.state, trace_id=job.trace_id)

        if envelope.command == JobCommand.REPORT:
            job = job_service.get_job(envelope.args["job_id"])
            return WebhookAck(
                message=f"artifacts={len(job.artifacts)}", job_id=job.job_id, state=job.state, trace_id=job.trace_id
            )

        if envelope.command == JobCommand.ARTIFACTS:
            job = job_service.get_job(envelope.args["job_id"])
            return WebhookAck(
                message=";".join(job.artifacts), job_id=job.job_id, state=job.state, trace_id=job.trace_id
            )

        if envelope.command == JobCommand.PAUSE:
            job = job_service.pause(envelope.args["job_id"], envelope.actor)
            return WebhookAck(message="job paused", job_id=job.job_id, state=job.state, trace_id=job.trace_id)

        if envelope.command == JobCommand.RESUME:
            job = job_service.resume(envelope.args["job_id"], envelope.actor)
            return WebhookAck(message="job resumed", job_id=job.job_id, state=job.state, trace_id=job.trace_id)

        if envelope.command == JobCommand.ABORT:
            job = job_service.abort(envelope.args["job_id"], envelope.actor)
            return WebhookAck(message="job aborted", job_id=job.job_id, state=job.state, trace_id=job.trace_id)

        raise HTTPException(status_code=400, detail="지원되지 않는 명령입니다.")

    except (ValidationError, AuthorizationError, StateTransitionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
