from app.core.enums import JobEvent, JobState
from app.services.state_machine import transition


def test_plan_transition() -> None:
    assert transition(JobState.RECEIVED, JobEvent.VALIDATE_OK.value) == JobState.VALIDATED
    assert transition(JobState.VALIDATED, JobEvent.PLAN_ENQUEUE.value) == JobState.PLAN_RUNNING
