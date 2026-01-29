#!/usr/bin/env python3
"""
Context Agent - Historical context and significance analysis using Ollama

Tools:
- research_historical_context: Generate historical context for the document
- assess_significance: Determine historical significance and impact
- generate_biographies: Create biographies of key people mentioned
- parse_ami_filename: Parse AMI Master naming convention filenames and extract metadata

Model: Ollama (llama3.2 or configured model)
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
        # API key not needed for Ollama, but keep for compatibility
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')

        logger.info(f"Initialized {self.agent_id}")
        logger.info(f"Server: {self.server_url}")

        # Import tool handlers (now using Ollama)
        from tools.historical_researcher import HistoricalResearcher
        from tools.significance_assessor import SignificanceAssessor
        from tools.biography_generator import BiographyGenerator
        from tools.ami_metadata_parser import AMIMetadataParser
        from tools.metadata_writer import MetadataWriter
        from tools.exif_metadata_handler import ExifMetadataHandler

        self.historian = HistoricalResearcher(self.anthropic_api_key)
        self.significance_assessor = SignificanceAssessor(self.anthropic_api_key)
        self.biographer = BiographyGenerator(self.anthropic_api_key)
        self.ami_parser = AMIMetadataParser()
        self.metadata_writer = MetadataWriter()
        self.exif_handler = ExifMetadataHandler()

        # Tool registry
        self.tools = {
            'research_historical_context': self.research_historical_context,
            'assess_significance': self.assess_significance,
            'generate_biographies': self.generate_biographies,
            'parse_ami_filename': self.parse_ami_filename,
            'write_metadata': self.write_metadata,
            'update_metadata': self.update_metadata,
            'read_metadata': self.read_metadata,
            'read_image_exif': self.read_image_exif,
            'write_image_exif': self.write_image_exif,
            'create_enriched_copy': self.create_enriched_copy
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

    async def parse_ami_filename(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Parse AMI filename and extract metadata"""
        filename = params.get('filename', '')

        logger.info(f"Parsing AMI filename: {filename}")

        try:
            result = self.ami_parser.parse(filename)

            # Add formatted summary and archipelago fields
            if result.get('parsed'):
                result['summary'] = self.ami_parser.format_metadata_summary(result)
                result['archipelago_fields'] = self.ami_parser.get_archipelago_fields(result)

            logger.info(f"Parsed AMI filename successfully: {result.get('parsed', False)}")
            return result
        except Exception as e:
            logger.error(f"Error parsing AMI filename: {e}")
            return {
                "filename": filename,
                "parsed": False,
                "error": str(e),
                "_fallback": True
            }

    async def write_metadata(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Write metadata to a JSON file"""
        file_path = params.get('file_path', '')
        metadata = params.get('metadata', {})
        output_filename = params.get('output_filename')

        logger.info(f"Writing metadata for file: {file_path}")

        try:
            result = self.metadata_writer.write_metadata(file_path, metadata, output_filename)
            logger.info(f"Metadata write result: {result.get('success', False)}")
            return result
        except Exception as e:
            logger.error(f"Error writing metadata: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }

    async def update_metadata(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing metadata file"""
        metadata_file_path = params.get('metadata_file_path', '')
        updates = params.get('updates', {})
        merge = params.get('merge', True)

        logger.info(f"Updating metadata file: {metadata_file_path}")

        try:
            result = self.metadata_writer.update_metadata(metadata_file_path, updates, merge)
            logger.info(f"Metadata update result: {result.get('success', False)}")
            return result
        except Exception as e:
            logger.error(f"Error updating metadata: {e}")
            return {
                "success": False,
                "error": str(e),
                "metadata_file_path": metadata_file_path
            }

    async def read_metadata(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read metadata from a JSON file"""
        metadata_file_path = params.get('metadata_file_path', '')

        logger.info(f"Reading metadata from: {metadata_file_path}")

        try:
            result = self.metadata_writer.read_metadata(metadata_file_path)
            logger.info(f"Metadata read result: {result.get('success', False)}")
            return result
        except Exception as e:
            logger.error(f"Error reading metadata: {e}")
            return {
                "success": False,
                "error": str(e),
                "metadata_file_path": metadata_file_path
            }

    async def read_image_exif(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read EXIF metadata from an image file"""
        image_path = params.get('image_path', '')

        logger.info(f"Reading EXIF from image: {image_path}")

        try:
            result = self.exif_handler.read_exif(image_path)
            logger.info(f"EXIF read result: {result.get('success', False)}")
            return result
        except Exception as e:
            logger.error(f"Error reading EXIF: {e}")
            return {
                "success": False,
                "error": str(e),
                "image_path": image_path
            }

    async def write_image_exif(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Write metadata to image EXIF tags"""
        image_path = params.get('image_path', '')
        metadata = params.get('metadata', {})
        output_path = params.get('output_path')

        logger.info(f"Writing EXIF to image: {image_path}")

        try:
            result = self.exif_handler.write_exif(image_path, metadata, output_path)
            logger.info(f"EXIF write result: {result.get('success', False)}")
            return result
        except Exception as e:
            logger.error(f"Error writing EXIF: {e}")
            return {
                "success": False,
                "error": str(e),
                "image_path": image_path
            }

    async def create_enriched_copy(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a copy of image with embedded metadata"""
        image_path = params.get('image_path', '')
        metadata = params.get('metadata', {})
        output_dir = params.get('output_dir')
        suffix = params.get('suffix', '_enriched')

        logger.info(f"Creating enriched copy of: {image_path}")

        try:
            result = self.exif_handler.create_copy_with_metadata(
                image_path, metadata, output_dir, suffix
            )
            logger.info(f"Enriched copy result: {result.get('success', False)}")
            return result
        except Exception as e:
            logger.error(f"Error creating enriched copy: {e}")
            return {
                "success": False,
                "error": str(e),
                "image_path": image_path
            }

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
            },
            {
                "name": "parse_ami_filename",
                "description": "Parse AMI Master naming convention filename and extract metadata including master identifier, document type, medium, date, sender, recipient, and Archipelago field mappings",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "The filename to parse (e.g., MSALTMEBA00100004.00_(01_02_0071)_LT_MIX_1990_BK MODI_TO_REVSNGOENKA.JPG)"
                        }
                    },
                    "required": ["filename"],
                    "additionalProperties": False
                }
            },
            {
                "name": "write_metadata",
                "description": "Write enriched metadata to a JSON file alongside the original document. Creates a metadata JSON file in the same directory as the original file.",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the original document file (e.g., /data/documents/letter001.jpg)"
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Metadata dictionary to write (e.g., document_type, sender, recipient, date, subjects, summary, etc.)"
                        },
                        "output_filename": {
                            "type": "string",
                            "description": "Optional custom output filename (defaults to {original}_metadata.json)"
                        }
                    },
                    "required": ["file_path", "metadata"],
                    "additionalProperties": False
                }
            },
            {
                "name": "update_metadata",
                "description": "Update an existing metadata JSON file by merging new fields or replacing entirely",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "metadata_file_path": {
                            "type": "string",
                            "description": "Path to the existing metadata JSON file"
                        },
                        "updates": {
                            "type": "object",
                            "description": "Dictionary of fields to update or add"
                        },
                        "merge": {
                            "type": "boolean",
                            "description": "If true, merge with existing data; if false, replace entirely (default: true)"
                        }
                    },
                    "required": ["metadata_file_path", "updates"],
                    "additionalProperties": False
                }
            },
            {
                "name": "read_metadata",
                "description": "Read metadata from an existing JSON file",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "metadata_file_path": {
                            "type": "string",
                            "description": "Path to the metadata JSON file to read"
                        }
                    },
                    "required": ["metadata_file_path"],
                    "additionalProperties": False
                }
            },
            {
                "name": "read_image_exif",
                "description": "Read EXIF/IPTC metadata from an image file (JPEG, TIFF, PNG). Returns camera info, timestamps, and embedded metadata.",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "Path to the image file (e.g., /data/images/photo.jpg)"
                        }
                    },
                    "required": ["image_path"],
                    "additionalProperties": False
                }
            },
            {
                "name": "write_image_exif",
                "description": "Write enriched metadata to image EXIF tags. Embeds title, author, date, copyright, and summary into the image file.",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "Path to the source image file"
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Metadata to embed (title, author, date, summary, etc.)"
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Optional output path (defaults to overwrite original)"
                        }
                    },
                    "required": ["image_path", "metadata"],
                    "additionalProperties": False
                }
            },
            {
                "name": "create_enriched_copy",
                "description": "Create a copy of an image with embedded EXIF metadata AND a companion JSON file. This creates both an enriched image file and a metadata.json sidecar file.",
                "agentId": self.agent_id,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "Path to the original image file"
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Enriched metadata to embed and save (document_type, sender, recipient, summary, etc.)"
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "Optional output directory (defaults to same as original)"
                        },
                        "suffix": {
                            "type": "string",
                            "description": "Suffix for output filename (default: '_enriched')"
                        }
                    },
                    "required": ["image_path", "metadata"],
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
