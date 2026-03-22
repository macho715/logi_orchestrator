from __future__ import annotations

from datetime import datetime

from app.config import settings
from app.core.enums import JobEvent, JobState, JobTaskType, OrchestrationMode
from app.core.exceptions import AuthorizationError, ValidationError
from app.infra.storage import FileJobStore
from app.schemas.job import AuditEvent, JobCreatePayload, JobRecord, JobTask
from app.services.acl import ACLService
from app.services.audit import AuditService
from app.services.state_machine import resume_event_name, transition
from app.workers.queue import queue_service


class JobService:
    def __init__(self) -> None:
        self.store = FileJobStore()
        self.acl = ACLService()
        self.audit = AuditService()

    def _now(self) -> datetime:
        return datetime.now().astimezone()

    def _next_job_id(self) -> str:
        runs_dir = settings.resolved_runs_dir
        runs_dir.mkdir(parents=True, exist_ok=True)
        existing = sorted([p.name for p in runs_dir.iterdir() if p.is_dir() and p.name.startswith("JOB-")])
        if not existing:
            return "JOB-0001"
        last = existing[-1]
        num = int(last.split("-")[1]) + 1
        return f"JOB-{num:04d}"

    def _audit(
        self,
        job: JobRecord,
        *,
        from_state: JobState | None,
        to_state: JobState,
        event: str,
        actor: str,
        detail: dict[str, str] | None = None,
    ) -> None:
        audit = AuditEvent(
            ts=self._now(),
            job_id=job.job_id,
            from_state=from_state,
            to_state=to_state,
            event=event,
            actor=actor,
            trace_id=job.trace_id,
            detail=detail or {},
        )
        self.audit.write(self.store.audit_file(job.job_id), audit)

    def _apply_transition(
        self, job: JobRecord, event: str, actor: str, detail: dict[str, str] | None = None
    ) -> JobRecord:
        from_state = job.state
        to_state = transition(job.state, event)
        job.previous_state = from_state
        job.state = to_state
        job.updated_at = self._now()
        self.store.save(job)
        self._audit(job, from_state=from_state, to_state=to_state, event=event, actor=actor, detail=detail)
        return job

    async def create_job(self, payload: JobCreatePayload) -> JobRecord:
        if not self.acl.is_requester(payload.requested_by):
            raise AuthorizationError("requester 권한이 없습니다.")
        if not self.acl.is_repo_allowed(payload.repo):
            raise ValidationError("허용되지 않은 repo 입니다.")

        # Resolve orchestration mode from the mode field
        try:
            orch_mode = OrchestrationMode(payload.mode)
        except ValueError:
            orch_mode = OrchestrationMode.SINGLE

        now = self._now()
        job_id = self._next_job_id()
        run_dir = str(settings.resolved_runs_dir / job_id)
        job = JobRecord(
            job_id=job_id,
            repo=payload.repo,
            base_branch=payload.base,
            goal=payload.goal,
            acceptance_criteria=payload.ac,
            mode=payload.mode,
            orchestration_mode=orch_mode,
            priority=payload.priority,
            requested_by=payload.requested_by,
            state=JobState.RECEIVED,
            trace_id=payload.trace_id,
            chat_id=payload.chat_id,
            created_at=now,
            updated_at=now,
            run_dir=run_dir,
        )
        self.store.create(job)
        self._audit(job, from_state=None, to_state=job.state, event="received", actor=payload.requested_by)

        job = self._apply_transition(job, JobEvent.VALIDATE_OK.value, payload.requested_by)
        job.current_phase = "plan"
        self.store.save(job)

        job = self._apply_transition(job, JobEvent.PLAN_ENQUEUE.value, "SYSTEM")
        await queue_service.enqueue(JobTask(job_id=job.job_id, task_type=JobTaskType.PLAN, trace_id=job.trace_id))
        return job

    def get_job(self, job_id: str) -> JobRecord:
        return self.store.get(job_id)

    async def approve_plan(self, job_id: str, actor: str) -> JobRecord:
        if not self.acl.is_approver(actor):
            raise AuthorizationError("approver 권한이 없습니다.")
        job = self.store.get(job_id)
        job.approved_by = actor
        self.store.save(job)
        job = self._apply_transition(job, JobEvent.APPROVE_PLAN.value, actor)
        job.current_phase = "fanout_execute"
        self.store.save(job)
        await queue_service.enqueue(JobTask(job_id=job.job_id, task_type=JobTaskType.EXEC, trace_id=job.trace_id))
        return job

    async def approve_merge(self, job_id: str, actor: str) -> JobRecord:
        if not self.acl.is_approver(actor):
            raise AuthorizationError("approver 권한이 없습니다.")
        job = self.store.get(job_id)
        job.approved_by = actor
        self.store.save(job)
        job = self._apply_transition(job, JobEvent.APPROVE_MERGE.value, actor)
        job.current_phase = "merge"
        self.store.save(job)
        await queue_service.enqueue(JobTask(job_id=job.job_id, task_type=JobTaskType.MERGE, trace_id=job.trace_id))
        return job

    def pause(self, job_id: str, actor: str) -> JobRecord:
        if not self.acl.is_approver(actor):
            raise AuthorizationError("approver 권한이 없습니다.")
        job = self.store.get(job_id)
        job.resume_target_state = job.state
        self.store.save(job)
        job = self._apply_transition(job, JobEvent.PAUSE.value, actor)
        return job

    def resume(self, job_id: str, actor: str) -> JobRecord:
        if not self.acl.is_approver(actor):
            raise AuthorizationError("approver 권한이 없습니다.")
        job = self.store.get(job_id)
        if job.state != JobState.PAUSED:
            raise ValidationError("PAUSED 상태에서만 resume 가능합니다.")
        event_name = resume_event_name(job.resume_target_state)
        job = self._apply_transition(job, event_name, actor)
        return job

    def abort(self, job_id: str, actor: str) -> JobRecord:
        if not self.acl.is_approver(actor):
            raise AuthorizationError("approver 권한이 없습니다.")
        job = self.store.get(job_id)
        job = self._apply_transition(job, JobEvent.ABORT.value, actor)
        return job
