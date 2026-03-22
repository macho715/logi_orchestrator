from __future__ import annotations

from enum import StrEnum


class JobState(StrEnum):
    RECEIVED = "RECEIVED"
    VALIDATED = "VALIDATED"
    PLAN_RUNNING = "PLAN_RUNNING"
    PLAN_READY = "PLAN_READY"
    PLAN_APPROVAL_WAIT = "PLAN_APPROVAL_WAIT"
    FANOUT_QUEUED = "FANOUT_QUEUED"
    EXEC_RUNNING = "EXEC_RUNNING"
    TEST_RUNNING = "TEST_RUNNING"
    REVIEW_RUNNING = "REVIEW_RUNNING"
    MERGE_APPROVAL_WAIT = "MERGE_APPROVAL_WAIT"
    MERGING = "MERGING"
    DONE = "DONE"
    FAILED = "FAILED"
    PAUSED = "PAUSED"
    ABORTED = "ABORTED"


class JobEvent(StrEnum):
    VALIDATE_OK = "validate.ok"
    VALIDATE_FAIL = "validate.fail"
    PLAN_ENQUEUE = "plan.enqueue"
    PLAN_DONE = "plan.done"
    PLAN_FAIL = "plan.fail"
    REPORT_PLAN = "report.plan"
    APPROVE_PLAN = "approve.plan"
    EXEC_START = "exec.start"
    IMPL_DONE = "impl.done"
    EXEC_FAIL = "exec.fail"
    TESTS_DONE = "tests.done"
    TESTS_FAIL = "tests.fail"
    REVIEW_DONE = "review.done"
    REVIEW_FAIL = "review.fail"
    APPROVE_MERGE = "approve.merge"
    MERGE_OK = "merge.ok"
    MERGE_FAIL = "merge.fail"
    PAUSE = "pause"
    RESUME = "resume"
    ABORT = "abort"


class JobCommand(StrEnum):
    PROJECT_START = "project.start"
    STATUS = "status"
    APPROVE_PLAN = "approve.plan"
    APPROVE_MERGE = "approve.merge"
    REPORT = "report"
    ARTIFACTS = "artifacts"
    PAUSE = "pause"
    RESUME = "resume"
    ABORT = "abort"
    RETRY = "retry"


class ApprovalGate(StrEnum):
    PLAN_APPROVAL = "PLAN_APPROVAL"
    MERGE_APPROVAL = "MERGE_APPROVAL"


class JobTaskType(StrEnum):
    PLAN = "PLAN"
    EXEC = "EXEC"
    TEST = "TEST"
    REVIEW = "REVIEW"
    MERGE = "MERGE"
