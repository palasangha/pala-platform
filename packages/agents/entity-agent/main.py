#!/usr/bin/env python3
"""
Entity Agent - Named Entity Recognition with hybrid Ollama/Claude disambiguation

Tools:
- extract_people: Extract and disambiguate person names
- extract_organizations: Extract organization/institution names
- extract_locations: Extract geographic entities
- extract_events: Extract historical events
- generate_relationships: Map entity connections

Model: Ollama (llama3.2) for basic NER, Claude for disambiguation
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


class EntityAgent:
    """Agent for Named Entity Recognition and disambiguation"""

    def __init__(self):
        self.agent_id = os.getenv('MCP_AGENT_ID', 'entity-agent')
        self.server_url = os.getenv('MCP_SERVER_URL', 'ws://mcp-server:3000')
        self.token = os.getenv('MCP_AGENT_TOKEN')
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://ollama:11434')
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'llama3.2')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')

        logger.info(f"Initialized {self.agent_id}")
        logger.info(f"Server: {self.server_url}")
        logger.info(f"Ollama: {self.ollama_host} ({self.ollama_model})")

        # Import tool handlers
        from tools.ner_extractor import NERExtractor
        from tools.entity_disambiguator import EntityDisambiguator
        from tools.relationship_mapper import RelationshipMapper

        self.ner_extractor = NERExtractor(self.ollama_host, self.ollama_model)
        self.disambiguator = EntityDisambiguator(self.anthropic_api_key)
        self.relationship_mapper = RelationshipMapper(self.ollama_host, self.ollama_model)

        # Tool registry
        self.tools = {
            'extract_people': self.extract_people,
            'extract_organizations': self.extract_organizations,
            'extract_locations': self.extract_locations,
            'extract_events': self.extract_events,
            'generate_relationships': self.generate_relationships
        }

    async def extract_people(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and disambiguate person names"""
        text = params.get('text', '')
        logger.info(f"Extracting people from {len(text)} chars of text")

        try:
            # Step 1: Extract using Ollama
            raw_people = await self.ner_extractor.extract_people(text)

            # Step 2: Disambiguate using Claude (if enabled)
            if self.anthropic_api_key and len(raw_people.get('people', [])) > 0:
                people = await self.disambiguator.disambiguate_people(
                    raw_people.get('people', []),
                    text[:2000]  # Provide context
                )
            else:
                people = raw_people.get('people', [])

            logger.info(f"Extracted {len(people)} people")
            return {"people": people}

        except Exception as e:
            logger.error(f"Error extracting people: {e}")
            return {"people": [], "_fallback": True}

    async def extract_organizations(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract organization names"""
        text = params.get('text', '')
        logger.info("Extracting organizations")

        try:
            result = await self.ner_extractor.extract_organizations(text)
            logger.info(f"Extracted {len(result.get('organizations', []))} organizations")
            return result
        except Exception as e:
            logger.error(f"Error extracting organizations: {e}")
            return {"organizations": [], "_fallback": True}

    async def extract_locations(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract geographic entities"""
        text = params.get('text', '')
        logger.info("Extracting locations")

        try:
            result = await self.ner_extractor.extract_locations(text)
            logger.info(f"Extracted {len(result.get('locations', []))} locations")
            return result
        except Exception as e:
            logger.error(f"Error extracting locations: {e}")
            return {"locations": [], "_fallback": True}

    async def extract_events(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract historical events"""
        text = params.get('text', '')
        logger.info("Extracting events")

        try:
            result = await self.ner_extractor.extract_events(text)
            logger.info(f"Extracted {len(result.get('events', []))} events")
            return result
        except Exception as e:
            logger.error(f"Error extracting events: {e}")
            return {"events": [], "_fallback": True}

    async def generate_relationships(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Map relationships between entities"""
        text = params.get('text', '')
        entities = params.get('entities', {})
        logger.info("Generating entity relationships")

        try:
            result = await self.relationship_mapper.map_relationships(text, entities)
            logger.info(f"Generated {len(result.get('relationships', []))} relationships")
            return result
        except Exception as e:
            logger.error(f"Error generating relationships: {e}")
            return {"relationships": [], "_fallback": True}

    def get_tool_definitions(self) -> list:
        """Return tool definitions for registration"""
        return [
            {
                "name": "extract_people",
                "description": "Extract and disambiguate person names from text",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Document text for NER"},
                    },
                    "required": ["text"],
                    "additionalProperties": False
                }
            },
            {
                "name": "extract_organizations",
                "description": "Extract organization and institution names",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Document text"},
                    },
                    "required": ["text"],
                    "additionalProperties": False
                }
            },
            {
                "name": "extract_locations",
                "description": "Extract geographic locations and places",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Document text"},
                    },
                    "required": ["text"],
                    "additionalProperties": False
                }
            },
            {
                "name": "extract_events",
                "description": "Extract historical events mentioned in text",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Document text"},
                    },
                    "required": ["text"],
                    "additionalProperties": False
                }
            },
            {
                "name": "generate_relationships",
                "description": "Map relationships and connections between entities",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Document text"},
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
    agent = EntityAgent()
    asyncio.run(agent.run())
