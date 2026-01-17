"""
Agent Orchestrator - Coordinates 5 MCP agents through 3-phase enrichment pipeline

Phase 1 (Parallel):
  - metadata-agent: Extract document type, storage info, digitization metadata
  - entity-agent: Extract people, organizations, locations, events
  - structure-agent: Parse letter structure (salutation, body, closing)

Phase 2 (Sequential):
  - content-agent: Generate summary, extract keywords, classify subjects
  (Depends on entities from Phase 1)

Phase 3 (Sequential):
  - context-agent: Research historical context, assess significance
  (Depends on all previous phases)

Phase 4 (Validation):
  - Schema validation and completeness checking
  - Route to human review if <95% completeness
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from enrichment_service.mcp_client.client import MCPClient, MCPInvocationError
from enrichment_service.schema.validator import HistoricalLettersValidator
from enrichment_service.config import config
from enrichment_service.utils.budget_manager import BudgetManager
from enrichment_service.utils.cost_tracker import CostTracker

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Orchestrates 3-phase enrichment pipeline with 5 MCP agents"""

    # Agent IDs
    METADATA_AGENT = "metadata-agent"
    ENTITY_AGENT = "entity-agent"
    STRUCTURE_AGENT = "structure-agent"
    CONTENT_AGENT = "content-agent"
    CONTEXT_AGENT = "context-agent"

    def __init__(self, mcp_client: Optional[MCPClient] = None, schema_path: Optional[str] = None, db=None):
        """
        Initialize orchestrator

        Args:
            mcp_client: MCP client instance
            schema_path: Path to schema JSON
            db: MongoDB database instance for cost tracking
        """
        self.mcp_client = mcp_client or MCPClient()
        self.schema_path = schema_path or config.SCHEMA_PATH
        self.validator = HistoricalLettersValidator(self.schema_path)

        # Cost tracking and budget management
        self.db = db
        self.budget_manager = BudgetManager(db)
        self.cost_tracker = CostTracker(db)

        # Track enrichment per document
        self.enrichment_id = str(uuid.uuid4())
        self.start_time: Optional[datetime] = None

    async def enrich_document(
        self,
        document_id: str,
        ocr_data: Dict[str, Any],
        collection_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enrich single document through 3-phase pipeline

        Args:
            document_id: Unique document ID
            ocr_data: Raw OCR extraction results
            collection_metadata: Optional collection context

        Returns:
            Enriched document with completeness metrics
        """
        self.start_time = datetime.utcnow()
        enrichment_start = datetime.utcnow()

        logger.info(f"Starting enrichment for document {document_id}")

        try:
            # Phase 1: Parallel extraction (free, fast)
            phase1_start = datetime.utcnow()
            phase1_results = await self._run_phase1(ocr_data)
            phase1_duration = (datetime.utcnow() - phase1_start).total_seconds() * 1000

            # Phase 2: Content analysis (Claude Sonnet)
            phase2_start = datetime.utcnow()
            phase2_results = await self._run_phase2(ocr_data, phase1_results)
            phase2_duration = (datetime.utcnow() - phase2_start).total_seconds() * 1000

            # Check budget before expensive Phase 3
            enable_context_agent = self.budget_manager.should_enable_context_agent()
            if not enable_context_agent:
                logger.info(f"Budget limit reached, skipping context agent for document {document_id}")

            # Phase 3: Historical context (Claude Opus) - optional based on budget
            phase3_start = datetime.utcnow()
            if enable_context_agent:
                phase3_results = await self._run_phase3(ocr_data, phase1_results, phase2_results)
            else:
                # Skip context agent, use empty results
                phase3_results = {'historical_context': '', 'significance': '', 'biographies': {}}
            phase3_duration = (datetime.utcnow() - phase3_start).total_seconds() * 1000

            # Merge results into target schema
            enriched_data = self._merge_results(phase1_results, phase2_results, phase3_results)

            # Validate and calculate completeness
            completeness = self.validator.calculate_completeness(enriched_data)

            # Build response
            enrichment_duration = (datetime.utcnow() - enrichment_start).total_seconds() * 1000

            return {
                "status": "success",
                "document_id": document_id,
                "enriched_data": enriched_data,
                "quality_metrics": {
                    "completeness_score": completeness["completeness_score"],
                    "missing_fields": completeness["missing_fields"],
                    "low_confidence_fields": completeness["low_confidence_fields"],
                    "passes_threshold": completeness["passes_threshold"]
                },
                "enrichment_metadata": {
                    "phase_1_duration_ms": phase1_duration,
                    "phase_2_duration_ms": phase2_duration,
                    "phase_3_duration_ms": phase3_duration,
                    "total_processing_time_ms": enrichment_duration,
                    "enrichment_id": self.enrichment_id,
                    "context_agent_enabled": enable_context_agent,
                    "budget_status": self.budget_manager.check_budget('daily') if self.budget_manager else None
                },
                "review_required": completeness["requires_review"],
                "review_reason": completeness["review_reason"] if completeness["requires_review"] else None
            }

        except Exception as e:
            logger.error(f"Enrichment failed for document {document_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "document_id": document_id,
                "error": str(e),
                "enrichment_id": self.enrichment_id
            }

    async def _run_phase1(self, ocr_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 1: Parallel extraction using Ollama (free, fast)

        Runs all 3 agents in parallel:
        - metadata-agent
        - entity-agent
        - structure-agent
        """
        logger.debug("Starting Phase 1 (parallel extraction)")

        # Prepare parameters for each agent
        tasks = [
            self._invoke_agent_with_fallback(
                self.METADATA_AGENT,
                "extract_document_type",
                {"text": ocr_data.get("text", "")}
            ),
            self._invoke_agent_with_fallback(
                self.ENTITY_AGENT,
                "extract_people",
                {"text": ocr_data.get("full_text", ocr_data.get("text", ""))}
            ),
            self._invoke_agent_with_fallback(
                self.STRUCTURE_AGENT,
                "parse_letter_body",
                {"text": ocr_data.get("full_text", ocr_data.get("text", ""))}
            )
        ]

        # Run in parallel with asyncio.gather
        metadata_result, entity_result, structure_result = await asyncio.gather(*tasks, return_exceptions=False)

        # Merge Phase 1 results
        return {
            "metadata": metadata_result or {},
            "entities": entity_result or {},
            "structure": structure_result or {},
            "phase": 1
        }

    async def _run_phase2(
        self,
        ocr_data: Dict[str, Any],
        phase1_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Phase 2: Content analysis using Claude (depends on Phase 1)

        Runs content-agent which needs entity extraction results
        """
        logger.debug("Starting Phase 2 (content analysis)")

        # Content agent needs entities to classify subjects properly
        entities = phase1_results.get("entities", {})

        try:
            summary = await self._invoke_agent_with_fallback(
                self.CONTENT_AGENT,
                "generate_summary",
                {
                    "text": ocr_data.get("full_text", ocr_data.get("text", "")),
                    "entities": entities
                }
            )

            keywords = await self._invoke_agent_with_fallback(
                self.CONTENT_AGENT,
                "extract_keywords",
                {"text": ocr_data.get("full_text", ocr_data.get("text", ""))}
            )

            subjects = await self._invoke_agent_with_fallback(
                self.CONTENT_AGENT,
                "classify_subjects",
                {
                    "text": ocr_data.get("full_text", ocr_data.get("text", "")),
                    "entities": entities
                }
            )

            return {
                "summary": summary or {},
                "keywords": keywords or {},
                "subjects": subjects or {},
                "phase": 2
            }

        except Exception as e:
            logger.error(f"Phase 2 error: {e}")
            return {"phase": 2, "error": str(e)}

    async def _run_phase3(
        self,
        ocr_data: Dict[str, Any],
        phase1_results: Dict[str, Any],
        phase2_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Phase 3: Historical context using Claude Opus (depends on all phases)

        Runs context-agent which uses highest quality model
        """
        logger.debug("Starting Phase 3 (historical context)")

        # Check if Claude Opus is enabled
        if not config.ENABLE_CLAUDE_OPUS:
            logger.info("Phase 3 skipped: Claude Opus disabled")
            return {"phase": 3, "skipped": True}

        # Prepare context for historical analysis
        entities = phase1_results.get("entities", {})
        people = entities.get("people", [])
        locations = entities.get("locations", [])
        events = entities.get("events", [])

        try:
            context = await self._invoke_agent_with_fallback(
                self.CONTEXT_AGENT,
                "research_historical_context",
                {
                    "text": ocr_data.get("text", ""),
                    "people": people,
                    "locations": locations,
                    "events": events,
                    "date": ocr_data.get("metadata", {}).get("date", "")
                }
            )

            significance = await self._invoke_agent_with_fallback(
                self.CONTEXT_AGENT,
                "assess_significance",
                {
                    "text": ocr_data.get("text", ""),
                    "context": context or {}
                }
            )

            return {
                "historical_context": context or {},
                "significance": significance or {},
                "phase": 3
            }

        except Exception as e:
            logger.error(f"Phase 3 error: {e}")
            return {"phase": 3, "error": str(e)}

    async def _invoke_agent_with_fallback(
        self,
        agent_id: str,
        tool_name: str,
        params: Dict[str, Any],
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Invoke agent tool with retry logic and fallback

        Args:
            agent_id: Agent to invoke
            tool_name: Tool to invoke
            params: Tool parameters
            max_retries: Max retry attempts

        Returns:
            Tool result or fallback empty dict
        """
        for attempt in range(max_retries):
            try:
                result = await self.mcp_client.invoke_tool(
                    agent_id=agent_id,
                    tool_name=tool_name,
                    arguments=params,
                    timeout=config.AGENT_TIMEOUT_SECONDS
                )
                logger.debug(f"Agent {agent_id} tool {tool_name} succeeded on attempt {attempt + 1}")
                return result

            except MCPInvocationError as e:
                logger.warning(f"Agent {agent_id} tool {tool_name} failed (attempt {attempt + 1}/{max_retries}): {e}")

                if attempt < max_retries - 1:
                    wait_time = config.AGENT_RETRY_BACKOFF_BASE ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Agent {agent_id} tool {tool_name} failed after {max_retries} attempts")
                    return self._get_fallback_result(agent_id, tool_name)

            except Exception as e:
                logger.error(f"Unexpected error invoking {agent_id}/{tool_name}: {e}")
                return self._get_fallback_result(agent_id, tool_name)

        return self._get_fallback_result(agent_id, tool_name)

    def _get_fallback_result(self, agent_id: str, tool_name: str) -> Dict[str, Any]:
        """
        Provide fallback result when agent fails

        Uses rule-based or empty extraction
        """
        logger.info(f"Using fallback for {agent_id}/{tool_name}")

        fallbacks = {
            ("metadata-agent", "extract_document_type"): {
                "document_type": "letter",
                "confidence": 0.5,
                "_fallback": True
            },
            ("entity-agent", "extract_people"): {
                "people": [],
                "_fallback": True
            },
            ("entity-agent", "extract_locations"): {
                "locations": [],
                "_fallback": True
            },
            ("structure-agent", "parse_letter_body"): {
                "body": [],
                "salutation": "",
                "closing": "",
                "_fallback": True
            },
            ("content-agent", "generate_summary"): {
                "summary": "Summary not available",
                "_fallback": True
            },
            ("context-agent", "research_historical_context"): {
                "historical_context": "Context not available",
                "_fallback": True
            }
        }

        return fallbacks.get((agent_id, tool_name), {"_fallback": True})

    def _merge_results(
        self,
        phase1: Dict[str, Any],
        phase2: Dict[str, Any],
        phase3: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge results from all 3 phases into target schema structure

        Target structure:
        {
            "metadata": {...},
            "document": {...},
            "content": {...},
            "analysis": {...}
        }
        """
        return {
            "metadata": {
                **phase1.get("metadata", {}),
                **phase1.get("structure", {}).get("metadata", {})
            },
            "document": {
                "languages": ["en"],  # TODO: Extract from OCR
                "physical_attributes": {},  # TODO: Extract from file metadata
                "correspondence": phase1.get("structure", {}).get("correspondence", {}),
                "date": {}  # TODO: Extract from content
            },
            "content": {
                "full_text": "",  # Populated from OCR
                "summary": phase2.get("summary", {}).get("summary", ""),
                "salutation": phase1.get("structure", {}).get("salutation", ""),
                "body": phase1.get("structure", {}).get("body", []),
                "closing": phase1.get("structure", {}).get("closing", ""),
                "signature": phase1.get("structure", {}).get("signature", ""),
                "attachments": [],
                "annotations": []
            },
            "analysis": {
                "keywords": phase2.get("keywords", {}).get("keywords", []),
                "subjects": phase2.get("subjects", {}).get("subjects", []),
                "people": phase1.get("entities", {}).get("people", []),
                "organizations": phase1.get("entities", {}).get("organizations", []),
                "locations": phase1.get("entities", {}).get("locations", []),
                "events": phase1.get("entities", {}).get("events", []),
                "historical_context": phase3.get("historical_context", {}).get("context", ""),
                "significance": phase3.get("significance", {}).get("significance", ""),
                "relationships": phase1.get("entities", {}).get("relationships", [])
            }
        }

    async def close(self) -> None:
        """Close MCP client connection"""
        await self.mcp_client.disconnect()
