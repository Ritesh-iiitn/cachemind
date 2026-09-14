import logging
from typing import Tuple, Type, Set

logger = logging.getLogger("cachemind.workers.retry_policy")


class RetryPolicy:
    """
    Classifies errors into transient vs. permanent and computes exponential backoff delays.
    Prevents endless loops on invalid documents while ensuring resiliency against network hiccups.
    """

    # Transient error signatures (retryable)
    TRANSIENT_EXCEPTIONS: Set[str] = {
        "TimeoutError",
        "ConnectionError",
        "RedisError",
        "OperationalError",  # SQLite database locked or busy
        "HTTPError",
        "RateLimitError",
        "ServiceUnavailableError",
        "EmbeddingServiceError"
    }

    # Permanent error signatures (non-retryable)
    PERMANENT_EXCEPTIONS: Set[str] = {
        "FileNotFoundError",
        "ValueError",
        "KeyError",
        "TypeError",
        "UnsupportedFileError",
        "CorruptedDocumentError",
        "InvalidStateTransitionError",
        "PermissionError"
    }

    def __init__(self, max_attempts: int = 3, base_backoff_seconds: float = 2.0, max_backoff_seconds: float = 30.0):
        self.max_attempts = max_attempts
        self.base_backoff_seconds = base_backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds

    def is_transient(self, exc: Exception) -> bool:
        """
        Determines whether the exception is classified as transient.
        """
        exc_type = type(exc).__name__
        msg = str(exc).lower()

        # Check explicit type names
        if exc_type in self.TRANSIENT_EXCEPTIONS:
            return True
        if exc_type in self.PERMANENT_EXCEPTIONS:
            return False

        # Keyword heuristics for external service or transient failures
        transient_keywords = [
            "timeout", "timed out", "connection reset", "connection refused",
            "busy", "locked", "too many requests", "rate limit", "503", "502", "504",
            "temporary", "unavailable"
        ]
        if any(kw in msg for kw in transient_keywords):
            return True

        permanent_keywords = [
            "corrupt", "unsupported", "invalid format", "not found", "cannot parse",
            "no such file", "magic number", "malformed"
        ]
        if any(kw in msg for kw in permanent_keywords):
            return False

        # Default: treat unexpected system/runtime errors as transient unless max retries reached
        return True

    def calculate_backoff(self, attempt: int) -> float:
        """
        Computes exponential backoff delay:
        Attempt 1: base (2.0s)
        Attempt 2: base * 2 = 4.0s
        Attempt 3: base * 4 = 8.0s
        """
        delay = self.base_backoff_seconds * (2 ** max(0, attempt - 1))
        return min(self.max_backoff_seconds, delay)

    def should_retry(self, attempt: int, exc: Exception, configured_max: int = 3) -> Tuple[bool, str, float]:
        """
        Returns (should_retry, error_code, delay_seconds).
        """
        max_att = configured_max or self.max_attempts
        exc_name = type(exc).__name__

        if attempt >= max_att:
            return False, f"MAX_ATTEMPTS_EXCEEDED_{exc_name}", 0.0

        if not self.is_transient(exc):
            return False, f"PERMANENT_FAILURE_{exc_name}", 0.0

        delay = self.calculate_backoff(attempt)
        return True, f"TRANSIENT_{exc_name}", delay


default_retry_policy = RetryPolicy()
