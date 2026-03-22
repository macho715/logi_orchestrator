"""Tests for multi-agent orchestration enums and agent resolver."""

from __future__ import annotations

from app.core.enums import AgentType, JobTaskType, OrchestrationMode
from app.schemas.job import AgentAssignment
from app.workers.agent_resolver import resolve_assignments

# ------------------------------------------------------------------ #
#  Enum tests                                                        #
# ------------------------------------------------------------------ #


def test_agent_type_values() -> None:
    assert AgentType.CLAUDE == "CLAUDE"
    assert AgentType.CODEX == "CODEX"
    assert AgentType.GEMINI == "GEMINI"


def test_orchestration_mode_values() -> None:
    assert OrchestrationMode.SINGLE == "single"
    assert OrchestrationMode.PARALLEL == "parallel"
    assert OrchestrationMode.MULTI_MODEL == "multi_model"


# ------------------------------------------------------------------ #
#  Agent resolver tests                                              #
# ------------------------------------------------------------------ #


def _phases(assignments: list[AgentAssignment]) -> set[str]:
    return {a.phase for a in assignments}


def test_resolve_single_mode_all_claude() -> None:
    assignments = resolve_assignments(OrchestrationMode.SINGLE)
    assert len(assignments) == 5
    assert _phases(assignments) == {"PLAN", "EXEC", "TEST", "REVIEW", "MERGE"}
    assert all(a.agent == AgentType.CLAUDE for a in assignments)


def test_resolve_parallel_mode_uses_codex_for_exec() -> None:
    assignments = resolve_assignments(OrchestrationMode.PARALLEL)
    assert len(assignments) == 5
    exec_agent = next(a for a in assignments if a.phase == JobTaskType.EXEC)
    assert exec_agent.agent == AgentType.CODEX


def test_resolve_multi_model_uses_gemini_for_review() -> None:
    assignments = resolve_assignments(OrchestrationMode.MULTI_MODEL)
    assert len(assignments) == 5
    review_agent = next(a for a in assignments if a.phase == JobTaskType.REVIEW)
    assert review_agent.agent == AgentType.GEMINI


def test_resolve_assignments_returns_copy() -> None:
    a1 = resolve_assignments(OrchestrationMode.SINGLE)
    a2 = resolve_assignments(OrchestrationMode.SINGLE)
    assert a1 is not a2


def test_agent_assignment_model() -> None:
    a = AgentAssignment(phase=JobTaskType.PLAN, agent=AgentType.CLAUDE, role="lead")
    assert a.phase == JobTaskType.PLAN
    assert a.agent == AgentType.CLAUDE
    assert a.role == "lead"
