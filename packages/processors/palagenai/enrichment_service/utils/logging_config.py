"""
Logging configuration for enrichment service

Provides:
- Structured JSON logging with context injection
- File rotation with 30-day retention
- Console output for Docker log collection
- Success/error event filtering
- Correlation ID and context tracking
"""

import logging
import logging.handlers
import json
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

try:
    from pythonjsonlogger import jsonlogger
except ImportError:
    jsonlogger = None


class ContextAwareFormatter(logging.Formatter):
    """
    Custom formatter that injects context variables into log records
    Supports both JSON and plain text formatting
    """

    def __init__(self, fmt=None, datefmt=None, use_json=True):
        """
        Initialize formatter

        Args:
            fmt: Format string (ignored if use_json=True)
            datefmt: Date format string
            use_json: Whether to use JSON formatting
        """
        super().__init__(fmt, datefmt)
        self.use_json = use_json

        if use_json and jsonlogger:
            self.json_formatter = jsonlogger.JsonFormatter()
        else:
            self.json_formatter = None

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with context injection

        Args:
            record: Log record to format

        Returns:
            Formatted log string
        """
        # Add timestamp
        record.timestamp = datetime.utcnow().isoformat()

        # Add context from thread-local storage if available
        if hasattr(record, '_context'):
            context = record._context
            record.enrichment_id = context.get('enrichment_id', '')
            record.job_id = context.get('job_id', '')
            record.document_id = context.get('document_id', '')
            record.correlation_id = context.get('correlation_id', '')
        else:
            record.enrichment_id = getattr(record, 'enrichment_id', '')
            record.job_id = getattr(record, 'job_id', '')
            record.document_id = getattr(record, 'document_id', '')
            record.correlation_id = getattr(record, 'correlation_id', '')

        # Use JSON formatter if available
        if self.use_json and self.json_formatter:
            return self.json_formatter.format(record)

        # Plain text formatting
        timestamp = record.timestamp
        level = record.levelname
        name = record.name
        message = record.getMessage()

        # Add context to message if available
        context_parts = []
        if record.correlation_id:
            context_parts.append(f"correlation_id={record.correlation_id}")
        if record.job_id:
            context_parts.append(f"job_id={record.job_id}")
        if record.document_id:
            context_parts.append(f"document_id={record.document_id}")

        context_str = " [" + " ".join(context_parts) + "]" if context_parts else ""

        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            return f"{timestamp} {level:8s} {name:40s} {message}{context_str}\n{exc_text}"

        return f"{timestamp} {level:8s} {name:40s} {message}{context_str}"


class SuccessErrorFilter(logging.Filter):
    """
    Filter for routing success/error events to separate logs
    """

    def __init__(self, event_type: str = 'all'):
        """
        Initialize filter

        Args:
            event_type: 'success', 'error', or 'all'
        """
        super().__init__()
        self.event_type = event_type

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log records by event type

        Args:
            record: Log record to check

        Returns:
            True if record should be logged
        """
        if self.event_type == 'all':
            return True

        # Check for success indicators
        success_indicators = ['✓', 'completed', 'success', 'passed', 'saved']
        is_success = any(
            indicator in record.getMessage().lower()
            for indicator in success_indicators
        )

        if self.event_type == 'success':
            return is_success
        elif self.event_type == 'error':
            return record.levelno >= logging.ERROR or not is_success
        else:
            return True


class ContextInjector:
    """
    Helper class for injecting context into log records
    """

    # Thread-local storage for context
    _context = {}

    @classmethod
    def set_context(cls, enrichment_id: str = '', job_id: str = '',
                   document_id: str = '', correlation_id: str = '') -> None:
        """
        Set context for current processing

        Args:
            enrichment_id: Enrichment operation ID
            job_id: Enrichment job ID
            document_id: Document being processed
            correlation_id: Request correlation ID
        """
        cls._context = {
            'enrichment_id': enrichment_id,
            'job_id': job_id,
            'document_id': document_id,
            'correlation_id': correlation_id
        }

    @classmethod
    def clear_context(cls) -> None:
        """Clear context"""
        cls._context = {}

    @classmethod
    def get_context(cls) -> Dict[str, str]:
        """Get current context"""
        return cls._context.copy()


def setup_logging(
    level: str = 'INFO',
    log_file: Optional[str] = None,
    service_name: str = 'enrichment_service',
    enable_json: bool = True,
    log_dir: Optional[str] = None,
    retention_days: int = 30
) -> logging.Logger:
    """
    Configure logging for enrichment service

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path (default: based on log_dir)
        service_name: Service name for logger
        enable_json: Whether to use JSON formatting
        log_dir: Directory for log files (default: ./logs)
        retention_days: Days to retain log files

    Returns:
        Configured logger instance
    """
    # Create logs directory if needed
    if log_dir is None:
        log_dir = os.path.join(os.getcwd(), 'logs')

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler (stdout for Docker)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    console_formatter = ContextAwareFormatter(use_json=enable_json)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation
    if log_file is None:
        log_file = os.path.join(log_dir, f'{service_name}.log')

    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when='midnight',
        interval=1,
        backupCount=retention_days,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    file_formatter = ContextAwareFormatter(use_json=enable_json)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Separate success/error event log
    events_log_file = os.path.join(log_dir, f'{service_name}-events.log')
    events_handler = logging.handlers.TimedRotatingFileHandler(
        events_log_file,
        when='midnight',
        interval=1,
        backupCount=retention_days,
        encoding='utf-8'
    )
    events_handler.setLevel(logging.INFO)
    events_handler.addFilter(SuccessErrorFilter(event_type='all'))
    events_formatter = ContextAwareFormatter(use_json=enable_json)
    events_handler.setFormatter(events_formatter)
    root_logger.addHandler(events_handler)

    # Get service logger
    service_logger = logging.getLogger(service_name)
    service_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Log startup
    service_logger.info(
        f"Logging configured: level={level}, json={enable_json}, "
        f"log_file={log_file}, log_dir={log_dir}"
    )

    return service_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def inject_context(enrichment_id: str = '', job_id: str = '',
                   document_id: str = '', correlation_id: str = ''):
    """
    Decorator to inject context into logger calls

    Args:
        enrichment_id: Enrichment operation ID
        job_id: Enrichment job ID
        document_id: Document being processed
        correlation_id: Request correlation ID

    Returns:
        Decorator function
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            ContextInjector.set_context(
                enrichment_id=enrichment_id,
                job_id=job_id,
                document_id=document_id,
                correlation_id=correlation_id
            )
            try:
                return await func(*args, **kwargs)
            finally:
                ContextInjector.clear_context()

        def sync_wrapper(*args, **kwargs):
            ContextInjector.set_context(
                enrichment_id=enrichment_id,
                job_id=job_id,
                document_id=document_id,
                correlation_id=correlation_id
            )
            try:
                return func(*args, **kwargs)
            finally:
                ContextInjector.clear_context()

        # Return appropriate wrapper based on function type
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x100:
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
