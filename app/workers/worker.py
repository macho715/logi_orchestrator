from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime
from pathlib import Path

from app.core.enums import JobEvent, JobState, JobTaskType, OrchestrationMode
from app.infra.filesystem import write_json, write_text
from app.infra.git_worktree import GitWorktreeManager
from app.infra.storage import FileJobStore
from app.schemas.job import AuditEvent, JobRecord, JobTask
from app.services.audit import AuditService
from app.services.state_machine import transition
from app.workers.agent_resolver import resolve_assignments
from app.workers.queue import queue_service


class QueueWorker:
    def __init__(self) -> None:
        self.store = FileJobStore()
        self.audit = AuditService()
        self.worktrees = GitWorktreeManager()
        self._task: asyncio.Task | None = None
        self._running = False

    def _now(self) -> datetime:
        return datetime.now().astimezone()

    def _transition(
        self, job: JobRecord, event: str, actor: str = "SYSTEM", detail: dict[str, str] | None = None
    ) -> JobRecord:
        from_state = job.state
        job.previous_state = from_state
        job.state = transition(job.state, event)
        job.updated_at = self._now()
        self.store.save(job)
        audit = AuditEvent(
            ts=self._now(),
            job_id=job.job_id,
            from_state=from_state,
            to_state=job.state,
            event=event,
            actor=actor,
            trace_id=job.trace_id,
            detail=detail or {},
        )
        self.audit.write(self.store.audit_file(job.job_id), audit)
        return job

    def _add_artifact(self, job: JobRecord, path: str) -> JobRecord:
        if path not in job.artifacts:
            job.artifacts.append(path)
            self.store.save(job)
        return job

    async def start(self) -> None:
        if self._task is None:
            self._running = True
            self._task = asyncio.create_task(self._run(), name="hvdc-queue-worker")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run(self) -> None:
        while self._running:
            task = await queue_service.dequeue()
            try:
                await self._handle(task)
            finally:
                queue_service.task_done()

    async def _handle(self, task: JobTask) -> None:
        job = self.store.get(task.job_id)
        if job.state in {JobState.ABORTED, JobState.DONE}:
            return

        if task.task_type == JobTaskType.PLAN:
            await self._handle_plan(job)
        elif task.task_type == JobTaskType.EXEC:
            await self._handle_exec(job)
        elif task.task_type == JobTaskType.TEST:
            await self._handle_test(job)
        elif task.task_type == JobTaskType.REVIEW:
            await self._handle_review(job)
        elif task.task_type == JobTaskType.MERGE:
            await self._handle_merge(job)

    async def _handle_plan(self, job: JobRecord) -> None:
        run_dir = Path(job.run_dir)
        plan_dir = run_dir / "plan"

        # Resolve agent assignments for the chosen orchestration mode
        try:
            orch_mode = OrchestrationMode(job.orchestration_mode)
        except ValueError:
            orch_mode = OrchestrationMode.SINGLE
        assignments = resolve_assignments(orch_mode)
        job.agent_assignments = assignments
        self.store.save(job)

        plan_path = write_text(
            plan_dir / "PLAN.md",
            f"# PLAN\n\n- repo: {job.repo}\n- goal: {job.goal}\n- ac: {job.acceptance_criteria}\n- mode: {job.mode}\n- orchestration: {orch_mode.value}\n",
        )
        tasks_path = write_text(
            plan_dir / "TASKS.yaml",
            "tasks:\n  - id: T010\n    owner: CLAUDE_LEAD\n  - id: T030\n    owner: CODEX_IMPL_A\n",
        )
        risks_path = write_text(
            plan_dir / "RISKS.md",
            "# RISKS\n\n- scope drift\n- concurrent write collision\n- test gap\n- merge conflict\n- approval lag\n",
        )
        tests_path = write_text(
            plan_dir / "TESTS.md",
            "# TESTS\n\n- lint\n- unit\n- smoke\n",
        )

        # Agent assignment artifact
        assignment_lines = [f"orchestration_mode: {orch_mode.value}\nassignments:\n"]
        for a in assignments:
            assignment_lines.append(f'  - phase: {a.phase}\n    agent: {a.agent}\n    role: "{a.role}"\n')
        assign_path = write_text(plan_dir / "agent_assignments.yaml", "".join(assignment_lines))

        for artifact in [plan_path, tasks_path, risks_path, tests_path, assign_path]:
            job = self._add_artifact(job, artifact)

        job = self._transition(job, JobEvent.PLAN_DONE.value)
        job.current_phase = "approval_plan"
        self.store.save(job)
        job = self._transition(job, JobEvent.REPORT_PLAN.value, detail={"message": "plan artifacts ready"})
        await asyncio.sleep(0.05)

    async def _handle_exec(self, job: JobRecord) -> None:
        job = self._transition(job, JobEvent.EXEC_START.value)
        run_dir = Path(job.run_dir)
        codex_dir = run_dir / "codex"

        wt_a = self.worktrees.create_stub(run_dir, "impl_a")
        wt_b = self.worktrees.create_stub(run_dir, "impl_b")
        diff_a = write_text(codex_dir / "patch_A.diff", "--- a/app.py\n+++ b/app.py\n@@\n+# stub patch A\n")
        diff_b = write_text(codex_dir / "patch_B.diff", "--- a/app.py\n+++ b/app.py\n@@\n+# stub patch B\n")
        note_a = write_text(codex_dir / "impl_A_notes.md", f"# Impl A\n\n- worktree: {wt_a}\n")
        note_b = write_text(codex_dir / "impl_B_notes.md", f"# Impl B\n\n- worktree: {wt_b}\n")

        for artifact in [diff_a, diff_b, note_a, note_b]:
            job = self._add_artifact(job, artifact)

        job.current_phase = "test"
        self.store.save(job)
        job = self._transition(job, JobEvent.IMPL_DONE.value)
        await queue_service.enqueue(JobTask(job_id=job.job_id, task_type=JobTaskType.TEST, trace_id=job.trace_id))

    async def _handle_test(self, job: JobRecord) -> None:
        run_dir = Path(job.run_dir)
        test_dir = run_dir / "tests"
        results = write_json(
            test_dir / "test_results.json",
            {
                "job_id": job.job_id,
                "lint": "pass",
                "unit": "pass",
                "smoke": "pass",
                "timestamp": self._now().isoformat(),
            },
        )
        smoke = write_text(test_dir / "smoke_report.md", "# Smoke Report\n\n- result: PASS\n")
        for artifact in [results, smoke]:
            job = self._add_artifact(job, artifact)

        job.current_phase = "review"
        self.store.save(job)
        job = self._transition(job, JobEvent.TESTS_DONE.value)
        await queue_service.enqueue(JobTask(job_id=job.job_id, task_type=JobTaskType.REVIEW, trace_id=job.trace_id))

    async def _handle_review(self, job: JobRecord) -> None:
        run_dir = Path(job.run_dir)
        review_dir = run_dir / "review"
        summary = write_text(
            review_dir / "review_summary.md",
            "# Review Summary\n\n- verdict: PASS_WITH_WARNINGS\n- rollback: git revert <sha>\n",
        )
        verdict = write_json(
            review_dir / "merge_verdict.json",
            {
                "verdict": "PASS_WITH_WARNINGS",
                "rollback": "git revert <sha>",
                "changed_files": 4,
            },
        )
        for artifact in [summary, verdict]:
            job = self._add_artifact(job, artifact)

        job.current_phase = "approval_merge"
        self.store.save(job)
        job = self._transition(job, JobEvent.REVIEW_DONE.value)

    async def _handle_merge(self, job: JobRecord) -> None:
        run_dir = Path(job.run_dir)
        report_path = write_text(
            run_dir / "final_report.md",
            f"# Final Report\n\n- job_id: {job.job_id}\n- result: DONE\n- repo: {job.repo}\n",
        )
        job = self._add_artifact(job, report_path)
        job.current_phase = "done"
        self.store.save(job)
        self._transition(job, JobEvent.MERGE_OK.value)


queue_worker = QueueWorker()
