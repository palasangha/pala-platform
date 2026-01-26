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
        Enrich a single OCR document with metadata and analysis
        
        Args:
            ocr_text: OCR extracted text
            filename: Original filename
            
        Returns:
            Enriched data dictionary
        """
        enriched_data = {
            "filename": filename,
            "ocr_text": ocr_text,
            "raw_mcp_responses": {}
        }

        logger.info(f"Starting enrichment for: {filename}")

        # Phase 1: Metadata Extraction
        logger.info("Phase 1: Extracting metadata...")
        
        # Extract document type
        doc_type_result = await self.invoke_tool(
            "extract_document_type",
            {"text": ocr_text[:5000]},  # Limit text to first 5000 chars
            timeout=30
        )
        enriched_data["raw_mcp_responses"]["extract_document_type"] = doc_type_result
        logger.info(f"extract_document_type result: {doc_type_result.get('success')}")

        # Phase 2: Entity and Structure Extraction
        logger.info("Phase 2: Extracting entities and structure...")

        # Extract people
        people_result = await self.invoke_tool(
            "extract_people",
            {"text": ocr_text[:10000]},
            timeout=120
        )
        enriched_data["raw_mcp_responses"]["extract_people"] = people_result
        logger.info(f"extract_people result: {people_result.get('success')}")

        # Parse letter structure
        structure_result = await self.invoke_tool(
            "parse_letter_body",
            {"text": ocr_text},
            timeout=180
        )
        enriched_data["raw_mcp_responses"]["parse_letter_body"] = structure_result
        logger.info(f"parse_letter_body result: {structure_result.get('success')}")

        # Phase 3: Content Analysis
        logger.info("Phase 3: Analyzing content...")

        # Generate summary
        summary_result = await self.invoke_tool(
            "generate_summary",
            {"text": ocr_text[:15000]},
            timeout=120
        )
        enriched_data["raw_mcp_responses"]["generate_summary"] = summary_result
        logger.info(f"generate_summary result: {summary_result.get('success')}")

        # Extract keywords
        keywords_result = await self.invoke_tool(
            "extract_keywords",
            {"text": ocr_text},
            timeout=90
        )
        enriched_data["raw_mcp_responses"]["extract_keywords"] = keywords_result
        logger.info(f"extract_keywords result: {keywords_result.get('success')}")

        # Phase 4: Context and Significance
        logger.info("Phase 4: Analyzing context...")

        # Research historical context
        context_result = await self.invoke_tool(
            "research_historical_context",
            {"text": ocr_text},  # Remove metadata argument - tool doesn't accept it
            timeout=120
        )
        enriched_data["raw_mcp_responses"]["research_historical_context"] = context_result
        logger.info(f"research_historical_context result: {context_result.get('success')}")

        # Assess significance
        significance_result = await self.invoke_tool(
            "assess_significance",
            {"text": ocr_text},  # Only pass text - don't pass context
            timeout=90
        )
        enriched_data["raw_mcp_responses"]["assess_significance"] = significance_result
        logger.info(f"assess_significance result: {significance_result.get('success')}")

        logger.info(f"Enrichment completed for: {filename}")
        return enriched_data


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
