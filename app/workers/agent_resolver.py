"""Resolve agent assignments for each orchestration mode.

⚠️ stub v1: assignments are descriptive only.  The worker does not yet
dispatch to real Claude / Codex / Gemini backends.
"""

from __future__ import annotations

from app.core.enums import AgentType, JobTaskType, OrchestrationMode
from app.schemas.job import AgentAssignment

# ------------------------------------------------------------------ #
#  Per-mode assignment tables                                        #
# ------------------------------------------------------------------ #

_SINGLE: list[AgentAssignment] = [
    AgentAssignment(phase=JobTaskType.PLAN, agent=AgentType.CLAUDE, role="plan & review lead"),
    AgentAssignment(phase=JobTaskType.EXEC, agent=AgentType.CLAUDE, role="implementation"),
    AgentAssignment(phase=JobTaskType.TEST, agent=AgentType.CLAUDE, role="test execution"),
    AgentAssignment(phase=JobTaskType.REVIEW, agent=AgentType.CLAUDE, role="code review"),
    AgentAssignment(phase=JobTaskType.MERGE, agent=AgentType.CLAUDE, role="merge coordination"),
]

_PARALLEL: list[AgentAssignment] = [
    AgentAssignment(phase=JobTaskType.PLAN, agent=AgentType.CLAUDE, role="plan lead"),
    AgentAssignment(phase=JobTaskType.EXEC, agent=AgentType.CODEX, role="implementation (parallel)"),
    AgentAssignment(phase=JobTaskType.TEST, agent=AgentType.CODEX, role="test execution (parallel)"),
    AgentAssignment(phase=JobTaskType.REVIEW, agent=AgentType.CLAUDE, role="code review"),
    AgentAssignment(phase=JobTaskType.MERGE, agent=AgentType.CLAUDE, role="merge coordination"),
]

_MULTI_MODEL: list[AgentAssignment] = [
    AgentAssignment(phase=JobTaskType.PLAN, agent=AgentType.CLAUDE, role="architecture & plan"),
    AgentAssignment(phase=JobTaskType.EXEC, agent=AgentType.CODEX, role="logic implementation"),
    AgentAssignment(phase=JobTaskType.TEST, agent=AgentType.CODEX, role="test execution"),
    AgentAssignment(phase=JobTaskType.REVIEW, agent=AgentType.GEMINI, role="UI/UX & design review"),
    AgentAssignment(phase=JobTaskType.MERGE, agent=AgentType.CLAUDE, role="integration & merge"),
]

_MODE_TABLE: dict[OrchestrationMode, list[AgentAssignment]] = {
    OrchestrationMode.SINGLE: _SINGLE,
    OrchestrationMode.PARALLEL: _PARALLEL,
    OrchestrationMode.MULTI_MODEL: _MULTI_MODEL,
}


def resolve_assignments(mode: OrchestrationMode) -> list[AgentAssignment]:
    """Return the agent assignment list for the given *mode*.

    Falls back to ``SINGLE`` if *mode* is not found (should not happen
    when using the enum).
    """
    return list(_MODE_TABLE.get(mode, _SINGLE))
