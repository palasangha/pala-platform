"""Inline enrichment service - processes enrichment synchronously via MCP server"""
import asyncio
import json
import logging
import websockets
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class MCPEnrichmentClient:
    """Direct MCP server client for inline enrichment"""

    def __init__(self, mcp_url: str = "ws://mcp-server:3003"):
        """
        Initialize MCP enrichment client
        
        Args:
            mcp_url: WebSocket URL of MCP server (default: ws://mcp-server:3003)
        """
        self.mcp_url = mcp_url
        self.request_id_counter = 0

    def _get_next_request_id(self) -> str:
        """Generate unique request ID"""
        self.request_id_counter += 1
        return f"req-{self.request_id_counter}"

    async def invoke_tool(self, tool_name: str, arguments: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """
        Invoke a tool via MCP server
        
        Args:
            tool_name: Name of the tool to invoke
            arguments: Arguments to pass to the tool
            timeout: Request timeout in seconds (default: 30)
            
        Returns:
            Tool response or error dict
        """
        request_id = self._get_next_request_id()
        request = {
            "jsonrpc": "2.0",
            "method": "tools/invoke",
            "params": {
                "toolName": tool_name,
                "arguments": arguments
            },
            "id": request_id
        }

        try:
            logger.debug(f"Invoking tool: {tool_name} (timeout: {timeout}s)")
            async with websockets.connect(self.mcp_url) as websocket:
                # Send request
                await websocket.send(json.dumps(request))
                logger.debug(f"Tool request sent: {tool_name}")

                # Wait for response with timeout
                try:
                    response = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=timeout
                    )
                    response_data = json.loads(response)
                    logger.debug(f"Tool response received: {tool_name}")
                    logger.info(f"[MCP-DEBUG] {tool_name} response keys: {list(response_data.keys())}")
                    
                    if "error" in response_data:
                        logger.error(f"Tool error: {tool_name} - {response_data['error']}")
                        return {"success": False, "error": response_data["error"]}
                    
                    # Extract result - MCP returns nested structure: {"result": {"success": true, "result": {...}}}
                    outer_result = response_data.get("result", {})
                    # Get the actual data from the nested result field
                    actual_result = outer_result.get("result", {}) if isinstance(outer_result, dict) else {}
                    
                    logger.info(f"[MCP-DEBUG] {tool_name} extracted actual data keys: {list(actual_result.keys()) if isinstance(actual_result, dict) else 'not a dict'}")
                    
                    return {
                        "success": True,
                        "result": actual_result
                    }
                except asyncio.TimeoutError:
                    logger.error(f"Tool timeout: {tool_name} (>{timeout}s)")
                    return {"success": False, "error": f"Tool invocation timeout after {timeout}s"}

        except Exception as e:
            logger.error(f"Tool invocation failed: {tool_name} - {str(e)}")
            return {"success": False, "error": str(e)}

    async def enrich_document(self, ocr_text: str, filename: str = "document") -> Dict[str, Any]:
        """
        Enrich a single OCR document with metadata and analysis using all 21 MCP tools

        Args:
            ocr_text: OCR extracted text
            filename: Original filename

        Returns:
            Enriched data dictionary with all raw MCP responses
        """
        enriched_data = {
            "filename": filename,
            "ocr_text": ocr_text,
            "raw_mcp_responses": {},  # Store ALL raw MCP tool outputs
            "merged_result": {}  # Final merged result matching required-format.json
        }

        logger.info(f"Starting enrichment for: {filename} (calling all 21 MCP tools)")

        # =====================================================================
        # Phase 1: Metadata Extraction (metadata-agent - 4 tools)
        # =====================================================================
        logger.info("Phase 1: Extracting metadata (4 tools)...")

        # 1. Extract document type - Classify as letter/memo/telegram/fax/email/invitation
        doc_type_result = await self.invoke_tool(
            "extract_document_type",
            {"text": ocr_text[:5000]},
            timeout=30
        )
        enriched_data["raw_mcp_responses"]["extract_document_type"] = doc_type_result
        logger.info(f"extract_document_type result: {doc_type_result.get('success')}")

        # 2. Extract storage info - Extract archive, collection, box, folder info
        storage_info_result = await self.invoke_tool(
            "extract_storage_info",
            {"text": ocr_text[:3000]},
            timeout=30
        )
        enriched_data["raw_mcp_responses"]["extract_storage_info"] = storage_info_result
        logger.info(f"extract_storage_info result: {storage_info_result.get('success')}")

        # 3. Extract digitization metadata - Extract scan date, operator, equipment
        digitization_result = await self.invoke_tool(
            "extract_digitization_metadata",
            {"text": ocr_text[:3000]},
            timeout=30
        )
        enriched_data["raw_mcp_responses"]["extract_digitization_metadata"] = digitization_result
        logger.info(f"extract_digitization_metadata result: {digitization_result.get('success')}")

        # 4. Determine access level - Classify as public/restricted/private
        access_level_result = await self.invoke_tool(
            "determine_access_level",
            {"text": ocr_text[:5000]},
            timeout=30
        )
        enriched_data["raw_mcp_responses"]["determine_access_level"] = access_level_result
        logger.info(f"determine_access_level result: {access_level_result.get('success')}")

        # =====================================================================
        # Phase 2: Entity Extraction (entity-agent - 5 tools)
        # =====================================================================
        logger.info("Phase 2: Extracting entities (5 tools)...")

        # 5. Extract people - Extract person names with disambiguation
        people_result = await self.invoke_tool(
            "extract_people",
            {"text": ocr_text[:10000]},
            timeout=120
        )
        enriched_data["raw_mcp_responses"]["extract_people"] = people_result
        logger.info(f"extract_people result: {people_result.get('success')}")

        # 6. Extract organizations - Extract organizations/institutions
        organizations_result = await self.invoke_tool(
            "extract_organizations",
            {"text": ocr_text[:10000]},
            timeout=90
        )
        enriched_data["raw_mcp_responses"]["extract_organizations"] = organizations_result
        logger.info(f"extract_organizations result: {organizations_result.get('success')}")

        # 7. Extract locations - Extract geographic locations
        locations_result = await self.invoke_tool(
            "extract_locations",
            {"text": ocr_text[:10000]},
            timeout=90
        )
        enriched_data["raw_mcp_responses"]["extract_locations"] = locations_result
        logger.info(f"extract_locations result: {locations_result.get('success')}")

        # 8. Extract events - Extract historical events
        events_result = await self.invoke_tool(
            "extract_events",
            {"text": ocr_text[:10000]},
            timeout=90
        )
        enriched_data["raw_mcp_responses"]["extract_events"] = events_result
        logger.info(f"extract_events result: {events_result.get('success')}")

        # 9. Generate relationships - Map entity connections (depends on entities above)
        # Collect all entities for relationship generation
        all_entities = {
            "people": people_result.get("result", {}).get("people", []) if people_result.get("success") else [],
            "organizations": organizations_result.get("result", {}).get("organizations", []) if organizations_result.get("success") else [],
            "locations": locations_result.get("result", {}).get("locations", []) if locations_result.get("success") else [],
            "events": events_result.get("result", {}).get("events", []) if events_result.get("success") else []
        }

        relationships_result = await self.invoke_tool(
            "generate_relationships",
            {
                "text": ocr_text[:10000],
                "entities": all_entities
            },
            timeout=120
        )
        enriched_data["raw_mcp_responses"]["generate_relationships"] = relationships_result
        logger.info(f"generate_relationships result: {relationships_result.get('success')}")

        # =====================================================================
        # Phase 3: Structure Extraction (structure-agent - 6 tools)
        # =====================================================================
        logger.info("Phase 3: Extracting document structure (6 tools)...")

        # 10. Extract salutation - Extract greeting
        salutation_result = await self.invoke_tool(
            "extract_salutation",
            {"text": ocr_text[:2000]},
            timeout=60
        )
        enriched_data["raw_mcp_responses"]["extract_salutation"] = salutation_result
        logger.info(f"extract_salutation result: {salutation_result.get('success')}")

        # 11. Parse letter body - Parse body into paragraphs
        body_result = await self.invoke_tool(
            "parse_letter_body",
            {"text": ocr_text},
            timeout=180
        )
        enriched_data["raw_mcp_responses"]["parse_letter_body"] = body_result
        logger.info(f"parse_letter_body result: {body_result.get('success')}")

        # 12. Extract closing - Extract closing phrase
        closing_result = await self.invoke_tool(
            "extract_closing",
            {"text": ocr_text[-2000:] if len(ocr_text) > 2000 else ocr_text},
            timeout=60
        )
        enriched_data["raw_mcp_responses"]["extract_closing"] = closing_result
        logger.info(f"extract_closing result: {closing_result.get('success')}")

        # 13. Extract signature - Extract signature/signatory info
        signature_result = await self.invoke_tool(
            "extract_signature",
            {"text": ocr_text[-1000:] if len(ocr_text) > 1000 else ocr_text},
            timeout=60
        )
        enriched_data["raw_mcp_responses"]["extract_signature"] = signature_result
        logger.info(f"extract_signature result: {signature_result.get('success')}")

        # 14. Identify attachments - Detect mentioned attachments
        attachments_result = await self.invoke_tool(
            "identify_attachments",
            {"text": ocr_text},
            timeout=60
        )
        enriched_data["raw_mcp_responses"]["identify_attachments"] = attachments_result
        logger.info(f"identify_attachments result: {attachments_result.get('success')}")

        # 15. Parse correspondence - Extract sender/recipient/cc/date
        correspondence_result = await self.invoke_tool(
            "parse_correspondence",
            {"text": ocr_text[:3000]},
            timeout=90
        )
        enriched_data["raw_mcp_responses"]["parse_correspondence"] = correspondence_result
        logger.info(f"parse_correspondence result: {correspondence_result.get('success')}")

        # =====================================================================
        # Phase 4: Content Analysis (content-agent - 3 tools)
        # =====================================================================
        logger.info("Phase 4: Analyzing content (3 tools)...")

        # 16. Generate summary - Generate summary using Claude Sonnet
        summary_result = await self.invoke_tool(
            "generate_summary",
            {
                "text": ocr_text[:15000],
                "entities": all_entities
            },
            timeout=120
        )
        enriched_data["raw_mcp_responses"]["generate_summary"] = summary_result
        logger.info(f"generate_summary result: {summary_result.get('success')}")

        # 17. Extract keywords - Extract keywords
        keywords_result = await self.invoke_tool(
            "extract_keywords",
            {"text": ocr_text},
            timeout=90
        )
        enriched_data["raw_mcp_responses"]["extract_keywords"] = keywords_result
        logger.info(f"extract_keywords result: {keywords_result.get('success')}")

        # 18. Classify subjects - Classify by subject taxonomy
        subjects_result = await self.invoke_tool(
            "classify_subjects",
            {
                "text": ocr_text,
                "entities": all_entities
            },
            timeout=90
        )
        enriched_data["raw_mcp_responses"]["classify_subjects"] = subjects_result
        logger.info(f"classify_subjects result: {subjects_result.get('success')}")

        # =====================================================================
        # Phase 5: Historical Context (context-agent - 3 tools)
        # =====================================================================
        logger.info("Phase 5: Analyzing historical context (3 tools)...")

        # 19. Research historical context - Generate historical context
        context_result = await self.invoke_tool(
            "research_historical_context",
            {"text": ocr_text},
            timeout=120
        )
        enriched_data["raw_mcp_responses"]["research_historical_context"] = context_result
        logger.info(f"research_historical_context result: {context_result.get('success')}")

        # 20. Assess significance - Assess historical significance
        significance_result = await self.invoke_tool(
            "assess_significance",
            {"text": ocr_text},
            timeout=90
        )
        enriched_data["raw_mcp_responses"]["assess_significance"] = significance_result
        logger.info(f"assess_significance result: {significance_result.get('success')}")

        # 21. Generate biographies - Generate biographies for people (CRITICAL MISSING TOOL!)
        # Extract people list for biography generation
        people_list = people_result.get("result", {}).get("people", []) if people_result.get("success") else []

        biographies_result = await self.invoke_tool(
            "generate_biographies",
            {
                "people": people_list,
                "text": ocr_text
            },
            timeout=180
        )
        enriched_data["raw_mcp_responses"]["generate_biographies"] = biographies_result
        logger.info(f"generate_biographies result: {biographies_result.get('success')}")

        # =====================================================================
        # Merge all results into required-format.json structure
        # =====================================================================
        logger.info("Merging all MCP tool outputs into final result...")
        enriched_data["merged_result"] = self._merge_all_tool_outputs(enriched_data["raw_mcp_responses"])

        logger.info(f"Enrichment completed for: {filename} - All 21 tools called successfully")
        return enriched_data

    def _merge_all_tool_outputs(self, raw_responses: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge all raw MCP tool outputs into required-format.json structure

        Args:
            raw_responses: Dictionary of all raw MCP tool responses

        Returns:
            Merged result matching required-format.json schema
        """
        # Helper function to safely extract result data
        def get_result(tool_name: str, field: str = None):
            response = raw_responses.get(tool_name, {})
            if not response.get("success"):
                return {} if field is None else None
            result = response.get("result", {})
            return result.get(field) if field else result

        # Build merged result matching required-format.json
        merged = {
            "metadata": {
                "document_type": get_result("extract_document_type", "document_type") or "",
                "access_level": get_result("determine_access_level", "access_level") or "public",
                "storage_location": get_result("extract_storage_info") or {},
                "digitization_info": get_result("extract_digitization_metadata") or {}
            },
            "document": {
                "date": get_result("parse_correspondence", "date") or {},
                "correspondence": get_result("parse_correspondence") or {},
                "languages": ["en"],  # Default, could be enhanced
                "physical_attributes": {}  # Not extracted by current tools
            },
            "content": {
                "full_text": "",  # Will be filled from OCR
                "summary": get_result("generate_summary", "summary") or "",
                "salutation": get_result("extract_salutation", "salutation") or "",
                "body": get_result("parse_letter_body", "body") or [],
                "closing": get_result("extract_closing", "closing") or "",
                "signature": get_result("extract_signature", "signature") or "",
                "attachments": get_result("identify_attachments", "attachments") or [],
                "annotations": []  # Not extracted by current tools
            },
            "analysis": {
                "keywords": get_result("extract_keywords", "keywords") or [],
                "subjects": get_result("classify_subjects", "subjects") or [],
                "people": get_result("extract_people", "people") or [],
                "organizations": get_result("extract_organizations", "organizations") or [],
                "locations": get_result("extract_locations", "locations") or [],
                "events": get_result("extract_events", "events") or [],
                "historical_context": get_result("research_historical_context", "historical_context") or "",
                "significance": get_result("assess_significance", "assessment") or "",
                "relationships": get_result("generate_relationships", "relationships") or []
            }
        }

        # Enrich people with biographies
        biographies = get_result("generate_biographies", "biographies") or {}
        if biographies and isinstance(merged["analysis"]["people"], list):
            for person in merged["analysis"]["people"]:
                person_name = person.get("name", "")
                if person_name in biographies:
                    person["biography"] = biographies[person_name]

        # Enrich correspondence with biographies
        if merged["document"]["correspondence"]:
            sender = merged["document"]["correspondence"].get("sender", {})
            recipient = merged["document"]["correspondence"].get("recipient", {})

            if sender and sender.get("name") in biographies:
                sender["biography"] = biographies[sender["name"]]

            if recipient and recipient.get("name") in biographies:
                recipient["biography"] = biographies[recipient["name"]]

        return merged


class InlineEnrichmentService:
    """Service to process enrichment inline during OCR aggregation"""

    def __init__(self, mcp_url: str = "ws://mcp-server:3003"):
        """
        Initialize inline enrichment service
        
        Args:
            mcp_url: WebSocket URL of MCP server
        """
        self.mcp_client = MCPEnrichmentClient(mcp_url)

    def enrich_ocr_results(self, ocr_results: list, timeout: int = 900) -> Dict[str, Any]:
        """
        Enrich multiple OCR results synchronously
        
        Args:
            ocr_results: List of OCR result dictionaries
            timeout: Overall timeout in seconds (default: 900 = 15 min)
            
        Returns:
            Dictionary with enriched results and statistics
        """
        enriched_results = {}
        enrichment_stats = {
            "total_documents": len(ocr_results),
            "successful": 0,
            "failed": 0,
            "errors": [],
            "started_at": datetime.utcnow().isoformat(),
        }

        try:
            for i, ocr_result in enumerate(ocr_results, 1):
                filename = ocr_result.get("file") or ocr_result.get("filename", f"document_{i}")
                ocr_text = ocr_result.get("text", "")

                if not ocr_text:
                    logger.warning(f"Skipping {filename}: No OCR text")
                    enrichment_stats["failed"] += 1
                    enrichment_stats["errors"].append({"file": filename, "error": "No OCR text"})
                    continue

                try:
                    logger.info(f"Enriching document {i}/{len(ocr_results)}: {filename}")
                    
                    # Run async enrichment
                    enriched_data = asyncio.run(
                        self.mcp_client.enrich_document(ocr_text, filename)
                    )
                    
                    enriched_results[filename] = enriched_data
                    enrichment_stats["successful"] += 1
                    logger.info(f"Successfully enriched: {filename}")

                except Exception as e:
                    logger.error(f"Enrichment failed for {filename}: {str(e)}")
                    enrichment_stats["failed"] += 1
                    enrichment_stats["errors"].append({
                        "file": filename,
                        "error": str(e)
                    })
                    # Continue with next document instead of failing entire job
                    continue

        except Exception as e:
            logger.error(f"Enrichment service error: {str(e)}", exc_info=True)
            enrichment_stats["errors"].append({"service_error": str(e)})

        enrichment_stats["completed_at"] = datetime.utcnow().isoformat()
        
        return {
            "enriched_results": enriched_results,
            "statistics": enrichment_stats
        }


def get_inline_enrichment_service() -> InlineEnrichmentService:
    """Factory function to get enrichment service"""
    return InlineEnrichmentService()
