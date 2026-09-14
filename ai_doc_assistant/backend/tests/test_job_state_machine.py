import pytest
from backend.app.jobs.job_models import JobStatus
from backend.app.jobs.job_state_machine import JobStateMachine, InvalidStateTransitionError


def test_valid_transitions():
    # QUEUED -> PROCESSING
    assert JobStateMachine.can_transition(JobStatus.QUEUED, JobStatus.PROCESSING)
    JobStateMachine.validate_transition(JobStatus.QUEUED, JobStatus.PROCESSING)

    # PROCESSING -> COMPLETED
    assert JobStateMachine.can_transition(JobStatus.PROCESSING, JobStatus.COMPLETED)
    JobStateMachine.validate_transition(JobStatus.PROCESSING, JobStatus.COMPLETED)

    # PROCESSING -> RETRYING
    assert JobStateMachine.can_transition(JobStatus.PROCESSING, JobStatus.RETRYING)
    JobStateMachine.validate_transition(JobStatus.PROCESSING, JobStatus.RETRYING)

    # RETRYING -> PROCESSING
    assert JobStateMachine.can_transition(JobStatus.RETRYING, JobStatus.PROCESSING)
    JobStateMachine.validate_transition(JobStatus.RETRYING, JobStatus.PROCESSING)

    # RETRYING -> FAILED
    assert JobStateMachine.can_transition(JobStatus.RETRYING, JobStatus.FAILED)
    JobStateMachine.validate_transition(JobStatus.RETRYING, JobStatus.FAILED)

    # QUEUED -> CANCELLED
    assert JobStateMachine.can_transition(JobStatus.QUEUED, JobStatus.CANCELLED)
    JobStateMachine.validate_transition(JobStatus.QUEUED, JobStatus.CANCELLED)

    # Self transitions (idempotent)
    assert JobStateMachine.can_transition(JobStatus.PROCESSING, JobStatus.PROCESSING)


def test_invalid_transitions():
    # COMPLETED -> PROCESSING is strictly prohibited
    assert not JobStateMachine.can_transition(JobStatus.COMPLETED, JobStatus.PROCESSING)
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        JobStateMachine.validate_transition(JobStatus.COMPLETED, JobStatus.PROCESSING)
    assert "Invalid state transition from COMPLETED to PROCESSING" in str(exc_info.value)

    # FAILED -> COMPLETED is prohibited without retry
    assert not JobStateMachine.can_transition(JobStatus.FAILED, JobStatus.COMPLETED)
    with pytest.raises(InvalidStateTransitionError):
        JobStateMachine.validate_transition(JobStatus.FAILED, JobStatus.COMPLETED)

    # COMPLETED -> FAILED
    assert not JobStateMachine.can_transition(JobStatus.COMPLETED, JobStatus.FAILED)
    with pytest.raises(InvalidStateTransitionError):
        JobStateMachine.validate_transition(JobStatus.COMPLETED, JobStatus.FAILED)


def test_manual_retry_transitions():
    # FAILED -> QUEUED (manual retry)
    assert JobStateMachine.can_transition(JobStatus.FAILED, JobStatus.QUEUED, is_manual_retry=True)
    JobStateMachine.validate_transition(JobStatus.FAILED, JobStatus.QUEUED, is_manual_retry=True)

    # CANCELLED -> QUEUED (manual retry)
    assert JobStateMachine.can_transition(JobStatus.CANCELLED, JobStatus.QUEUED, is_manual_retry=True)
    JobStateMachine.validate_transition(JobStatus.CANCELLED, JobStatus.QUEUED, is_manual_retry=True)

    # COMPLETED -> QUEUED should still fail even with manual retry flag
    assert not JobStateMachine.can_transition(JobStatus.COMPLETED, JobStatus.QUEUED, is_manual_retry=True)


def test_terminal_states():
    assert JobStateMachine.is_terminal(JobStatus.COMPLETED)
    assert JobStateMachine.is_terminal(JobStatus.FAILED)
    assert JobStateMachine.is_terminal(JobStatus.CANCELLED)
    assert not JobStateMachine.is_terminal(JobStatus.QUEUED)
    assert not JobStateMachine.is_terminal(JobStatus.PROCESSING)
    assert not JobStateMachine.is_terminal(JobStatus.RETRYING)
