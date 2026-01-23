#!/usr/bin/env python3
"""
Content Agent - Summarization, keyword extraction, and subject classification

Tools:
- generate_summary: Claude Sonnet summaries of letter content
- extract_keywords: Extract key terms and concepts
- classify_subjects: Classify letter by subject taxonomy

Model: Claude Sonnet for summaries, Ollama for keywords
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


class ContentAgent:
    """Agent for content analysis, summarization, and classification"""

    def __init__(self):
        self.agent_id = os.getenv('MCP_AGENT_ID', 'content-agent')
        self.server_url = os.getenv('MCP_SERVER_URL', 'ws://mcp-server:3000')
        self.token = os.getenv('MCP_AGENT_TOKEN')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://ollama:11434')
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'llama3.2')

        logger.info(f"Initialized {self.agent_id}")
        logger.info(f"Server: {self.server_url}")

        # Import tool handlers
        from tools.summarizer import Summarizer
        from tools.keyword_extractor import KeywordExtractor
        from tools.subject_classifier import SubjectClassifier

        self.summarizer = Summarizer(self.anthropic_api_key)
        self.keyword_extractor = KeywordExtractor(self.ollama_host, self.ollama_model)
        self.subject_classifier = SubjectClassifier(self.ollama_host, self.ollama_model)

        # Tool registry
        self.tools = {
            'generate_summary': self.generate_summary,
            'extract_keywords': self.extract_keywords,
            'classify_subjects': self.classify_subjects
        }

    async def generate_summary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of letter content"""
        text = params.get('text', '')
        entities = params.get('entities', {})

        logger.info(f"Generating summary from {len(text)} chars of text")

        try:
            result = await self.summarizer.summarize(text, entities)
            logger.info(f"Generated summary: {len(result.get('summary', ''))} chars")
            return result
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return {
                "summary": "Summary not available",
                "confidence": 0.0,
                "_fallback": True
            }

    async def extract_keywords(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract keywords from letter"""
        text = params.get('text', '')

        logger.info("Extracting keywords")

        try:
            result = await self.keyword_extractor.extract(text)
            logger.info(f"Extracted {len(result.get('keywords', []))} keywords")
            return result
        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return {"keywords": [], "_fallback": True}

    async def classify_subjects(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Classify letter by subject"""
        text = params.get('text', '')
        entities = params.get('entities', {})

        logger.info("Classifying subjects")

        try:
            result = await self.subject_classifier.classify(text, entities)
            logger.info(f"Classified subjects: {result.get('subjects', [])}")
            return result
        except Exception as e:
            logger.error(f"Error classifying subjects: {e}")
            return {"subjects": [], "_fallback": True}

    def get_tool_definitions(self) -> list:
        """Return tool definitions for registration"""
        return [
            {
                "name": "generate_summary",
                "description": "Generate high-quality summary of letter content",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Full letter text"},
                        "entities": {"type": "object", "description": "Extracted entities from Phase 1"}
                    },
                    "required": ["text"],
                    "additionalProperties": False
                }
            },
            {
                "name": "extract_keywords",
                "description": "Extract keywords and key concepts from letter",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Full letter text"}
                    },
                    "required": ["text"],
                    "additionalProperties": False
                }
            },
            {
                "name": "classify_subjects",
                "description": "Classify letter by subject and topics",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Full letter text"},
                        "entities": {"type": "object", "description": "Extracted entities"}
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
    agent = ContentAgent()
    asyncio.run(agent.run())
