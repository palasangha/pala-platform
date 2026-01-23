"""Error type classification for enrichment service"""

from enum import Enum
from typing import Type


class ErrorType(Enum):
    """Classification of error types for retry decisions"""
    TIMEOUT = "timeout"  # Tool exceeded time limit
    CONNECTION = "connection"  # Network/connection issue
    INVALID_DATA = "invalid_data"  # Data validation failed
    AUTHENTICATION = "authentication"  # Auth/permission failed
    OVERLOADED = "overloaded"  # Service overloaded (429, 503)
    EVENT_LOOP = "event_loop"  # Async event loop conflict
    UNKNOWN = "unknown"  # Unknown error type


class EnrichmentError(Exception):
    """Base enrichment error with type classification"""

    def __init__(self, message: str, error_type: ErrorType = ErrorType.UNKNOWN):
        super().__init__(message)
        self.error_type = error_type
        self.message = message


class TimeoutError(EnrichmentError):
    """Error raised when tool invocation exceeds timeout"""

    def __init__(self, message: str, timeout_seconds: int = 0):
        super().__init__(message, ErrorType.TIMEOUT)
        self.timeout_seconds = timeout_seconds


class ConnectionError(EnrichmentError):
    """Error raised for network/connection issues"""

    def __init__(self, message: str):
        super().__init__(message, ErrorType.CONNECTION)


class InvalidDataError(EnrichmentError):
    """Error raised for invalid or malformed data"""

    def __init__(self, message: str):
        super().__init__(message, ErrorType.INVALID_DATA)


class AuthenticationError(EnrichmentError):
    """Error raised for authentication/authorization failures"""

    def __init__(self, message: str):
        super().__init__(message, ErrorType.AUTHENTICATION)


class OverloadedError(EnrichmentError):
    """Error raised when service is overloaded (429, 503)"""

    def __init__(self, message: str, retry_after_seconds: int = 0):
        super().__init__(message, ErrorType.OVERLOADED)
        self.retry_after_seconds = retry_after_seconds


class EventLoopError(EnrichmentError):
    """Error raised for async event loop conflicts"""

    def __init__(self, message: str):
        super().__init__(message, ErrorType.EVENT_LOOP)


def get_error_type(exception: Exception) -> ErrorType:
    """
    Classify an exception into an ErrorType

    Args:
        exception: The exception to classify

    Returns:
        ErrorType classification
    """
    message = str(exception).lower()
    error_type_name = type(exception).__name__.lower()

    # Check message patterns first
    if "timeout" in message:
        return ErrorType.TIMEOUT

    if any(pattern in message for pattern in ["connection", "socket", "host", "network", "refused"]):
        return ErrorType.CONNECTION

    if any(pattern in message for pattern in ["unauthorized", "permission", "forbidden"]):
        return ErrorType.AUTHENTICATION

    if "event" in message and "loop" in message:
        return ErrorType.EVENT_LOOP

    if any(pattern in message for pattern in ["429", "503", "overload"]):
        return ErrorType.OVERLOADED

    if any(pattern in message for pattern in ["invalid", "malformed", "parse", "schema"]):
        return ErrorType.INVALID_DATA

    # Check exception type
    if error_type_name == "asyncio.timeouterror":
        return ErrorType.TIMEOUT

    if "connection" in error_type_name:
        return ErrorType.CONNECTION

    if "auth" in error_type_name:
        return ErrorType.AUTHENTICATION

    return ErrorType.UNKNOWN
