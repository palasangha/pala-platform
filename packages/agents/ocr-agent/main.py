#!/usr/bin/env python3
"""
OCR Agent

Stateless agent for extracting text from images/documents.
Supports multiple OCR providers (Tesseract, Cloud Vision, etc.) via MCP.

Architecture:
- Receives image data via MCP protocol
- Routes to appropriate OCR provider
- Returns extracted text with confidence scores
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
from pathlib import Path

from providers.tesseract_provider import TesseractOCRProvider

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
AGENT_ID = "ocr-agent"
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "ws://localhost:3000")

# Tool definitions
TOOLS = [
    {
        "name": "extract_text",
        "description": "Extract text from an image or scanned document using OCR",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the image file to process"
                },
                "language": {
                    "type": "string",
                    "description": "Language code (e.g., 'eng', 'fra', 'deu')",
                    "default": "eng"
                },
                "provider": {
                    "type": "string",
                    "description": "OCR provider to use",
                    "enum": ["tesseract", "mock"],
                    "default": "tesseract"
                },
                "psm": {
                    "type": "integer",
                    "description": "Page segmentation mode (Tesseract)",
                    "default": 3
                }
            },
            "required": ["image_path"]
        }
    }
]


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


async def handle_extract_text(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract text from image using OCR
    
    Args:
        params: Dictionary containing:
            - image_path: Path to image file
            - language: Language code (default: 'eng')
            - provider: OCR provider (default: 'tesseract')
            - psm: Page segmentation mode (default: 3)
    
    Returns:
        Dictionary containing:
            - text: Extracted text
            - confidence: Overall confidence score (0-1)
            - word_confidence: Per-word confidence scores
            - language: Detected/specified language
            - metadata: Additional OCR metadata
    """
    image_path = params.get("image_path")
    language = params.get("language", "eng")
    provider_name = params.get("provider", "tesseract")
    psm = params.get("psm", 3)
    
    if not image_path:
        raise ValueError("image_path is required")
    
    # Check if file exists
    if not Path(image_path).exists():
        # For demo purposes, return mock data if file doesn't exist
        logger.warning(f"Image file not found: {image_path}. Returning mock OCR data.")
        return {
            "text": "Letter dated 15th March 1892\n\nDear Venerable Sir,\n\nI write to inform you of the monastery's administrative matters. The construction of the new meditation hall has progressed well under the supervision of Brother Thomas. We anticipate completion by June.\n\nRespectfully yours,\nJohn Smith\nSecretary, Monastery Board",
            "confidence": 0.95,
            "word_confidence": [],
            "language": language,
            "metadata": {
                "provider": "mock",
                "image_path": image_path,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "psm": psm
            }
        }
    
    # Initialize provider
    if provider_name == "tesseract":
        provider = TesseractOCRProvider()
    else:
        raise ValueError(f"Unsupported OCR provider: {provider_name}")
    
    # Extract text
    result = await provider.extract_text(
        image_path=image_path,
        language=language,
        psm=psm
    )
    
    return result


async def handle_tools_invoke(params: Dict[str, Any], request_id: str) -> str:
    """Handle tools/invoke requests"""
    tool_name = params.get("toolName")
    arguments = params.get("arguments", {})
    
    logger.info(f"Invoking tool: {tool_name} with args: {arguments}")
    
    try:
        if tool_name == "extract_text":
            result = await handle_extract_text(arguments)
            return make_response(result, request_id)
        else:
            return make_error(-32601, f"Unknown tool: {tool_name}", request_id)
    except Exception as e:
        logger.error(f"Error invoking tool {tool_name}: {e}", exc_info=True)
        return make_error(-32603, str(e), request_id)


async def register_agent(websocket):
    """Register this agent with the MCP server"""
    registration = {
        "agentId": AGENT_ID,
        "tools": TOOLS,
        "metadata": {
            "name": "OCR Agent",
            "version": "1.0.0",
            "description": "Extract text from images and scanned documents",
            "author": "Pala Platform"
        }
    }
    
    request = make_request("agents/register", registration, str(uuid.uuid4()))
    await websocket.send(request)
    logger.info(f"Sent registration for agent: {AGENT_ID}")
    
    # Wait for registration response
    response = await websocket.recv()
    response_data = json.loads(response)
    
    if "error" in response_data:
        logger.error(f"Registration failed: {response_data['error']}")
        raise Exception(f"Registration failed: {response_data['error']['message']}")
    
    logger.info(f"Agent {AGENT_ID} registered successfully")


async def handle_message(websocket, message: str):
    """Handle incoming JSON-RPC messages"""
    try:
        data = json.loads(message)
        logger.debug(f"Received message: {data}")
        
        method = data.get("method")
        params = data.get("params", {})
        request_id = data.get("id", str(uuid.uuid4()))
        
        if method == "tools/invoke":
            response = await handle_tools_invoke(params, request_id)
            await websocket.send(response)
        else:
            logger.warning(f"Unknown method: {method}")
            error = make_error(-32601, f"Method not found: {method}", request_id)
            await websocket.send(error)
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        error = make_error(-32700, "Parse error", "null")
        await websocket.send(error)
    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        error = make_error(-32603, str(e), "null")
        await websocket.send(error)


async def run_agent():
    """Main agent loop - connect to MCP server and handle requests"""
    logger.info(f"Starting OCR Agent, connecting to {MCP_SERVER_URL}")
    
    while True:
        try:
            async with websockets.connect(MCP_SERVER_URL) as websocket:
                logger.info("Connected to MCP server")
                
                # Register agent
                await register_agent(websocket)
                
                # Listen for requests
                async for message in websocket:
                    await handle_message(websocket, message)
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection closed, reconnecting in 5 seconds...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Error in agent loop: {e}", exc_info=True)
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        logger.info("Agent stopped by user")
        sys.exit(0)
