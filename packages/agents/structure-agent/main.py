#!/usr/bin/env python3
"""
Structure Agent - Parses letter structure and correspondence information

Tools:
- extract_salutation: Identify greeting
- parse_letter_body: Segment into paragraphs
- extract_closing: Find closing phrase
- extract_signature: Identify signatory
- identify_attachments: Detect enclosures
- parse_correspondence: Extract sender/recipient/cc

Model: Ollama (mixtral for complex structural analysis)
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


class StructureAgent:
    """Agent for parsing letter structure and correspondence"""

    def __init__(self):
        self.agent_id = os.getenv('MCP_AGENT_ID', 'structure-agent')
        self.server_url = os.getenv('MCP_SERVER_URL', 'ws://mcp-server:3000')
        self.token = os.getenv('MCP_AGENT_TOKEN')
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://ollama:11434')
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'mixtral')

        logger.info(f"Initialized {self.agent_id}")
        logger.info(f"Server: {self.server_url}")
        logger.info(f"Ollama: {self.ollama_host} ({self.ollama_model})")

        # Import tool handlers
        from tools.structure_parser import StructureParser
        from tools.correspondence_extractor import CorrespondenceExtractor

        self.structure_parser = StructureParser(self.ollama_host, self.ollama_model)
        self.correspondence_extractor = CorrespondenceExtractor(self.ollama_host, self.ollama_model)

        # Tool registry
        self.tools = {
            'extract_salutation': self.extract_salutation,
            'parse_letter_body': self.parse_letter_body,
            'extract_closing': self.extract_closing,
            'extract_signature': self.extract_signature,
            'identify_attachments': self.identify_attachments,
            'parse_correspondence': self.parse_correspondence
        }

    async def extract_salutation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract salutation (greeting) from letter"""
        text = params.get('text', '')
        full_text = params.get('full_text', text)

        logger.info(f"Extracting salutation from {len(text)} chars of text")

        try:
            result = await self.structure_parser.extract_salutation(full_text)
            logger.info(f"Salutation: {result.get('salutation', '')}")
            return result
        except Exception as e:
            logger.error(f"Error extracting salutation: {e}")
            return {
                "salutation": "",
                "type": "unknown",
                "confidence": 0.0,
                "_fallback": True
            }

    async def parse_letter_body(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Parse letter body into paragraphs"""
        text = params.get('text', '')
        full_text = params.get('full_text', text)

        logger.info("Parsing letter body structure")

        try:
            result = await self.structure_parser.parse_body(full_text)
            logger.info(f"Parsed {result.get('paragraph_count', 0)} paragraphs")
            return result
        except Exception as e:
            logger.error(f"Error parsing letter body: {e}")
            return {
                "body": [],
                "paragraph_count": 0,
                "average_paragraph_length": 0,
                "_fallback": True
            }

    async def extract_closing(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract closing phrase from letter"""
        text = params.get('text', '')
        full_text = params.get('full_text', text)

        logger.info("Extracting closing phrase")

        try:
            result = await self.structure_parser.extract_closing(full_text)
            logger.info(f"Closing: {result.get('closing', '')}")
            return result
        except Exception as e:
            logger.error(f"Error extracting closing: {e}")
            return {
                "closing": "",
                "type": "unknown",
                "confidence": 0.0,
                "_fallback": True
            }

    async def extract_signature(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract signature or signatory information"""
        text = params.get('text', '')
        full_text = params.get('full_text', text)

        logger.info("Extracting signature information")

        try:
            result = await self.structure_parser.extract_signature(full_text)
            logger.info(f"Signature info: {result.get('signatory_name', '')}")
            return result
        except Exception as e:
            logger.error(f"Error extracting signature: {e}")
            return {
                "signature": "",
                "signatory_name": "",
                "title": "",
                "confidence": 0.0,
                "_fallback": True
            }

    async def identify_attachments(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Identify attachments and enclosures mentioned in letter"""
        text = params.get('text', '')
        full_text = params.get('full_text', text)

        logger.info("Identifying attachments")

        try:
            result = await self.structure_parser.identify_attachments(full_text)
            logger.info(f"Found {len(result.get('attachments', []))} attachments")
            return result
        except Exception as e:
            logger.error(f"Error identifying attachments: {e}")
            return {
                "attachments": [],
                "has_attachments": False,
                "_fallback": True
            }

    async def parse_correspondence(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract correspondence information (sender, recipient, cc, date)"""
        text = params.get('text', '')
        full_text = params.get('full_text', text)

        logger.info("Parsing correspondence information")

        try:
            result = await self.correspondence_extractor.extract(full_text)
            logger.info(f"Extracted correspondence from {result.get('correspondence', {}).get('sender', {}).get('name', 'Unknown')}")
            return result
        except Exception as e:
            logger.error(f"Error parsing correspondence: {e}")
            return {
                "correspondence": {
                    "sender": {"name": "", "title": "", "organization": ""},
                    "recipient": {"name": "", "title": "", "organization": ""},
                    "cc": [],
                    "bcc": [],
                    "date": ""
                },
                "_fallback": True
            }

    def get_tool_definitions(self) -> list:
        """Return tool definitions for registration"""
        return [
            {
                "name": "extract_salutation",
                "description": "Extract salutation (greeting) from letter",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Letter text"},
                        "full_text": {"type": "string", "description": "Full text with formatting"}
                    },
                    "required": ["text"],
                    "additionalProperties": False
                }
            },
            {
                "name": "parse_letter_body",
                "description": "Parse letter body into paragraphs",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Letter text"},
                        "full_text": {"type": "string", "description": "Full text with formatting"}
                    },
                    "required": ["text"],
                    "additionalProperties": False
                }
            },
            {
                "name": "extract_closing",
                "description": "Extract closing phrase from letter",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Letter text"},
                        "full_text": {"type": "string", "description": "Full text with formatting"}
                    },
                    "required": ["text"],
                    "additionalProperties": False
                }
            },
            {
                "name": "extract_signature",
                "description": "Extract signature and signatory information",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Letter text"},
                        "full_text": {"type": "string", "description": "Full text with formatting"}
                    },
                    "required": ["text"],
                    "additionalProperties": False
                }
            },
            {
                "name": "identify_attachments",
                "description": "Identify attachments and enclosures mentioned in letter",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Letter text"},
                        "full_text": {"type": "string", "description": "Full text with formatting"}
                    },
                    "required": ["text"],
                    "additionalProperties": False
                }
            },
            {
                "name": "parse_correspondence",
                "description": "Extract correspondence information (sender, recipient, date)",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Letter text"},
                        "full_text": {"type": "string", "description": "Full text with formatting"}
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
            headers = {}
            if self.token:
                headers['Authorization'] = f'Bearer {self.token}'

            logger.info(f"Connecting to MCP server at {self.server_url}")

            async with websockets.connect(self.server_url, additional_headers=headers) as ws:
                logger.info("Connected to MCP server")

                registration_id = str(uuid.uuid4())
                registration_msg = make_request(
                    "tools/register",
                    {"tools": self.get_tool_definitions()},
                    registration_id
                )

                await ws.send(registration_msg)
                logger.info("Sent tool registration request")

                response = await ws.recv()
                reg_response = json.loads(response)
                logger.info(f"Registration response: {reg_response}")

                logger.info("Entering message processing loop")
                async for raw_message in ws:
                    try:
                        message = json.loads(raw_message)

                        if message.get('method') == 'tools/invoke':
                            request_id = message.get('id')
                            params = message.get('params', {})

                            logger.debug(f"Received tool invocation: {request_id}")

                            try:
                                result = await self.handle_tool_invocation(message['method'], params)
                                response_msg = make_response(result, request_id)
                                await ws.send(response_msg)
                                logger.debug(f"Sent tool response: {request_id}")

                            except Exception as e:
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
    agent = StructureAgent()
    asyncio.run(agent.run())
