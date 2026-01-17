"""
Enrichment Service for OCR Data

This module provides AI-powered enrichment of OCR data using MCP agents.
Enriches historical documents to achieve 100% schema completeness.
"""

__version__ = "0.1.0"
__author__ = "Pala Platform"

from enrichment_service.mcp_client.client import MCPClient
from enrichment_service.workers.agent_orchestrator import AgentOrchestrator
from enrichment_service.schema.validator import HistoricalLettersValidator

__all__ = [
    'MCPClient',
    'AgentOrchestrator',
    'HistoricalLettersValidator',
]
