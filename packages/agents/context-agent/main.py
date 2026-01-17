#!/usr/bin/env python3
"""
Context Agent - Historical context and significance analysis using Claude Opus

Tools:
- research_historical_context: Generate historical context for the document
- assess_significance: Determine historical significance and impact
- generate_biographies: Create biographies of key people mentioned

Model: Claude Opus 4.5 (highest quality for critical analysis)
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


class ContextAgent:
    """Agent for historical context and significance analysis"""

    def __init__(self):
        self.agent_id = os.getenv('MCP_AGENT_ID', 'context-agent')
        self.server_url = os.getenv('MCP_SERVER_URL', 'ws://mcp-server:3000')
        self.token = os.getenv('MCP_AGENT_TOKEN')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')

        logger.info(f"Initialized {self.agent_id}")
        logger.info(f"Server: {self.server_url}")

        # Import tool handlers
        from tools.historical_researcher import HistoricalResearcher
        from tools.significance_assessor import SignificanceAssessor
        from tools.biography_generator import BiographyGenerator

        self.historian = HistoricalResearcher(self.anthropic_api_key)
        self.significance_assessor = SignificanceAssessor(self.anthropic_api_key)
        self.biographer = BiographyGenerator(self.anthropic_api_key)

        # Tool registry
        self.tools = {
            'research_historical_context': self.research_historical_context,
            'assess_significance': self.assess_significance,
            'generate_biographies': self.generate_biographies
        }

    async def research_historical_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Research historical context for the document"""
        text = params.get('text', '')
        people = params.get('people', [])
        locations = params.get('locations', [])
        events = params.get('events', [])
        date = params.get('date', '')

        logger.info("Researching historical context")

        try:
            result = await self.historian.research(text, people, locations, events, date)
            logger.info(f"Generated historical context: {len(result.get('historical_context', ''))} chars")
            return result
        except Exception as e:
            logger.error(f"Error researching context: {e}")
            return {
                "historical_context": "Historical context not available",
                "confidence": 0.0,
                "_fallback": True
            }

    async def assess_significance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Assess historical significance of the document"""
        text = params.get('text', '')
        context = params.get('context', '')

        logger.info("Assessing historical significance")

        try:
            result = await self.significance_assessor.assess(text, context)
            logger.info(f"Assessed significance: {result.get('significance_level', 'unknown')}")
            return result
        except Exception as e:
            logger.error(f"Error assessing significance: {e}")
            return {
                "significance_level": "unknown",
                "assessment": "Significance assessment not available",
                "confidence": 0.0,
                "_fallback": True
            }

    async def generate_biographies(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate enhanced biographies for key people"""
        people = params.get('people', [])
        text = params.get('text', '')

        logger.info(f"Generating biographies for {len(people)} people")

        try:
            result = await self.biographer.generate(people, text)
            logger.info(f"Generated {len(result.get('biographies', {}))} biographies")
            return result
        except Exception as e:
            logger.error(f"Error generating biographies: {e}")
            return {"biographies": {}, "_fallback": True}

    def get_tool_definitions(self) -> list:
        """Return tool definitions for registration"""
        return [
            {
                "name": "research_historical_context",
                "description": "Research and generate historical context for the document",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Document text"},
                        "people": {"type": "array", "description": "People mentioned"},
                        "locations": {"type": "array", "description": "Locations mentioned"},
                        "events": {"type": "array", "description": "Events mentioned"},
                        "date": {"type": "string", "description": "Document date"}
                    },
                    "required": ["text"],
                    "additionalProperties": False
                }
            },
            {
                "name": "assess_significance",
                "description": "Assess the historical significance of the document",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Document text"},
                        "context": {"type": "string", "description": "Historical context"}
                    },
                    "required": ["text"],
                    "additionalProperties": False
                }
            },
            {
                "name": "generate_biographies",
                "description": "Generate enhanced biographies for key people",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "people": {"type": "array", "description": "People to generate bios for"},
                        "text": {"type": "string", "description": "Document context"}
                    },
                    "required": ["people"],
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
    agent = ContextAgent()
    asyncio.run(agent.run())
