from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import AgentType, JobCommand, JobState, JobTaskType, OrchestrationMode


class JobCreatePayload(BaseModel):
    repo: str
    base: str
    goal: str
    ac: str
    mode: str = "default"
    priority: str = "normal"
    requested_by: str
    chat_id: int | None = None
    trace_id: str


class CommandEnvelope(BaseModel):
    command: JobCommand
    raw_text: str
    actor: str
    chat_id: int | None = None
    args: dict[str, str] = Field(default_factory=dict)
    trace_id: str


class AgentAssignment(BaseModel):
    """Maps a task phase to the AI agent that handles it."""

    phase: JobTaskType
    agent: AgentType
    role: str


class JobRecord(BaseModel):
    job_id: str
    repo: str
    base_branch: str
    goal: str
    acceptance_criteria: str
    mode: str
    orchestration_mode: OrchestrationMode = OrchestrationMode.SINGLE
    priority: str = "normal"
    requested_by: str
    approved_by: str | None = None
    state: JobState
    previous_state: JobState | None = None
    resume_target_state: JobState | None = None
    current_phase: str = "bootstrap"
    retry_count: dict[str, int] = Field(default_factory=dict)
    trace_id: str
    chat_id: int | None = None
    created_at: datetime
    updated_at: datetime
    run_dir: str
    artifacts: list[str] = Field(default_factory=list)
    agent_assignments: list[AgentAssignment] = Field(default_factory=list)
    notes: dict[str, str] = Field(default_factory=dict)


class AuditEvent(BaseModel):
    ts: datetime
    job_id: str
    from_state: JobState | None = None
    to_state: JobState
    event: str
    actor: str
    trace_id: str
    detail: dict[str, str] = Field(default_factory=dict)


class JobTask(BaseModel):
    job_id: str
    task_type: JobTaskType
    actor: str = "SYSTEM"
    trace_id: str
    payload: dict[str, str] = Field(default_factory=dict)


class WebhookAck(BaseModel):
    ok: bool = True
    message: str
    job_id: str | None = None
    state: JobState | None = None
    trace_id: str | None = None
