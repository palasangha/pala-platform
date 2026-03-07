"""
Prometheus Metrics - Real-time monitoring of enrichment pipeline

Exports metrics for Prometheus scraping and Grafana visualization
"""

import logging
import time
from typing import Optional, Dict, Any
from prometheus_client import Counter, Histogram, Gauge, start_http_server

logger = logging.getLogger(__name__)

# ===================== Throughput Metrics =====================

documents_enriched_total = Counter(
    'enrichment_documents_total',
    'Total documents enriched',
    ['status'],  # success, error, review_required
    registry=None  # Will be set properly
)

enrichment_duration_seconds = Histogram(
    'enrichment_duration_seconds',
    'Time to enrich single document in seconds',
    ['phase'],  # phase1, phase2, phase3, total
    buckets=(0.5, 1, 2, 5, 10, 30, 60, 300),  # 0.5s to 5min
    registry=None
)

# ===================== Quality Metrics =====================

completeness_score = Histogram(
    'enrichment_completeness_score',
    'Distribution of document completeness scores (0-1)',
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0],
    registry=None
)

review_queue_size = Gauge(
    'enrichment_review_queue_size',
    'Number of documents pending human review',
    registry=None
)

missing_fields_distribution = Histogram(
    'enrichment_missing_fields',
    'Distribution of missing required fields per document',
    buckets=[0, 1, 2, 5, 10, 20],
    registry=None
)

# ===================== Cost Metrics =====================

claude_api_cost_usd = Counter(
    'enrichment_claude_cost_usd_total',
    'Total Claude API cost in USD',
    ['model'],  # opus, sonnet, haiku
    registry=None
)

ollama_calls_total = Counter(
    'enrichment_ollama_calls_total',
    'Total Ollama API calls (free)',
    ['model'],  # llama3.2, mixtral
    registry=None
)

api_tokens_total = Counter(
    'enrichment_api_tokens_total',
    'Total API tokens used',
    ['model', 'direction'],  # direction: input, output
    registry=None
)

daily_spend_usd = Gauge(
    'enrichment_daily_spend_usd',
    'Current daily spending in USD',
    registry=None
)

budget_remaining_usd = Gauge(
    'enrichment_budget_remaining_usd',
    'Remaining daily budget in USD',
    registry=None
)

budget_percentage_used = Gauge(
    'enrichment_budget_percentage_used',
    'Percentage of daily budget used (0-100)',
    registry=None
)

# ===================== Agent Health Metrics =====================

agent_availability = Gauge(
    'enrichment_agent_available',
    'Agent availability (1=available, 0=unavailable)',
    ['agent_id'],
    registry=None
)

agent_response_time_seconds = Histogram(
    'enrichment_agent_response_seconds',
    'Agent response time in seconds',
    ['agent_id', 'tool_name'],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30),
    registry=None
)

agent_errors_total = Counter(
    'enrichment_agent_errors_total',
    'Total agent errors',
    ['agent_id', 'error_type'],  # timeout, connection, validation, etc.
    registry=None
)

# ===================== Processing Metrics =====================

processing_queue_size = Gauge(
    'enrichment_processing_queue_size',
    'Number of documents in enrichment queue',
    registry=None
)

processing_throughput = Gauge(
    'enrichment_throughput_docs_per_hour',
    'Document processing throughput (docs/hour)',
    registry=None
)

ocr_confidence_score = Histogram(
    'enrichment_ocr_confidence',
    'Distribution of OCR confidence scores',
    buckets=[0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.99],
    registry=None
)

# ===================== MCP Communication Metrics =====================

mcp_requests_total = Counter(
    'enrichment_mcp_requests_total',
    'Total MCP requests',
    ['agent_id', 'tool_name', 'status'],  # status: success, timeout, error
    registry=None
)

mcp_response_time_seconds = Histogram(
    'enrichment_mcp_response_seconds',
    'MCP response time in seconds',
    ['agent_id', 'tool_name'],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30),
    registry=None
)

mcp_connection_pool_size = Gauge(
    'enrichment_mcp_pool_size',
    'Size of MCP connection pool',
    registry=None
)

# ===================== Database Metrics =====================

mongodb_operations_total = Counter(
    'enrichment_mongodb_operations_total',
    'Total MongoDB operations',
    ['operation', 'collection'],  # operation: insert, update, find, etc.
    registry=None
)

mongodb_operation_time_seconds = Histogram(
    'enrichment_mongodb_operation_seconds',
    'MongoDB operation time in seconds',
    ['operation', 'collection'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1, 5),
    registry=None
)

# ===================== NSQ Metrics =====================

nsq_messages_published = Counter(
    'enrichment_nsq_messages_published',
    'Messages published to NSQ',
    ['topic'],
    registry=None
)

nsq_messages_consumed = Counter(
    'enrichment_nsq_messages_consumed',
    'Messages consumed from NSQ',
    ['topic', 'status'],  # status: success, error, requeue
    registry=None
)

nsq_message_processing_time = Histogram(
    'enrichment_nsq_processing_seconds',
    'NSQ message processing time in seconds',
    ['topic'],
    buckets=(1, 5, 10, 30, 60, 300),
    registry=None
)


class MetricsRecorder:
    """Helper class to record metrics"""

    @staticmethod
    def record_document_enrichment(
        status: str,
        duration_seconds: float,
        completeness_score: float,
        missing_fields: int,
        ocr_confidence: float,
        cost_usd: float = 0.0
    ):
        """
        Record metrics for enriched document

        Args:
            status: 'success', 'error', or 'review_required'
            duration_seconds: Total enrichment time
            completeness_score: Final completeness (0-1)
            missing_fields: Number of missing required fields
            ocr_confidence: Original OCR confidence (0-1)
            cost_usd: Cost of enrichment
        """
        documents_enriched_total.labels(status=status).inc()
        enrichment_duration_seconds.labels(phase='total').observe(duration_seconds)
        completeness_score.observe(completeness_score)
        missing_fields_distribution.observe(missing_fields)
        ocr_confidence_score.observe(ocr_confidence)

        if cost_usd > 0:
            daily_spend_usd.set(daily_spend_usd._value + cost_usd if hasattr(daily_spend_usd, '_value') else cost_usd)

    @staticmethod
    def record_phase_duration(phase: str, duration_seconds: float):
        """Record phase-specific duration"""
        enrichment_duration_seconds.labels(phase=phase).observe(duration_seconds)

    @staticmethod
    def record_agent_call(
        agent_id: str,
        tool_name: str,
        duration_seconds: float,
        success: bool,
        error_type: Optional[str] = None
    ):
        """
        Record MCP agent call metrics

        Args:
            agent_id: Agent identifier
            tool_name: Tool name
            duration_seconds: Response time
            success: Whether call succeeded
            error_type: Type of error if failed
        """
        status = 'success' if success else 'error'
        mcp_requests_total.labels(agent_id=agent_id, tool_name=tool_name, status=status).inc()
        mcp_response_time_seconds.labels(agent_id=agent_id, tool_name=tool_name).observe(duration_seconds)

        if not success and error_type:
            agent_errors_total.labels(agent_id=agent_id, error_type=error_type).inc()

    @staticmethod
    def record_api_cost(model: str, cost_usd: float, input_tokens: int, output_tokens: int):
        """
        Record Claude API cost

        Args:
            model: Model name (claude-opus, etc.)
            cost_usd: Cost in USD
            input_tokens: Input tokens used
            output_tokens: Output tokens used
        """
        if model.startswith('claude'):
            model_short = model.split('-')[-1]  # Get 'opus', 'sonnet', 'haiku'
            claude_api_cost_usd.labels(model=model_short).inc(cost_usd)
            api_tokens_total.labels(model=model_short, direction='input').inc(input_tokens)
            api_tokens_total.labels(model=model_short, direction='output').inc(output_tokens)
        elif model == 'ollama':
            ollama_calls_total.labels(model='ollama').inc()

    @staticmethod
    def record_review_queue_change(size: int):
        """Record review queue size"""
        review_queue_size.set(size)

    @staticmethod
    def set_budget_metrics(daily_spend: float, daily_budget: float):
        """Update budget metrics"""
        daily_spend_usd.set(daily_spend)
        budget_remaining_usd.set(max(0, daily_budget - daily_spend))
        percentage = (daily_spend / daily_budget * 100) if daily_budget > 0 else 0
        budget_percentage_used.set(min(percentage, 100))

    @staticmethod
    def set_agent_availability(agent_id: str, available: bool):
        """Update agent availability"""
        agent_availability.labels(agent_id=agent_id).set(1 if available else 0)

    @staticmethod
    def record_mongodb_operation(
        operation: str,
        collection: str,
        duration_seconds: float,
        success: bool = True
    ):
        """
        Record MongoDB operation

        Args:
            operation: insert, update, find, delete, etc.
            collection: Collection name
            duration_seconds: Operation time
            success: Whether operation succeeded
        """
        if success:
            mongodb_operations_total.labels(operation=operation, collection=collection).inc()
            mongodb_operation_time_seconds.labels(operation=operation, collection=collection).observe(duration_seconds)

    @staticmethod
    def record_nsq_publish(topic: str):
        """Record NSQ publish"""
        nsq_messages_published.labels(topic=topic).inc()

    @staticmethod
    def record_nsq_consume(topic: str, status: str, duration_seconds: float):
        """
        Record NSQ consumption

        Args:
            topic: Topic name
            status: success, error, requeue
            duration_seconds: Processing time
        """
        nsq_messages_consumed.labels(topic=topic, status=status).inc()
        nsq_message_processing_time.labels(topic=topic).observe(duration_seconds)


def start_metrics_server(port: int = 8000):
    """
    Start Prometheus metrics HTTP server

    Args:
        port: Port to serve metrics on
    """
    try:
        start_http_server(port)
        logger.info(f"Prometheus metrics server started on port {port}")
        logger.info(f"Metrics available at http://localhost:{port}/metrics")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")


class MetricsContextManager:
    """Context manager for recording operation duration"""

    def __init__(self, metric_func, labels: Dict[str, str] = None):
        """
        Initialize context manager

        Args:
            metric_func: Histogram metric function (e.g., mcp_response_time_seconds.labels(...).observe)
            labels: Labels dict to pass to metric
        """
        self.metric = metric_func
        self.labels = labels or {}
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        try:
            if self.labels:
                self.metric.labels(**self.labels).observe(duration)
            else:
                self.metric.observe(duration)
        except Exception as e:
            logger.error(f"Error recording metric: {e}")
