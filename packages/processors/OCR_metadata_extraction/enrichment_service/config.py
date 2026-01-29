"""
Configuration management for Enrichment Service
"""

import os
from typing import Optional, Dict, Any


class EnrichmentConfig:
    """Central configuration for enrichment service"""

    # Service Configuration
    SERVICE_NAME = "enrichment-service"
    SERVICE_VERSION = "0.1.0"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # MCP Server Configuration
    MCP_ENABLED = os.getenv("MCP_ENABLED", "true").lower() == "true"
    MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "ws://mcp-server:3000")
    MCP_AGENT_TOKEN = os.getenv("MCP_AGENT_TOKEN", "")
    MCP_JWT_SECRET = os.getenv("MCP_JWT_SECRET", "")

    # MongoDB Configuration
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/gvpocr")
    MONGO_USERNAME = os.getenv("MONGO_USERNAME", "")
    MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "gvpocr")

    # NSQ Configuration
    NSQD_ADDRESS = os.getenv("NSQD_ADDRESS", "nsqd:4150")
    NSQLOOKUPD_ADDRESSES = os.getenv("NSQLOOKUPD_ADDRESSES", "nsqlookupd:4161")
    NSQ_ENRICHMENT_TOPIC = "enrichment"
    NSQ_ENRICHMENT_CHANNEL = "enrichment-workers"

    # Enrichment Configuration
    ENRICHMENT_ENABLED = os.getenv("ENRICHMENT_ENABLED", "true").lower() == "true"
    ENRICHMENT_BATCH_SIZE = int(os.getenv("ENRICHMENT_BATCH_SIZE", "50"))
    ENRICHMENT_REVIEW_THRESHOLD = float(os.getenv("ENRICHMENT_REVIEW_THRESHOLD", "0.95"))
    ENRICHMENT_AUTO_TRIGGER = os.getenv("ENRICHMENT_AUTO_TRIGGER", "true").lower() == "true"

    # AI Model Configuration
    ENRICHMENT_OLLAMA_MODEL = os.getenv("ENRICHMENT_OLLAMA_MODEL", "llama3.2")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")

    # Claude API Configuration
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL_OPUS = os.getenv("CLAUDE_MODEL_OPUS", "claude-opus-4-5-20251101")
    CLAUDE_MODEL_SONNET = os.getenv("CLAUDE_MODEL_SONNET", "claude-sonnet-4-20250514")
    CLAUDE_MODEL_HAIKU = os.getenv("CLAUDE_MODEL_HAIKU", "claude-haiku-4-5-20251001")

    # Cost Control Configuration
    MAX_COST_PER_DOC = float(os.getenv("MAX_COST_PER_DOC", "0.50"))
    DAILY_BUDGET_USD = float(os.getenv("DAILY_BUDGET_USD", "100.00"))
    COST_ALERT_THRESHOLD_USD = float(os.getenv("COST_ALERT_THRESHOLD_USD", "100.00"))
    MAX_CLAUDE_TOKENS_PER_DOC = int(os.getenv("MAX_CLAUDE_TOKENS_PER_DOC", "50000"))

    # Enrichment Feature Flags
    ENABLE_OLLAMA = os.getenv("ENABLE_OLLAMA", "true").lower() == "true"
    ENABLE_CLAUDE_HAIKU = os.getenv("ENABLE_CLAUDE_HAIKU", "true").lower() == "true"
    ENABLE_CLAUDE_SONNET = os.getenv("ENABLE_CLAUDE_SONNET", "true").lower() == "true"
    ENABLE_CLAUDE_OPUS = os.getenv("ENABLE_CLAUDE_OPUS", "true").lower() == "true"

    # Agent Configuration
    AGENT_TIMEOUT_SECONDS = int(os.getenv("AGENT_TIMEOUT_SECONDS", "60"))
    AGENT_RETRY_MAX = int(os.getenv("AGENT_RETRY_MAX", "3"))
    AGENT_RETRY_BACKOFF_BASE = int(os.getenv("AGENT_RETRY_BACKOFF_BASE", "2"))

    # Schema Configuration
    _default_schema_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "schema/historical_letters_schema.json"
    )
    SCHEMA_PATH = os.getenv(
        "SCHEMA_PATH",
        _default_schema_path if os.path.exists(_default_schema_path) else "/app/enrichment_service/schema/historical_letters_schema.json"
    )
    SCHEMA_VALIDATION_ENABLED = os.getenv("SCHEMA_VALIDATION_ENABLED", "true").lower() == "true"

    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "json")

    # Monitoring Configuration
    METRICS_ENABLED = os.getenv("METRICS_ENABLED", "true").lower() == "true"
    PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "9090"))

    @classmethod
    def validate(cls) -> Dict[str, Any]:
        """Validate configuration and return any warnings"""
        warnings = []

        if cls.MCP_ENABLED and not cls.MCP_SERVER_URL:
            warnings.append("MCP enabled but MCP_SERVER_URL not set")

        if not cls.ANTHROPIC_API_KEY and cls.ENABLE_CLAUDE_OPUS:
            warnings.append("Claude Opus enabled but ANTHROPIC_API_KEY not set")

        if not cls.MONGO_URI:
            warnings.append("MONGO_URI not configured")

        if not os.path.exists(cls.SCHEMA_PATH):
            warnings.append(f"Schema file not found at {cls.SCHEMA_PATH}")

        return {
            "status": "valid" if not warnings else "warnings",
            "warnings": warnings
        }

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "service_name": cls.SERVICE_NAME,
            "service_version": cls.SERVICE_VERSION,
            "debug": cls.DEBUG,
            "mcp_enabled": cls.MCP_ENABLED,
            "mcp_server_url": cls.MCP_SERVER_URL,
            "mongo_db": cls.MONGO_DB_NAME,
            "nsq_topic": cls.NSQ_ENRICHMENT_TOPIC,
            "enrichment_enabled": cls.ENRICHMENT_ENABLED,
            "batch_size": cls.ENRICHMENT_BATCH_SIZE,
            "review_threshold": cls.ENRICHMENT_REVIEW_THRESHOLD,
            "daily_budget_usd": cls.DAILY_BUDGET_USD,
            "log_level": cls.LOG_LEVEL,
        }


# Singleton instance
config = EnrichmentConfig()
