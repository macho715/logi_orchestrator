from __future__ import annotations

from app.core.enums import JobEvent, JobState
from app.core.exceptions import StateTransitionError

_TRANSITIONS: dict[JobState, dict[str, JobState]] = {
    JobState.RECEIVED: {
        JobEvent.VALIDATE_OK.value: JobState.VALIDATED,
        JobEvent.VALIDATE_FAIL.value: JobState.FAILED,
    },
    JobState.VALIDATED: {
        JobEvent.PLAN_ENQUEUE.value: JobState.PLAN_RUNNING,
    },
    JobState.PLAN_RUNNING: {
        JobEvent.PLAN_DONE.value: JobState.PLAN_READY,
        JobEvent.PLAN_FAIL.value: JobState.FAILED,
    },
    JobState.PLAN_READY: {
        JobEvent.REPORT_PLAN.value: JobState.PLAN_APPROVAL_WAIT,
    },
    JobState.PLAN_APPROVAL_WAIT: {
        JobEvent.APPROVE_PLAN.value: JobState.FANOUT_QUEUED,
        JobEvent.PAUSE.value: JobState.PAUSED,
        JobEvent.ABORT.value: JobState.ABORTED,
    },
    JobState.FANOUT_QUEUED: {
        JobEvent.EXEC_START.value: JobState.EXEC_RUNNING,
    },
    JobState.EXEC_RUNNING: {
        JobEvent.IMPL_DONE.value: JobState.TEST_RUNNING,
        JobEvent.EXEC_FAIL.value: JobState.FAILED,
        JobEvent.PAUSE.value: JobState.PAUSED,
    },
    JobState.TEST_RUNNING: {
        JobEvent.TESTS_DONE.value: JobState.REVIEW_RUNNING,
        JobEvent.TESTS_FAIL.value: JobState.FAILED,
        JobEvent.PAUSE.value: JobState.PAUSED,
    },
    JobState.REVIEW_RUNNING: {
        JobEvent.REVIEW_DONE.value: JobState.MERGE_APPROVAL_WAIT,
        JobEvent.REVIEW_FAIL.value: JobState.FAILED,
        JobEvent.PAUSE.value: JobState.PAUSED,
    },
    JobState.MERGE_APPROVAL_WAIT: {
        JobEvent.APPROVE_MERGE.value: JobState.MERGING,
        JobEvent.PAUSE.value: JobState.PAUSED,
        JobEvent.ABORT.value: JobState.ABORTED,
    },
    JobState.MERGING: {
        JobEvent.MERGE_OK.value: JobState.DONE,
        JobEvent.MERGE_FAIL.value: JobState.FAILED,
    },
    JobState.PAUSED: {
        "resume.plan_wait": JobState.PLAN_APPROVAL_WAIT,
        "resume.exec": JobState.EXEC_RUNNING,
        "resume.test": JobState.TEST_RUNNING,
        "resume.review": JobState.REVIEW_RUNNING,
        "resume.merge_wait": JobState.MERGE_APPROVAL_WAIT,
        JobEvent.ABORT.value: JobState.ABORTED,
    },
    JobState.FAILED: {
        "retry.exec": JobState.EXEC_RUNNING,
        "retry.test": JobState.TEST_RUNNING,
        "retry.review": JobState.REVIEW_RUNNING,
        JobEvent.ABORT.value: JobState.ABORTED,
    },
}


def transition(current: JobState, event: str) -> JobState:
    next_state = _TRANSITIONS.get(current, {}).get(event)
    if next_state is None:
        raise StateTransitionError(f"허용되지 않은 전이입니다: {current.value} -> {event}")
    return next_state


def resume_event_name(target: JobState | None) -> str:
    mapping = {
        JobState.PLAN_APPROVAL_WAIT: "resume.plan_wait",
        JobState.EXEC_RUNNING: "resume.exec",
        JobState.TEST_RUNNING: "resume.test",
        JobState.REVIEW_RUNNING: "resume.review",
        JobState.MERGE_APPROVAL_WAIT: "resume.merge_wait",
    }
    if target not in mapping:
        raise StateTransitionError("resume_target_state 가 올바르지 않습니다.")
    return mapping[target]
