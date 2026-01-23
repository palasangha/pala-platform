"""Error handling and classification for enrichment service"""

from enrichment_service.errors.error_types import (
    ErrorType,
    EnrichmentError,
    TimeoutError,
    ConnectionError,
    InvalidDataError,
    AuthenticationError,
    OverloadedError,
    get_error_type
)
from enrichment_service.errors.retry_strategy import (
    RetryStrategy,
    get_retry_strategy
)

__all__ = [
    'ErrorType',
    'EnrichmentError',
    'TimeoutError',
    'ConnectionError',
    'InvalidDataError',
    'AuthenticationError',
    'OverloadedError',
    'get_error_type',
    'RetryStrategy',
    'get_retry_strategy'
]
