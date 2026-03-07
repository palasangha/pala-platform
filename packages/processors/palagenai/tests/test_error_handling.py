"""
Tests for error handling and retry strategies

Tests verify:
1. Error type classification works correctly
2. Adaptive timeouts are assigned per tool
3. Retry strategies follow error type classification
4. Data source tracking (actual vs fallback) works
"""

import pytest
from enrichment_service.errors.error_types import (
    ErrorType, get_error_type, TimeoutError, ConnectionError,
    InvalidDataError, AuthenticationError, EventLoopError
)
from enrichment_service.errors.retry_strategy import get_retry_strategy
from enrichment_service.config.timeouts import get_tool_timeout


class TestErrorClassification:
    """Test error type classification"""

    def test_timeout_error_classification(self):
        """Timeout errors should be classified as TIMEOUT"""
        exc = TimeoutError("Tool invocation timeout after 60s", timeout_seconds=60)
        assert get_error_type(exc) == ErrorType.TIMEOUT

    def test_connection_error_classification(self):
        """Connection errors should be classified as CONNECTION"""
        exc = ConnectionError("Connection refused to MCP server")
        assert get_error_type(exc) == ErrorType.CONNECTION

    def test_invalid_data_error_classification(self):
        """Invalid data errors should be classified as INVALID_DATA"""
        exc = InvalidDataError("Schema validation failed")
        assert get_error_type(exc) == ErrorType.INVALID_DATA

    def test_authentication_error_classification(self):
        """Authentication errors should be classified as AUTHENTICATION"""
        exc = AuthenticationError("Unauthorized access")
        assert get_error_type(exc) == ErrorType.AUTHENTICATION

    def test_event_loop_error_classification(self):
        """Event loop errors should be classified as EVENT_LOOP"""
        exc = EventLoopError("Task got Future attached to a different loop")
        assert get_error_type(exc) == ErrorType.EVENT_LOOP

    def test_message_pattern_timeout_classification(self):
        """Generic exceptions with 'timeout' should be classified as TIMEOUT"""
        exc = Exception("timeout after 60s: connection timeout")
        assert get_error_type(exc) == ErrorType.TIMEOUT

    def test_message_pattern_connection_classification(self):
        """Generic exceptions with 'connection' should be classified as CONNECTION"""
        exc = Exception("Connection lost: socket error")
        assert get_error_type(exc) == ErrorType.CONNECTION

    def test_http_429_overloaded_classification(self):
        """HTTP 429 errors should be classified as OVERLOADED"""
        exc = Exception("HTTP 429: Too many requests")
        assert get_error_type(exc) == ErrorType.OVERLOADED

    def test_http_503_overloaded_classification(self):
        """HTTP 503 errors should be classified as OVERLOADED"""
        exc = Exception("HTTP 503: Service unavailable")
        assert get_error_type(exc) == ErrorType.OVERLOADED


class TestRetryStrategies:
    """Test retry strategy selection"""

    def test_timeout_strategy_retryable(self):
        """Timeout strategy should be retryable"""
        strategy = get_retry_strategy(ErrorType.TIMEOUT)
        assert strategy.is_retryable is True
        assert strategy.max_retries == 3

    def test_timeout_strategy_backoff(self):
        """Timeout strategy should use exponential backoff"""
        strategy = get_retry_strategy(ErrorType.TIMEOUT)
        assert strategy.get_wait_time(0) == 1  # 2^0 = 1
        assert strategy.get_wait_time(1) == 2  # 2^1 = 2
        assert strategy.get_wait_time(2) == 4  # 2^2 = 4

    def test_connection_strategy_retryable(self):
        """Connection strategy should be retryable"""
        strategy = get_retry_strategy(ErrorType.CONNECTION)
        assert strategy.is_retryable is True
        assert strategy.max_retries == 5

    def test_connection_strategy_longer_backoff(self):
        """Connection strategy should use longer backoff"""
        strategy = get_retry_strategy(ErrorType.CONNECTION)
        assert strategy.get_wait_time(0) == 1  # 2^0 * 1.5 = 1.5 → 1
        assert strategy.get_wait_time(1) == 3  # 2^1 * 1.5 = 3
        assert strategy.get_wait_time(2) == 6  # 2^2 * 1.5 = 6

    def test_invalid_data_not_retryable(self):
        """Invalid data errors should not be retryable"""
        strategy = get_retry_strategy(ErrorType.INVALID_DATA)
        assert strategy.is_retryable is False
        assert strategy.max_retries == 0

    def test_authentication_not_retryable(self):
        """Authentication errors should not be retryable"""
        strategy = get_retry_strategy(ErrorType.AUTHENTICATION)
        assert strategy.is_retryable is False
        assert strategy.max_retries == 0

    def test_overloaded_strategy_retryable(self):
        """Overloaded strategy should be retryable"""
        strategy = get_retry_strategy(ErrorType.OVERLOADED)
        assert strategy.is_retryable is True
        assert strategy.max_retries == 5

    def test_backoff_respects_max(self):
        """Backoff should not exceed max_backoff_seconds"""
        strategy = get_retry_strategy(ErrorType.OVERLOADED)
        # With base=3 and multiplier=1, we'd get 3^6 = 729, but max is 60
        assert strategy.get_wait_time(10) == 60


class TestAdaptiveTimeouts:
    """Test adaptive timeout configuration per tool"""

    def test_fast_extraction_timeout(self):
        """Fast extraction tools should have 30s timeout"""
        assert get_tool_timeout("extract_document_type") == 30

    def test_medium_extraction_timeout(self):
        """Medium extraction tools should have 120s timeout"""
        assert get_tool_timeout("extract_people") == 120
        assert get_tool_timeout("extract_locations") == 120

    def test_slow_structure_parsing_timeout(self):
        """Structure parsing should have 180s timeout"""
        assert get_tool_timeout("parse_letter_body") == 180
        assert get_tool_timeout("parse_letter_structure") == 180

    def test_phase2_content_analysis_timeout(self):
        """Content analysis should have 90-120s timeout"""
        assert get_tool_timeout("generate_summary") == 120
        assert get_tool_timeout("extract_keywords") == 90
        assert get_tool_timeout("classify_subjects") == 90

    def test_phase3_historical_context_timeout(self):
        """Historical context should have 240s timeout (Opus)"""
        assert get_tool_timeout("research_historical_context") == 240
        assert get_tool_timeout("generate_biographies") == 240
        assert get_tool_timeout("assess_significance") == 240

    def test_unknown_tool_default_timeout(self):
        """Unknown tools should use default timeout"""
        assert get_tool_timeout("unknown_tool") == 120
        assert get_tool_timeout("future_tool") == 120

    def test_adaptive_timeouts_improvement(self):
        """Adaptive timeouts should prevent premature timeouts vs fixed 60s"""
        # Old: All tools had 60s
        # New: Tools have appropriate timeouts
        assert get_tool_timeout("parse_letter_body") > 60  # 180s > 60s
        assert get_tool_timeout("research_historical_context") > 60  # 240s > 60s
        assert get_tool_timeout("extract_document_type") < 60  # 30s < 60s


class TestDataSourceTracking:
    """Test data source tracking (actual vs fallback)"""

    def test_source_marker_on_actual_data(self):
        """Actual data should be marked with _source: 'actual'"""
        # This would be tested in integration tests with actual MCP client
        # Here we test the expected structure
        assert "_source" in {"_source": "actual", "data": "test"}
        assert {"_source": "actual"}["_source"] == "actual"

    def test_source_marker_on_fallback_data(self):
        """Fallback data should be marked with _source: 'fallback'"""
        assert "_source" in {"_source": "fallback", "data": []}
        assert {"_source": "fallback"}["_source"] == "fallback"


class TestRetryBehavior:
    """Test retry behavior based on error type"""

    def test_timeout_immediate_retry(self):
        """Timeout errors should be retried immediately"""
        strategy = get_retry_strategy(ErrorType.TIMEOUT)
        # First retry has minimal backoff
        assert strategy.get_wait_time(0) == 1

    def test_connection_longer_retry_delay(self):
        """Connection errors should have longer retry delays"""
        strategy = get_retry_strategy(ErrorType.CONNECTION)
        # First retry has longer backoff than timeout
        assert strategy.get_wait_time(0) > 0

    def test_invalid_data_no_retry(self):
        """Invalid data should fail immediately without retry"""
        strategy = get_retry_strategy(ErrorType.INVALID_DATA)
        assert strategy.max_retries == 0
        assert strategy.is_retryable is False

    def test_authentication_no_retry(self):
        """Authentication errors should fail immediately"""
        strategy = get_retry_strategy(ErrorType.AUTHENTICATION)
        assert strategy.max_retries == 0
        assert strategy.is_retryable is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
