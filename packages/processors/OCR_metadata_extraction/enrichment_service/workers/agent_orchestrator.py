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
from enrichment_service.errors.error_types import get_error_type, ErrorType
from enrichment_service.errors.retry_strategy import get_retry_strategy
from enrichment_service.config.timeouts import get_tool_timeout

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

            # Detect if OCR data contains structured extraction
            has_structured_ocr = 'structured_data' in ocr_data
            extraction_mode = ocr_data.get('extraction_mode', 'text_only')

            if has_structured_ocr:
                logger.info(f"OCR includes structured extraction (mode: {extraction_mode})")
                lmstudio_structured = ocr_data.get('structured_data', {})
                # Merge results with priority handling
                enriched_data = self._merge_results_with_ocr(
                    lmstudio_structured,
                    phase1_results,
                    phase2_results,
                    phase3_results
                )
            else:
                logger.info("OCR is text-only, using agent results only")
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

        # Run in parallel with asyncio.gather (return_exceptions=True to prevent pipeline halt)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Extract results and check for exceptions
        metadata_result = results[0] if not isinstance(results[0], Exception) else None
        entity_result = results[1] if not isinstance(results[1], Exception) else None
        structure_result = results[2] if not isinstance(results[2], Exception) else None

        # Log any agent failures
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                agent_names = [self.METADATA_AGENT, self.ENTITY_AGENT, self.STRUCTURE_AGENT]
                logger.warning(f"Phase 1 agent {agent_names[idx]} failed: {result}")

        # Pipeline continues even if individual agents fail (they have fallbacks)

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
        phase2_results = {"phase": 2, "summary": {}, "keywords": {}, "subjects": {}}

        try:
            # Generate summary with fallback
            summary = await self._invoke_agent_with_fallback(
                self.CONTENT_AGENT,
                "generate_summary",
                {
                    "text": ocr_data.get("full_text", ocr_data.get("text", "")),
                    "entities": entities
                }
            )
            phase2_results["summary"] = summary or {}
        except Exception as e:
            logger.error(f"Phase 2 summary generation failed: {e}", exc_info=True)
            phase2_results["summary"] = self._get_fallback_result(self.CONTENT_AGENT, "generate_summary")
            phase2_results["summary_error"] = str(e)

        try:
            # Extract keywords with fallback
            keywords = await self._invoke_agent_with_fallback(
                self.CONTENT_AGENT,
                "extract_keywords",
                {"text": ocr_data.get("full_text", ocr_data.get("text", ""))}
            )
            phase2_results["keywords"] = keywords or {}
        except Exception as e:
            logger.error(f"Phase 2 keyword extraction failed: {e}", exc_info=True)
            phase2_results["keywords"] = self._get_fallback_result(self.CONTENT_AGENT, "extract_keywords")
            phase2_results["keywords_error"] = str(e)

        try:
            # Classify subjects with fallback
            subjects = await self._invoke_agent_with_fallback(
                self.CONTENT_AGENT,
                "classify_subjects",
                {
                    "text": ocr_data.get("full_text", ocr_data.get("text", "")),
                    "entities": entities
                }
            )
            phase2_results["subjects"] = subjects or {}
        except Exception as e:
            logger.error(f"Phase 2 subject classification failed: {e}", exc_info=True)
            phase2_results["subjects"] = self._get_fallback_result(self.CONTENT_AGENT, "classify_subjects")
            phase2_results["subjects_error"] = str(e)

        return phase2_results

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
            return {"phase": 3, "skipped": True, "historical_context": "", "significance": ""}

        # Prepare context for historical analysis
        entities = phase1_results.get("entities", {})
        people = entities.get("people", [])
        locations = entities.get("locations", [])
        events = entities.get("events", [])

        phase3_results = {
            "phase": 3,
            "historical_context": "",
            "significance": ""
        }

        try:
            # Research historical context with fallback
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
            phase3_results["historical_context"] = context or {}
        except Exception as e:
            logger.error(f"Phase 3 historical context failed: {e}", exc_info=True)
            phase3_results["historical_context"] = self._get_fallback_result(self.CONTEXT_AGENT, "research_historical_context")
            phase3_results["context_error"] = str(e)

        try:
            # Assess significance with fallback
            significance = await self._invoke_agent_with_fallback(
                self.CONTEXT_AGENT,
                "assess_significance",
                {
                    "text": ocr_data.get("text", ""),
                    "context": phase3_results["historical_context"] or {}
                }
            )
            phase3_results["significance"] = significance or {}
        except Exception as e:
            logger.error(f"Phase 3 significance assessment failed: {e}", exc_info=True)
            phase3_results["significance"] = self._get_fallback_result(self.CONTEXT_AGENT, "assess_significance")
            phase3_results["significance_error"] = str(e)

        return phase3_results

    async def _invoke_agent_with_fallback(
        self,
        agent_id: str,
        tool_name: str,
        params: Dict[str, Any],
        max_retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Invoke agent tool with adaptive timeout and error-based retry logic

        Args:
            agent_id: Agent to invoke
            tool_name: Tool to invoke
            params: Tool parameters
            max_retries: Max retry attempts (if None, determined by error type)

        Returns:
            Tool result or fallback empty dict with _source indicator
        """
        # Get adaptive timeout for this tool
        timeout_seconds = get_tool_timeout(tool_name)

        # Classify error and get retry strategy
        last_error = None
        attempt = 0

        while True:
            try:
                logger.debug(f"Invoking {agent_id}/{tool_name} (attempt {attempt + 1}, timeout: {timeout_seconds}s)")
                result = await self.mcp_client.invoke_tool(
                    agent_id=agent_id,
                    tool_name=tool_name,
                    arguments=params,
                    timeout=timeout_seconds
                )
                logger.debug(f"Agent {agent_id} tool {tool_name} succeeded on attempt {attempt + 1}")
                result["_source"] = "actual"
                return result

            except Exception as e:
                last_error = e
                error_type = get_error_type(e)
                retry_strategy = get_retry_strategy(error_type)

                logger.warning(
                    f"Agent {agent_id} tool {tool_name} failed with {error_type.value}: {e} "
                    f"(attempt {attempt + 1}/{retry_strategy.max_retries + 1})"
                )

                # Check if we should retry
                if not retry_strategy.is_retryable or attempt >= retry_strategy.max_retries:
                    logger.error(
                        f"Agent {agent_id} tool {tool_name} failed after {attempt + 1} attempts "
                        f"({error_type.value}): {e}"
                    )
                    return self._get_fallback_result(agent_id, tool_name)

                # Calculate backoff and retry
                attempt += 1
                wait_time = retry_strategy.get_wait_time(attempt - 1)
                logger.info(f"Retrying in {wait_time}s (strategy: {retry_strategy.description})")
                await asyncio.sleep(wait_time)

    def _get_fallback_result(self, agent_id: str, tool_name: str) -> Dict[str, Any]:
        """
        Provide fallback result when agent fails

        Uses rule-based or empty extraction, marked with _source: fallback
        """
        logger.info(f"Using fallback for {agent_id}/{tool_name}")

        fallbacks = {
            ("metadata-agent", "extract_document_type"): {
                "document_type": "letter",
                "confidence": 0.5,
                "_source": "fallback"
            },
            ("entity-agent", "extract_people"): {
                "people": [],
                "_source": "fallback"
            },
            ("entity-agent", "extract_locations"): {
                "locations": [],
                "_source": "fallback"
            },
            ("structure-agent", "parse_letter_body"): {
                "body": [],
                "salutation": "",
                "closing": "",
                "_source": "fallback"
            },
            ("content-agent", "generate_summary"): {
                "summary": "Summary not available",
                "_source": "fallback"
            },
            ("context-agent", "research_historical_context"): {
                "historical_context": "Context not available",
                "_source": "fallback"
            }
        }

        return fallbacks.get((agent_id, tool_name), {"_source": "fallback"})

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

    def _merge_results_with_ocr(
        self,
        lmstudio_data: Dict[str, Any],
        phase1: Dict[str, Any],
        phase2: Dict[str, Any],
        phase3: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge LM Studio structured data with enrichment agent results

        Priority:
        - LM Studio: visible fields (dates, sender/recipient names, structure)
        - Agents: knowledge-based fields (biographies, context, analysis)
        """
        logger.debug("Merging LM Studio structured data with enrichment results")

        # Start with agent results
        merged = self._merge_results(phase1, phase2, phase3)

        if not lmstudio_data:
            logger.debug("No structured OCR data, returning agent results only")
            return merged

        # Merge document section - LM Studio priority for visible fields
        if 'document' in lmstudio_data:
            lm_doc = lmstudio_data['document']

            # Date - LM Studio priority (visible in image)
            if lm_doc.get('date'):
                merged['document']['date'] = lm_doc['date']
                logger.debug("Applied LM Studio date extraction")

            # Languages - LM Studio priority (detectable from text)
            if lm_doc.get('languages'):
                merged['document']['languages'] = lm_doc['languages']
                logger.debug("Applied LM Studio language detection")

            # Physical attributes - LM Studio priority (visible)
            if lm_doc.get('physical_attributes'):
                if 'physical_attributes' not in merged['document']:
                    merged['document']['physical_attributes'] = {}
                for key, value in lm_doc['physical_attributes'].items():
                    if value:  # Only use non-empty values
                        merged['document']['physical_attributes'][key] = value
                logger.debug("Applied LM Studio physical attributes")

            # Correspondence - MERGE both sources
            if lm_doc.get('correspondence'):
                if 'correspondence' not in merged['document']:
                    merged['document']['correspondence'] = {}

                lm_corr = lm_doc['correspondence']
                merged_corr = merged['document']['correspondence']

                # Sender: LM Studio (name, location, contact), agents (biography)
                if lm_corr.get('sender'):
                    if 'sender' not in merged_corr:
                        merged_corr['sender'] = {}
                    for field in ['name', 'location', 'contact_info', 'affiliation']:
                        if lm_corr['sender'].get(field):
                            merged_corr['sender'][field] = lm_corr['sender'][field]
                    logger.debug("Applied LM Studio sender information")

                # Recipient: similar logic
                if lm_corr.get('recipient'):
                    if 'recipient' not in merged_corr:
                        merged_corr['recipient'] = {}
                    for field in ['name', 'location', 'contact_info', 'affiliation']:
                        if lm_corr['recipient'].get(field):
                            merged_corr['recipient'][field] = lm_corr['recipient'][field]
                    logger.debug("Applied LM Studio recipient information")

        # Merge content section - LM Studio priority for visible structure
        if 'content' in lmstudio_data:
            lm_content = lmstudio_data['content']

            # LM Studio has priority for structure fields (visible in image)
            for field in ['full_text', 'salutation', 'body', 'closing', 'signature']:
                if lm_content.get(field):
                    merged['content'][field] = lm_content[field]
            logger.debug("Applied LM Studio content structure")

        # Metadata section - system fields, not from LM Studio
        # Analysis section - agents only (knowledge-based, not visible in image)

        logger.info("Successfully merged LM Studio structured data with enrichment results")
        return merged

    async def close(self) -> None:
        """Close MCP client connection"""
        await self.mcp_client.disconnect()
