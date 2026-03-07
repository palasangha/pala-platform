"""Retry strategy based on error type"""

from dataclasses import dataclass
from typing import Optional

from enrichment_service.errors.error_types import ErrorType


@dataclass
class RetryStrategy:
    """Configuration for retrying based on error type"""

    max_retries: int
    backoff_base: int
    backoff_multiplier: float = 1.0
    max_backoff_seconds: int = 300
    is_retryable: bool = True
    description: str = ""

    def get_wait_time(self, attempt: int) -> int:
        """
        Calculate wait time for a given retry attempt

        Args:
            attempt: Zero-indexed retry attempt number (0, 1, 2, ...)

        Returns:
            Wait time in seconds
        """
        wait_time = int(self.backoff_base ** attempt * self.backoff_multiplier)
        return min(wait_time, self.max_backoff_seconds)


# Retry strategies per error type
RETRY_STRATEGIES = {
    ErrorType.TIMEOUT: RetryStrategy(
        max_retries=3,
        backoff_base=2,
        backoff_multiplier=1.0,
        max_backoff_seconds=10,
        is_retryable=True,
        description="Timeout - retry with exponential backoff (2s, 4s, 8s)"
    ),
    ErrorType.CONNECTION: RetryStrategy(
        max_retries=5,
        backoff_base=2,
        backoff_multiplier=1.5,
        max_backoff_seconds=30,
        is_retryable=True,
        description="Connection error - retry with longer backoff (1.5s, 3s, 6s, 12s, 24s)"
    ),
    ErrorType.OVERLOADED: RetryStrategy(
        max_retries=5,
        backoff_base=3,
        backoff_multiplier=1.0,
        max_backoff_seconds=60,
        is_retryable=True,
        description="Service overloaded - retry with longer backoff (3s, 9s, 27s, 81s)"
    ),
    ErrorType.INVALID_DATA: RetryStrategy(
        max_retries=0,
        backoff_base=1,
        is_retryable=False,
        description="Invalid data - fail immediately, no retry"
    ),
    ErrorType.AUTHENTICATION: RetryStrategy(
        max_retries=0,
        backoff_base=1,
        is_retryable=False,
        description="Authentication failed - fail immediately, no retry"
    ),
    ErrorType.EVENT_LOOP: RetryStrategy(
        max_retries=1,
        backoff_base=2,
        backoff_multiplier=0.5,
        max_backoff_seconds=5,
        is_retryable=True,
        description="Event loop conflict - single retry with short backoff (0.5s)"
    ),
    ErrorType.UNKNOWN: RetryStrategy(
        max_retries=2,
        backoff_base=2,
        backoff_multiplier=1.0,
        max_backoff_seconds=10,
        is_retryable=True,
        description="Unknown error - conservative retry with exponential backoff"
    ),
}


def get_retry_strategy(error_type: ErrorType) -> RetryStrategy:
    """
    Get retry strategy for an error type

    Args:
        error_type: The ErrorType to get strategy for

    Returns:
        RetryStrategy configuration
    """
    return RETRY_STRATEGIES.get(error_type, RETRY_STRATEGIES[ErrorType.UNKNOWN])
