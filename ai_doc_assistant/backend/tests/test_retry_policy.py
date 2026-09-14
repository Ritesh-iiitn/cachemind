import pytest
from backend.app.workers.retry_policy import RetryPolicy


def test_transient_vs_permanent_classification():
    policy = RetryPolicy(max_attempts=3, base_backoff_seconds=2.0)

    # Transient exceptions
    assert policy.is_transient(TimeoutError("Connection timed out after 5000ms"))
    assert policy.is_transient(ConnectionError("Connection refused by peer"))
    assert policy.is_transient(RuntimeError("Temporary embedding service rate limit 503"))

    # Permanent exceptions
    assert not policy.is_transient(FileNotFoundError("File not found on disk"))
    assert not policy.is_transient(ValueError("Unsupported document format .xyz"))
    assert not policy.is_transient(TypeError("Invalid chunk parameter type"))
    assert not policy.is_transient(Exception("Corrupted PDF document header"))


def test_exponential_backoff_calculation():
    policy = RetryPolicy(base_backoff_seconds=2.0, max_backoff_seconds=30.0)

    # Attempt 1 -> 2.0s
    assert policy.calculate_backoff(1) == 2.0
    # Attempt 2 -> 4.0s
    assert policy.calculate_backoff(2) == 4.0
    # Attempt 3 -> 8.0s
    assert policy.calculate_backoff(3) == 8.0
    # Attempt 4 -> 16.0s
    assert policy.calculate_backoff(4) == 16.0
    # Attempt 5 -> capped at 30.0s
    assert policy.calculate_backoff(5) == 30.0


def test_should_retry_boundaries():
    policy = RetryPolicy(max_attempts=3, base_backoff_seconds=2.0)

    # Attempt 1: Transient -> Should retry with delay 2.0s
    should_retry, code, delay = policy.should_retry(1, TimeoutError("timed out"))
    assert should_retry is True
    assert "TRANSIENT" in code
    assert delay == 2.0

    # Attempt 3: Max attempt reached -> Should not retry
    should_retry, code, delay = policy.should_retry(3, TimeoutError("timed out"), configured_max=3)
    assert should_retry is False
    assert "MAX_ATTEMPTS_EXCEEDED" in code

    # Attempt 1: Permanent error -> Should not retry immediately
    should_retry, code, delay = policy.should_retry(1, FileNotFoundError("missing.pdf"))
    assert should_retry is False
    assert "PERMANENT_FAILURE" in code
    assert delay == 0.0
