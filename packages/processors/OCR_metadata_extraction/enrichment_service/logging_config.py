"""
Centralized logging configuration for all enrichment services

Provides structured logging with:
- Console output for real-time monitoring
- File rotation for long-term storage
- JSON formatting for log aggregation
- Different log levels for different components
"""

import logging
import logging.config
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path


def setup_logging(
    service_name: str,
    log_level: str = None,
    log_dir: str = None,
    enable_file: bool = True,
    enable_console: bool = True,
    json_format: bool = False
) -> logging.Logger:
    """
    Setup comprehensive logging configuration

    Args:
        service_name: Name of the service (e.g., 'enrichment-coordinator', 'enrichment-worker')
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        enable_file: Whether to log to files
        enable_console: Whether to log to console
        json_format: Whether to use JSON format for logs

    Returns:
        Configured logger instance
    """

    # Get log level from env or parameter
    log_level = log_level or os.getenv('LOG_LEVEL', 'INFO')
    log_level = getattr(logging, log_level.upper(), logging.INFO)

    # Set up log directory
    if log_dir is None:
        log_dir = os.getenv('LOG_DIR', '/app/logs')

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Format strings
    detailed_format = (
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s'
    )
    simple_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Console handler (always enabled for Docker)
    if enable_console or True:  # Force console for Docker
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        if json_format:
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(detailed_format)

        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler (rotating)
    if enable_file:
        log_file = log_path / f"{service_name}.log"

        # Rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=10  # Keep 10 backups
        )
        file_handler.setLevel(log_level)

        if json_format:
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(detailed_format)

        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        print(f"Logging to file: {log_file}", file=sys.stderr)

    return root_logger


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        import json

        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add custom fields if present
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


# Service-specific logger configurations
def get_coordinator_logger(service_name: str = 'enrichment-coordinator') -> logging.Logger:
    """Get logger for enrichment coordinator"""
    logger = setup_logging(
        service_name=service_name,
        log_level=os.getenv('COORDINATOR_LOG_LEVEL', 'INFO')
    )
    return logger.getChild('coordinator')


def get_worker_logger(service_name: str = 'enrichment-worker') -> logging.Logger:
    """Get logger for enrichment worker"""
    logger = setup_logging(
        service_name=service_name,
        log_level=os.getenv('WORKER_LOG_LEVEL', 'INFO')
    )
    return logger.getChild('worker')


def get_review_api_logger(service_name: str = 'review-api') -> logging.Logger:
    """Get logger for review API"""
    logger = setup_logging(
        service_name=service_name,
        log_level=os.getenv('REVIEW_API_LOG_LEVEL', 'INFO')
    )
    return logger.getChild('review_api')


def get_cost_api_logger(service_name: str = 'cost-api') -> logging.Logger:
    """Get logger for cost API"""
    logger = setup_logging(
        service_name=service_name,
        log_level=os.getenv('COST_API_LOG_LEVEL', 'INFO')
    )
    return logger.getChild('cost_api')


def log_operation(logger: logging.Logger, operation: str, **kwargs) -> None:
    """
    Log an operation with structured data

    Args:
        logger: Logger instance
        operation: Operation name
        **kwargs: Additional fields to log
    """
    message = f"[{operation}] {' | '.join(f'{k}={v}' for k, v in kwargs.items())}"
    logger.info(message)


def log_error(logger: logging.Logger, operation: str, error: Exception, **kwargs) -> None:
    """
    Log an error with context

    Args:
        logger: Logger instance
        operation: Operation name
        error: Exception instance
        **kwargs: Additional context fields
    """
    context = ' | '.join(f'{k}={v}' for k, v in kwargs.items())
    message = f"[{operation}] ERROR: {str(error)} | {context}" if context else f"[{operation}] ERROR: {str(error)}"
    logger.error(message, exc_info=True)


def log_debug_data(logger: logging.Logger, operation: str, data: dict, prefix: str = "DEBUG") -> None:
    """
    Log debug data (structured)

    Args:
        logger: Logger instance
        operation: Operation name
        data: Dictionary of data to log
        prefix: Prefix for the log message
    """
    import json

    try:
        data_str = json.dumps(data, default=str, indent=2)
    except:
        data_str = str(data)

    logger.debug(f"[{prefix}] {operation}: {data_str}")


# Configure loggers for each service at module load time
_coordinator_logger = None
_worker_logger = None
_review_api_logger = None
_cost_api_logger = None


def initialize_all_loggers():
    """Initialize all service loggers"""
    global _coordinator_logger, _worker_logger, _review_api_logger, _cost_api_logger

    _coordinator_logger = get_coordinator_logger()
    _worker_logger = get_worker_logger()
    _review_api_logger = get_review_api_logger()
    _cost_api_logger = get_cost_api_logger()

    return {
        'coordinator': _coordinator_logger,
        'worker': _worker_logger,
        'review_api': _review_api_logger,
        'cost_api': _cost_api_logger,
    }
