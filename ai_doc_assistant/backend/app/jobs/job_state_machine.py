import logging
from typing import Set, Dict
from backend.app.jobs.job_models import JobStatus

logger = logging.getLogger("cachemind.jobs.state_machine")


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal job state transition is attempted."""
    def __init__(self, from_state: JobStatus, to_state: JobStatus, reason: str = ""):
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason
        message = f"Invalid state transition from {from_state.value} to {to_state.value}"
        if reason:
            message += f" ({reason})"
        super().__init__(message)


class JobStateMachine:
    """
    Guarantees deterministic lifecycle transitions for document ingestion jobs.
    Prevents race conditions, zombie task revivals, and illegal completions.
    """

    # Standard execution transitions
    _ALLOWED_TRANSITIONS: Dict[JobStatus, Set[JobStatus]] = {
        JobStatus.QUEUED: {
            JobStatus.PROCESSING,
            JobStatus.CANCELLED
        },
        JobStatus.PROCESSING: {
            JobStatus.COMPLETED,
            JobStatus.RETRYING,
            JobStatus.FAILED,
            JobStatus.CANCELLED
        },
        JobStatus.RETRYING: {
            JobStatus.PROCESSING,
            JobStatus.FAILED,
            JobStatus.CANCELLED
        },
        JobStatus.COMPLETED: set(),  # Terminal state (immutable)
        JobStatus.FAILED: set(),     # Terminal state unless explicit retry requested
        JobStatus.CANCELLED: set()   # Terminal state unless explicit retry requested
    }

    # Explicit manual recovery transitions (invoked via retry endpoint)
    _ALLOWED_MANUAL_RETRY_TRANSITIONS: Dict[JobStatus, Set[JobStatus]] = {
        JobStatus.FAILED: {JobStatus.QUEUED},
        JobStatus.CANCELLED: {JobStatus.QUEUED},
        JobStatus.RETRYING: {JobStatus.QUEUED}
    }

    @classmethod
    def can_transition(
        cls,
        current_status: JobStatus,
        target_status: JobStatus,
        is_manual_retry: bool = False
    ) -> bool:
        """Check if transition is mathematically allowed."""
        if current_status == target_status:
            return True

        if is_manual_retry:
            allowed = cls._ALLOWED_MANUAL_RETRY_TRANSITIONS.get(current_status, set())
            return target_status in allowed

        allowed = cls._ALLOWED_TRANSITIONS.get(current_status, set())
        return target_status in allowed

    @classmethod
    def validate_transition(
        cls,
        current_status: JobStatus,
        target_status: JobStatus,
        is_manual_retry: bool = False
    ) -> None:
        """
        Validates transition and raises InvalidStateTransitionError if illegal.
        """
        if current_status == target_status:
            return

        if not cls.can_transition(current_status, target_status, is_manual_retry=is_manual_retry):
            logger.error(
                f"Rejected state transition: {current_status.value} -> {target_status.value} "
                f"(manual_retry={is_manual_retry})"
            )
            raise InvalidStateTransitionError(
                from_state=current_status,
                to_state=target_status,
                reason="Transition violates lifecycle state machine rules"
            )

    @classmethod
    def is_terminal(cls, status: JobStatus) -> bool:
        """Check if state is terminal without external intervention."""
        return status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}
