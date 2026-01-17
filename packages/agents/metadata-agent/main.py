#!/usr/bin/env python3
"""
Metadata Agent - Extracts metadata section for historical letters

Tools:
- extract_document_type: Classify document as letter/memo/telegram/fax/email/invitation
- extract_storage_info: Parse archive, collection, box, folder references
- extract_digitization_metadata: Extract scanning date, operator, equipment info
- determine_access_level: Classify as public/restricted/private

Model: Ollama (llama3.2)
"""

import asyncio
import json
import logging
import os
import sys
import websockets
import uuid
from typing import Dict, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def make_request(method: str, params: Dict[str, Any], request_id: str) -> str:
    """Create JSON-RPC 2.0 request"""
    return json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": request_id
    })


def make_response(result: Dict[str, Any], request_id: str) -> str:
    """Create JSON-RPC 2.0 response"""
    return json.dumps({
        "jsonrpc": "2.0",
        "result": result,
        "id": request_id
    })


def make_error(code: int, message: str, request_id: str) -> str:
    """Create JSON-RPC 2.0 error response"""
    return json.dumps({
        "jsonrpc": "2.0",
        "error": {
            "code": code,
            "message": message
        },
        "id": request_id
    })


class MetadataAgent:
    """Agent for extracting metadata from historical documents"""

    def __init__(self):
        self.agent_id = os.getenv('MCP_AGENT_ID', 'metadata-agent')
        self.server_url = os.getenv('MCP_SERVER_URL', 'ws://mcp-server:3000')
        self.token = os.getenv('MCP_AGENT_TOKEN')
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://ollama:11434')
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'llama3.2')

        logger.info(f"Initialized {self.agent_id}")
        logger.info(f"Server: {self.server_url}")
        logger.info(f"Ollama: {self.ollama_host} ({self.ollama_model})")

        # Import tool handlers
        from tools.document_classifier import DocumentClassifier
        from tools.storage_extractor import StorageExtractor
        from tools.access_determiner import AccessDeterminer

        self.classifier = DocumentClassifier(self.ollama_host, self.ollama_model)
        self.storage_extractor = StorageExtractor(self.ollama_host, self.ollama_model)
        self.access_determiner = AccessDeterminer(self.ollama_host, self.ollama_model)

        # Tool registry
        self.tools = {
            'extract_document_type': self.extract_document_type,
            'extract_storage_info': self.extract_storage_info,
            'extract_digitization_metadata': self.extract_digitization_metadata,
            'determine_access_level': self.determine_access_level
        }

    async def extract_document_type(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify document type based on OCR text

        Input:
        {
            "text": str,
            "ocr_confidence": float (optional),
            "detected_language": str (optional)
        }

        Output:
        {
            "document_type": "letter|memo|telegram|fax|email|invitation",
            "confidence": float (0-1),
            "reasoning": str
        }
        """
        text = params.get('text', '')
        ocr_confidence = params.get('ocr_confidence', 1.0)

        logger.info(f"Extracting document type from {len(text)} chars of text")

        try:
            result = await self.classifier.classify(text, ocr_confidence)
            logger.info(f"Document type: {result['document_type']} (confidence: {result['confidence']:.2%})")
            return result
        except Exception as e:
            logger.error(f"Error classifying document: {e}")
            return {
                "document_type": "letter",
                "confidence": 0.5,
                "reasoning": f"Classification error: {str(e)}",
                "_fallback": True
            }

    async def extract_storage_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract storage location information from text and metadata

        Input:
        {
            "text": str,
            "file_path": str (optional),
            "metadata": dict (optional)
        }

        Output:
        {
            "archive_name": str,
            "collection_name": str,
            "box_number": str,
            "folder_number": str,
            "digital_repository": str
        }
        """
        text = params.get('text', '')
        file_path = params.get('file_path', '')
        metadata = params.get('metadata', {})

        logger.info("Extracting storage information")

        try:
            result = await self.storage_extractor.extract(text, file_path, metadata)
            logger.info(f"Storage info: {result.get('archive_name', 'N/A')}")
            return result
        except Exception as e:
            logger.error(f"Error extracting storage info: {e}")
            return {
                "archive_name": "",
                "collection_name": "",
                "box_number": "",
                "folder_number": "",
                "digital_repository": "",
                "_fallback": True
            }

    async def extract_digitization_metadata(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract digitization metadata (scanning date, equipment, etc.)

        Input:
        {
            "file_path": str (optional),
            "file_metadata": dict (optional),
            "text": str (optional)
        }

        Output:
        {
            "date": str,
            "operator": str,
            "equipment": str,
            "resolution": str,
            "file_format": str
        }
        """
        file_path = params.get('file_path', '')
        file_metadata = params.get('file_metadata', {})
        text = params.get('text', '')

        logger.info("Extracting digitization metadata")

        try:
            # Extract from EXIF or file metadata
            result = {
                "date": file_metadata.get('upload_date', file_metadata.get('date', 'Unknown')),
                "operator": file_metadata.get('scanned_by', file_metadata.get('operator', 'Unknown')),
                "equipment": file_metadata.get('scanner_model', file_metadata.get('equipment', 'Unknown')),
                "resolution": f"{file_metadata.get('dpi', file_metadata.get('resolution', 'Unknown'))} DPI",
                "file_format": file_metadata.get('file_format', file_metadata.get('format', 'JPEG'))
            }
            logger.info(f"Digitization date: {result['date']}")
            return result
        except Exception as e:
            logger.error(f"Error extracting digitization metadata: {e}")
            return {
                "date": "Unknown",
                "operator": "Unknown",
                "equipment": "Unknown",
                "resolution": "Unknown",
                "file_format": "Unknown",
                "_fallback": True
            }

    async def determine_access_level(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine access level based on content sensitivity

        Input:
        {
            "text": str,
            "metadata": dict (optional)
        }

        Output:
        {
            "access_level": "public|restricted|private",
            "reasoning": str,
            "confidence": float (0-1)
        }
        """
        text = params.get('text', '')
        metadata = params.get('metadata', {})

        logger.info("Determining access level")

        try:
            result = await self.access_determiner.determine(text, metadata)
            logger.info(f"Access level: {result['access_level']} (confidence: {result['confidence']:.2%})")
            return result
        except Exception as e:
            logger.error(f"Error determining access level: {e}")
            return {
                "access_level": "public",
                "reasoning": "Default access level",
                "confidence": 0.5,
                "_fallback": True
            }

    def get_tool_definitions(self) -> list:
        """Return tool definitions for registration"""
        return [
            {
                "name": "extract_document_type",
                "description": "Classify historical document type (letter, memo, telegram, fax, email, invitation)",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "OCR extracted text from document"
                        },
                        "ocr_confidence": {
                            "type": "number",
                            "description": "OCR confidence score (0-1)"
                        },
                        "detected_language": {
                            "type": "string",
                            "description": "Detected language code"
                        }
                    },
                    "required": ["text"],
                    "additionalProperties": False
                }
            },
            {
                "name": "extract_storage_info",
                "description": "Extract storage location information (archive, collection, box, folder)",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Document text"},
                        "file_path": {"type": "string", "description": "File path"},
                        "metadata": {"type": "object", "description": "File metadata"}
                    },
                    "required": ["text"],
                    "additionalProperties": False
                }
            },
            {
                "name": "extract_digitization_metadata",
                "description": "Extract digitization metadata (date, operator, equipment, resolution)",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "file_metadata": {"type": "object"},
                        "text": {"type": "string"}
                    },
                    "additionalProperties": False
                }
            },
            {
                "name": "determine_access_level",
                "description": "Determine document access level (public, restricted, private)",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Document text"},
                        "metadata": {"type": "object", "description": "Document metadata"}
                    },
                    "required": ["text"],
                    "additionalProperties": False
                }
            }
        ]

    async def handle_tool_invocation(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Route tool invocation to appropriate handler"""
        tool_name = params.get('name')
        arguments = params.get('arguments', {})

        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        logger.info(f"Invoking tool: {tool_name}")
        return await self.tools[tool_name](arguments)

    async def run(self):
        """Main agent loop"""
        try:
            # Prepare connection headers
            headers = {}
            if self.token:
                headers['Authorization'] = f'Bearer {self.token}'

            logger.info(f"Connecting to MCP server at {self.server_url}")

            async with websockets.connect(self.server_url, additional_headers=headers) as ws:
                logger.info("Connected to MCP server")

                # Register tools
                registration_id = str(uuid.uuid4())
                registration_msg = make_request(
                    "tools/register",
                    {"tools": self.get_tool_definitions()},
                    registration_id
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
                        if message.get('method') == 'tools/invoke':
                            request_id = message.get('id')
                            params = message.get('params', {})

                            logger.debug(f"Received tool invocation: {request_id}")

                            try:
                                result = await self.handle_tool_invocation(message['method'], params)

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
            logger.error(f"Agent error: {e}", exc_info=True)
            sys.exit(1)


if __name__ == '__main__':
    agent = MetadataAgent()
    asyncio.run(agent.run())
