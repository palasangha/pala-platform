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
        self.server_url = os.getenv("MCP_SERVER_URL", "ws://localhost:4000")
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
        if model.lower() == "claude":
            return self.claude_provider
        elif model.lower() == "ollama":
            return self.ollama_provider
        # Future providers can be added here
        # elif model.lower() == "gemini":
        #     return self.gemini_provider
        else:
            raise ValueError(
                f"Unsupported model: {model}. Supported: claude, ollama (more coming soon)"
            )

    async def extract_metadata(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured metadata from OCR text.

        Input parameters:
        {
            "text": str,                                        # Optional if file_data provided
            "file_data": str (base64-encoded file content),     # Optional if text provided
            "filename": str,                                    # Optional with file_data
            "file_format": str,                                 # Optional with file_data (pdf, txt, json, md, ...)
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
        file_data_b64 = params.get("file_data", "").strip()
        filename = params.get("filename", "document")
        file_format = params.get("file_format", "").lower()
        model = params.get("model", "claude").lower()
        output_type = params.get("output_type", "pala").lower()
        language = params.get("language")
        document_context = params.get("document_context")
        custom_prompt = params.get("custom_prompt")
        schema_version = params.get("schema_version", "1.0.0")
        chunk_size = int(os.getenv("METADATA_CHUNK_CHARS", "8000"))
        chunk_overlap = int(os.getenv("METADATA_CHUNK_OVERLAP", "500"))

        # Validate required parameters
        if not text and not file_data_b64:
            raise ValueError("Either text or file_data is required and cannot be empty")
        if output_type not in ["pala", "archipelago", "combined"]:
            raise ValueError(
                f'output_type must be "pala", "archipelago", or "combined", got: {output_type}'
            )

        # If file payload is provided without text, extract text from file first
        if not text and file_data_b64:
            if not file_format:
                file_format = filename.split(".")[-1].lower() if "." in filename else "txt"

            return await self.extract_metadata_from_file(
                {
                    "file_data": file_data_b64,
                    "filename": filename,
                    "file_format": file_format,
                    "model": model,
                    "output_type": output_type,
                    "language": language,
                    "document_context": document_context,
                    "custom_prompt": custom_prompt,
                    "schema_version": schema_version,
                }
            )

        logger.info(
            f"Extracting metadata: model={model}, output_type={output_type}, text_len={len(text)}"
        )

        try:
            # Get provider
            provider = self.get_provider(model)
            if not provider.is_available():
                raise ValueError(
                    f"Provider {model} is not available. Check configuration and dependencies."
                )

            # Extract metadata from provider, chunking long input so the full document is analyzed.
            extracted_data = await self._extract_metadata_with_chunking(
                provider=provider,
                text=text,
                language=language,
                document_context=document_context,
                custom_prompt=custom_prompt,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            logger.info(f"Raw extracted data keys: {list(extracted_data.keys())}")
            logger.info(f"Raw extracted data (truncated): {str(extracted_data)[:500]}")

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

            logger.info(f"Metadata extraction complete in {processing_time_ms}ms")
            return result

        except Exception as e:
            logger.exception(f"Metadata extraction failed: {e}")
            raise

    async def _extract_metadata_with_chunking(
        self,
        provider: BaseMetadataProvider,
        text: str,
        language: Optional[str],
        document_context: Optional[str],
        custom_prompt: Optional[str],
        chunk_size: int,
        chunk_overlap: int,
    ) -> Dict[str, Any]:
        """Extract metadata for either a single chunk or multiple chunks merged together."""
        normalized_text = text.strip()
        if len(normalized_text) <= chunk_size:
            return await provider.extract_metadata(
                ocr_text=normalized_text,
                language=language,
                document_context=document_context,
                custom_prompt=custom_prompt,
            )

        chunks = self._split_text_into_chunks(normalized_text, chunk_size, chunk_overlap)
        logger.info(f"Splitting input into {len(chunks)} chunks (chunk_size={chunk_size}, overlap={chunk_overlap})")

        chunk_results = []
        for index, chunk in enumerate(chunks, start=1):
            logger.info(f"Extracting chunk {index}/{len(chunks)} ({len(chunk)} chars)")
            chunk_result = await provider.extract_metadata(
                ocr_text=chunk,
                language=language,
                document_context=document_context,
                custom_prompt=custom_prompt,
            )
            chunk_results.append(chunk_result)

        merged = self._merge_chunk_extractions(chunk_results)
        merged["chunk_count"] = len(chunks)
        merged["chunk_sizes"] = [len(chunk) for chunk in chunks]
        return merged

    @staticmethod
    def _split_text_into_chunks(text: str, chunk_size: int, chunk_overlap: int) -> list:
        """Split text into overlapping chunks without losing the full document."""
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + chunk_size, text_length)
            chunks.append(text[start:end])
            if end >= text_length:
                break
            start = end - chunk_overlap

        return chunks

    @staticmethod
    def _merge_chunk_extractions(chunk_results: list) -> Dict[str, Any]:
        """Merge multiple provider outputs into one combined extracted data structure."""
        if not chunk_results:
            return {}

        if len(chunk_results) == 1:
            return chunk_results[0]

        merged: Dict[str, Any] = {
            "document_type": {"value": "unknown", "confidence": 0.0},
            "document_date": {"value": None, "confidence": 0.0},
            "people": [],
            "organizations": [],
            "locations": [],
            "summary": {"text": "", "confidence": 0.0},
            "topics": [],
            "tone": "neutral",
            "sentiment": "neutral",
            "language": "en",
            "access_level": "public",
            "confidence_notes": [],
        }

        def _as_dict(value: Any) -> Dict[str, Any]:
            return value if isinstance(value, dict) else {}

        def _as_list(value: Any) -> list:
            return value if isinstance(value, list) else []

        def _pick_better(current: Dict[str, Any], candidate: Dict[str, Any], value_key: str = "value") -> Dict[str, Any]:
            current_conf = current.get("confidence", 0.0) if isinstance(current, dict) else 0.0
            candidate_conf = candidate.get("confidence", 0.0) if isinstance(candidate, dict) else 0.0
            current_value = current.get(value_key) if isinstance(current, dict) else None
            candidate_value = candidate.get(value_key) if isinstance(candidate, dict) else None
            if candidate_conf > current_conf:
                return candidate
            if candidate_conf == current_conf and current_value in [None, "", "unknown"] and candidate_value not in [None, "", "unknown"]:
                return candidate
            return current

        people_by_key = {}
        orgs_by_key = {}
        locations_by_key = {}
        topic_order = []
        notes = []
        summary_texts = []

        for result in chunk_results:
            if not isinstance(result, dict):
                continue

            merged["document_type"] = _pick_better(merged["document_type"], _as_dict(result.get("document_type")))
            merged["document_date"] = _pick_better(merged["document_date"], _as_dict(result.get("document_date")))

            summary_obj = result.get("summary")
            if isinstance(summary_obj, dict):
                summary_text = summary_obj.get("text") or summary_obj.get("value") or ""
                if summary_text:
                    summary_texts.append(summary_text.strip())
                merged["summary"] = _pick_better(merged["summary"], {"text": summary_text, "confidence": summary_obj.get("confidence", 0.0)}, value_key="text")

            for field_name, bucket in [("people", people_by_key), ("organizations", orgs_by_key), ("locations", locations_by_key)]:
                for item in _as_list(result.get(field_name)):
                    if not isinstance(item, dict):
                        continue
                    name = (item.get("name") or "").strip()
                    role = (item.get("role") or "").strip()
                    if not name:
                        continue
                    key = (name.lower(), role.lower())
                    existing = bucket.get(key)
                    if existing is None or item.get("confidence", 0.0) > existing.get("confidence", 0.0):
                        bucket[key] = item

            for topic in _as_list(result.get("topics")):
                if isinstance(topic, str):
                    cleaned = topic.strip()
                    if cleaned and cleaned.lower() not in [t.lower() for t in topic_order]:
                        topic_order.append(cleaned)

            tone = result.get("tone")
            if isinstance(tone, str) and tone.strip() and merged["tone"] == "neutral":
                merged["tone"] = tone.strip()

            sentiment = result.get("sentiment")
            if isinstance(sentiment, str) and sentiment.strip() and merged["sentiment"] == "neutral":
                merged["sentiment"] = sentiment.strip()

            language = result.get("language")
            if isinstance(language, str) and language.strip():
                merged["language"] = language.strip()

            access_level = result.get("access_level")
            if isinstance(access_level, str) and access_level.strip():
                merged["access_level"] = access_level.strip()

            notes_value = result.get("confidence_notes")
            if isinstance(notes_value, str) and notes_value.strip():
                notes.append(notes_value.strip())

        merged["people"] = list(people_by_key.values())
        merged["organizations"] = list(orgs_by_key.values())
        merged["locations"] = list(locations_by_key.values())
        merged["topics"] = topic_order
        merged["confidence_notes"] = " | ".join(notes) if notes else None

        if summary_texts and not merged["summary"].get("text"):
            merged["summary"]["text"] = " ".join(summary_texts)
        elif summary_texts and len(summary_texts) > 1:
            merged["summary"]["text"] = " ".join(summary_texts)

        merged["summary"]["confidence"] = max(
            [result.get("summary", {}).get("confidence", 0.0) for result in chunk_results if isinstance(result, dict) and isinstance(result.get("summary"), dict)] + [0.0]
        )

        return merged

    async def extract_metadata_from_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured metadata directly from a file (base64-encoded).

        Input parameters:
        {
            "file_data": str (base64-encoded file content),  # Required
            "filename": str,                                  # Optional - original filename
            "file_format": str,                               # Optional - pdf, txt, json, etc
            "model": "claude" | "ollama",                     # Optional, default: "ollama"
            "output_type": "pala" | "archipelago" | "combined", # Optional, default: "pala"
            "language": str (optional),                       # ISO language code
            "document_context": str (optional),               # Context hint
            "custom_prompt": str (optional)                   # Override default prompt
        }

        Returns:
        Same as extract_metadata() but processes file first to extract text.
        """
        import base64
        import tempfile
        import os

        file_data_b64 = params.get("file_data", "").strip()
        filename = params.get("filename", "document")
        file_format = params.get("file_format", "").lower()
        model = params.get("model", "ollama").lower()
        output_type = params.get("output_type", "pala").lower()
        language = params.get("language")
        document_context = params.get("document_context")
        custom_prompt = params.get("custom_prompt")
        schema_version = params.get("schema_version", "1.0.0")

        if not file_data_b64:
            raise ValueError("file_data (base64-encoded) is required")

        logger.info(f"Extracting metadata from file: {filename}, format: {file_format}")

        try:
            # Decode base64 to bytes
            file_bytes = base64.b64decode(file_data_b64)
            logger.info(f"Decoded {len(file_bytes)} bytes from base64")

            # Extract text based on file format
            text = await self._extract_text_from_file(file_bytes, file_format, filename)

            if not text or not text.strip():
                logger.warning(f"No text extracted from file: {filename}")
                text = f"Document: {filename}\nFormat: {file_format}\n(Binary file, could not extract text)"

            logger.info(f"Extracted {len(text)} characters from file")

            # Now call extract_metadata with the extracted text
            result = await self.extract_metadata({
                "text": text,
                "model": model,
                "output_type": output_type,
                "language": language,
                "document_context": document_context,
                "custom_prompt": custom_prompt,
                "schema_version": schema_version,
            })

            # Add file metadata to result
            result["source_file"] = {
                "filename": filename,
                "format": file_format,
                "size_bytes": len(file_bytes),
                "text_extracted": True
            }

            return result

        except Exception as e:
            logger.error(f"Failed to extract metadata from file: {e}")
            raise

    @staticmethod
    async def _extract_text_from_file(file_bytes: bytes, file_format: str, filename: str) -> str:
        """
        Extract text from file based on format.

        Supports: txt, json, pdf (basic), md
        """
        text = ""

        if file_format in ["txt", "md"]:
            # Simple text formats
            try:
                text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text = file_bytes.decode("latin-1")

        elif file_format == "json":
            # JSON format
            try:
                import json
                text = file_bytes.decode("utf-8")
                data = json.loads(text)
                # Pretty print JSON for better readability
                text = json.dumps(data, indent=2)
            except Exception as e:
                logger.warning(f"Failed to parse JSON: {e}")
                text = file_bytes.decode("utf-8", errors="ignore")

        elif file_format == "pdf":
            # PDF format - try to extract text
            try:
                from pypdf import PdfReader
                from io import BytesIO

                pdf_file = BytesIO(file_bytes)
                pdf_reader = PdfReader(pdf_file)
                text_parts = []
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                text = "\n\n".join(text_parts)
                logger.info(f"Extracted {len(text)} chars from PDF with {len(pdf_reader.pages)} pages")
            except ImportError:
                try:
                    import PyPDF2
                    from io import BytesIO

                    pdf_file = BytesIO(file_bytes)
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    text_parts = []
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                    text = "\n\n".join(text_parts)
                    logger.info(
                        f"Extracted {len(text)} chars from PDF with {len(pdf_reader.pages)} pages (PyPDF2)"
                    )
                except ImportError:
                    logger.warning("No PDF parser available (pypdf/PyPDF2). Returning safe fallback text")
                    text = (
                        f"Document: {filename}\n"
                        f"Format: {file_format}\n"
                        "(PDF uploaded but PDF text parser is not installed. Install pypdf for full extraction.)"
                    )
                except Exception as e:
                    logger.warning(f"PDF extraction fallback failed: {e}")
                    text = f"PDF file: {filename} (could not extract text)"
            except Exception as e:
                logger.warning(f"PDF extraction error: {e}")
                text = f"PDF file: {filename} (extraction error)"

        else:
            # Unknown format - try UTF-8 decoding
            logger.info(f"Unknown format '{file_format}', attempting UTF-8 decode")
            try:
                text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    text = file_bytes.decode("latin-1")
                except Exception:
                    logger.warning(f"Could not decode file: {filename}")
                    text = f"Binary file: {filename} (could not extract text)"

        return text

    @staticmethod
    def _extract_confidence_scores(extracted_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract confidence scores from extracted data"""
        confidences = {}
        for field, value in extracted_data.items():
            if isinstance(value, dict) and "confidence" in value:
                confidences[field] = value["confidence"]

        # Calculate overall confidence
        if confidences:
            overall = sum(confidences.values()) / len(confidences)
            confidences["overall"] = round(overall, 3)
        else:
            confidences["overall"] = 0.0

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
                            "description": "Input text from any source (OCR, transcription, etc.)",
                        },
                        "file_data": {
                            "type": "string",
                            "description": "Base64-encoded file content. Optional if text is provided.",
                        },
                        "filename": {
                            "type": "string",
                            "description": "Optional filename for file_data input (e.g., 'document.pdf')",
                        },
                        "file_format": {
                            "type": "string",
                            "description": "Optional file format for file_data input (e.g., 'pdf', 'txt', 'json', 'md')",
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
                    "required": ["model", "output_type"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "extract_metadata_from_file",
                "description": "Extract structured metadata directly from a file (base64-encoded). Supports PDF, text, JSON, and markdown files.",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_data": {
                            "type": "string",
                            "description": "Base64-encoded file content",
                        },
                        "filename": {
                            "type": "string",
                            "description": "Original filename (e.g., 'document.pdf')",
                        },
                        "file_format": {
                            "type": "string",
                            "description": 'File format: "pdf", "txt", "json", "md", etc.',
                            "enum": ["pdf", "txt", "json", "md"],
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
                    },
                    "required": ["file_data", "file_format", "model", "output_type"],
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

        if tool_name == "extract_metadata":
            logger.info(f"Invoking tool: {tool_name}")
            return await self.extract_metadata(arguments)
        elif tool_name == "extract_metadata_from_file":
            logger.info(f"Invoking tool: {tool_name}")
            return await self.extract_metadata_from_file(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

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
