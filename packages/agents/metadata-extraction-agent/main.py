#!/usr/bin/env python3
"""
Metadata Extraction Agent

Stateless AI-powered agent for extracting structured metadata from OCR text.
Supports multiple output schemas (Pala, Archipelago Commons) via MCP.

Provider: Claude (with extensible interface for future providers)
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
import websockets
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from providers.base_provider import BaseMetadataProvider
from providers.claude_provider import ClaudeMetadataProvider
from providers.ollama_provider import OllamaMetadataProvider
from mappers.pala_mapper import PalaMapper
from mappers.archipelago_mapper import ArchipelagoMapper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def make_request(method: str, params: Dict[str, Any], request_id: str) -> str:
    """Create JSON-RPC 2.0 request"""
    return json.dumps(
        {"jsonrpc": "2.0", "method": method, "params": params, "id": request_id}
    )


def make_response(result: Dict[str, Any], request_id: str) -> str:
    """Create JSON-RPC 2.0 response"""
    return json.dumps({"jsonrpc": "2.0", "result": result, "id": request_id})


def make_error(code: int, message: str, request_id: str) -> str:
    """Create JSON-RPC 2.0 error response"""
    return json.dumps(
        {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": request_id}
    )


class MetadataExtractionAgent:
    """Agent for extracting structured metadata from OCR text"""

    def __init__(self):
        """Initialize metadata extraction agent"""
        self.agent_id = os.getenv("MCP_AGENT_ID", "metadata-extraction-agent")
        self.server_url = os.getenv("MCP_SERVER_URL", "ws://mcp-server:3010")
        self.token = os.getenv("MCP_AGENT_TOKEN")

        # Initialize Claude provider
        self.claude_provider = ClaudeMetadataProvider()
        
        # Initialize Ollama provider
        self.ollama_provider = OllamaMetadataProvider()

        logger.info(f"Initialized {self.agent_id}")
        logger.info(f"Server: {self.server_url}")
        logger.info(
            f"Claude provider available: {self.claude_provider.is_available()}"
        )
        logger.info(
            f"Ollama provider available: {self.ollama_provider.is_available()}"
        )

    def get_provider(self, model: str) -> BaseMetadataProvider:
        """
        Get provider instance by model name.

        Args:
            model: Model name ("claude", "ollama", "gemini", "openai", etc.)

        Returns:
            Provider instance implementing BaseMetadataProvider

        Raises:
            ValueError: If model not supported
        """
        model_lower = model.lower()
        
        if model_lower == "claude":
            if not self.claude_provider.is_available():
                raise RuntimeError("Claude provider is not available (ANTHROPIC_API_KEY not set)")
            return self.claude_provider
        elif model_lower == "ollama":
            if not self.ollama_provider.is_available():
                raise RuntimeError("Ollama provider is not available (check if Ollama is running on localhost:11434)")
            return self.ollama_provider
        else:
            available = []
            if self.claude_provider.is_available():
                available.append("claude")
            if self.ollama_provider.is_available():
                available.append("ollama")
            
            raise ValueError(
                f"Unsupported model: {model}. Available providers: {', '.join(available) if available else 'none available'}"
            )

    async def extract_metadata(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured metadata from OCR text.

        Input parameters:
        {
            "text": str,                                    # Required
            "model": "claude" | "ollama" | "gemini" | "openai", # Required
            "output_type": "pala" | "archipelago" | "combined", # Required
            "language": str (optional),                         # ISO language code
            "document_context": str (optional),                 # Context hint
            "custom_prompt": str (optional),                    # Override default prompt
            "schema_version": str (optional)                    # Pin to schema version
        }

        Returns:
        {
            "schema_version": "1.0.0",
            "extraction_metadata": {
                "model_used": str,
                "timestamp": str (ISO8601),
                "processing_time_ms": int,
                "input_length": int
            },
            "confidence_scores": {
                "overall": float (0.0-1.0),
                "field_name": float (0.0-1.0),
                ...
            },
            "pala_metadata": {...},       # if output_type is "pala" or "combined"
            "archipelago_metadata": {...}, # if output_type is "archipelago" or "combined"
            "extracted_fields": {...}     # if output_type is "combined" (raw extracted data)
        }
        """
        start_time = datetime.now(timezone.utc)

        # Extract parameters
        text = params.get("text", "").strip()
        model = params.get("model", "claude").lower()
        output_type = params.get("output_type", "pala").lower()
        language = params.get("language")
        document_context = params.get("document_context")
        custom_prompt = params.get("custom_prompt")
        schema_version = params.get("schema_version", "1.0.0")

        # Validate required parameters
        if not text:
            raise ValueError("text is required and cannot be empty")
        if output_type not in ["pala", "archipelago", "combined"]:
            raise ValueError(
                f'output_type must be "pala", "archipelago", or "combined", got: {output_type}'
            )

        logger.info(
            f"[TOOL-START] extract_metadata: model={model}, output_type={output_type}, text_len={len(text)}"
        )

        try:
            # Get provider
            provider = self.get_provider(model)
            if not provider.is_available():
                raise ValueError(
                    f"Provider {model} is not available. Check configuration and dependencies."
                )

            # Extract metadata from provider
            extracted_data = await provider.extract_metadata(
                ocr_text=text,
                language=language,
                document_context=document_context,
                custom_prompt=custom_prompt,
            )

            # Add metadata
            extracted_data["extraction_timestamp"] = datetime.now(timezone.utc).isoformat()
            extracted_data["input_text_length"] = len(text)
            extracted_data["model"] = model
            extracted_data["document_context"] = document_context

            # Build response
            processing_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )

            result = {
                "schema_version": schema_version,
                "extraction_metadata": {
                    "model_used": model,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "processing_time_ms": processing_time_ms,
                    "input_length": len(text),
                },
                "confidence_scores": self._extract_confidence_scores(extracted_data),
            }

            # Apply mappers based on output_type
            if output_type in ["pala", "combined"]:
                result["pala_metadata"] = PalaMapper.map_extracted_data(extracted_data)

            if output_type in ["archipelago", "combined"]:
                result["archipelago_metadata"] = ArchipelagoMapper.map_extracted_data(
                    extracted_data
                )

            if output_type == "combined":
                result["extracted_fields"] = extracted_data

            logger.info(f"[TOOL-SUCCESS] extract_metadata completed in {processing_time_ms}ms")
            return result

        except Exception as e:
            processing_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            logger.error(f"[TOOL-FAILED] extract_metadata failed after {processing_time_ms}ms: {e}")
            raise

    @staticmethod
    def _extract_confidence_scores(extracted_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract confidence scores from extracted data"""
        # Get overall confidence from extracted data
        overall = extracted_data.get("confidence", 0.0)
        # Handle None values
        if overall is None:
            overall = 0.0
        
        confidences = {
            "overall": round(float(overall), 3) if overall is not None else 0.0
        }
        
        # Extract per-field confidences
        for field, value in extracted_data.items():
            if isinstance(value, dict) and "confidence" in value:
                conf_val = value.get("confidence")
                if conf_val is not None:
                    confidences[field] = round(float(conf_val), 3) if isinstance(conf_val, (int, float)) else 0.0

        return confidences

    def get_tool_definitions(self) -> list:
        """Return MCP tool definitions for registration"""
        return [
            {
                "name": "extract_metadata",
                "description": "Extract structured metadata from OCR text with confidence scores",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Input text (from OCR, transcription, or any source)",
                        },
                        "model": {
                            "type": "string",
                            "description": 'AI provider to use: "claude", "ollama", "gemini", "openai"',
                            "enum": ["claude", "ollama", "gemini", "openai"],
                        },
                        "output_type": {
                            "type": "string",
                            "description": 'Output schema: "pala", "archipelago", or "combined"',
                            "enum": ["pala", "archipelago", "combined"],
                        },
                        "language": {
                            "type": "string",
                            "description": "ISO language code (e.g., 'en', 'hi')",
                        },
                        "document_context": {
                            "type": "string",
                            "description": 'Context hint: "historical_letter", "monastery_record", etc.',
                        },
                        "custom_prompt": {
                            "type": "string",
                            "description": "Override default extraction prompt",
                        },
                        "schema_version": {
                            "type": "string",
                            "description": "Pin to specific schema version (e.g., '1.0.0')",
                        },
                    },
                    "required": ["text", "model", "output_type"],
                    "additionalProperties": False,
                },
            }
        ]

    async def handle_tool_invocation(
        self, method: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route tool invocation to appropriate handler"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name != "extract_metadata":
            raise ValueError(f"Unknown tool: {tool_name}")

        logger.info(f"Invoking tool: {tool_name}")
        return await self.extract_metadata(arguments)

    async def run(self):
        """Main agent loop"""
        try:
            # Prepare connection headers
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            logger.info(f"Connecting to MCP server at {self.server_url}")

            async with websockets.connect(self.server_url, additional_headers=headers) as ws:
                logger.info("Connected to MCP server")

                # Register tools
                registration_id = str(uuid.uuid4())
                registration_msg = make_request(
                    "tools/register",
                    {"tools": self.get_tool_definitions()},
                    registration_id,
                )

                await ws.send(registration_msg)
                logger.info("Sent tool registration request")

                # Wait for registration confirmation
                response = await ws.recv()
                reg_response = json.loads(response)
                logger.info(f"Registration response: {reg_response}")

                # Main message loop
                logger.info("Entering message processing loop")
                async for raw_message in ws:
                    try:
                        message = json.loads(raw_message)

                        # Handle tool invocation
                        if message.get("method") == "tools/invoke":
                            request_id = message.get("id")
                            params = message.get("params", {})

                            logger.debug(f"Received tool invocation: {request_id}")

                            try:
                                result = await self.handle_tool_invocation(
                                    message["method"], params
                                )

                                # Send response
                                response_msg = make_response(result, request_id)
                                await ws.send(response_msg)
                                logger.debug(f"Sent tool response: {request_id}")

                            except Exception as e:
                                # Send error response
                                error_msg = make_error(-32603, str(e), request_id)
                                await ws.send(error_msg)
                                logger.error(f"Tool invocation error: {e}")

                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")

        except Exception as e:
            logger.error(f"Agent error: {e}")
            raise


if __name__ == "__main__":
    agent = MetadataExtractionAgent()
    asyncio.run(agent.run())
