#!/usr/bin/env python3
"""
OCR Agent - Enhanced

Stateful agent for extracting text from images/documents with multi-provider support.
Supports folder-based batch processing with job tracking.

Features:
- Multiple OCR providers (Tesseract, Ollama, LM Studio)
- Non-blocking folder processing with job IDs
- Real-time job status polling
- Results streaming as files are processed
"""

import asyncio
import json
import logging
import os
import sys
import uuid
import websockets
import importlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
AGENT_ID = "ocr-agent"
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "ws://localhost:3000")

# Dynamically import job registry from shared
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))
try:
    from job_registry import JobRegistry
    from job_models import Job
except ImportError:
    logger.error("Failed to import job registry from shared - this will cause issues")
    raise

# Initialize job registry
agent_dir = Path(__file__).parent
data_dir = agent_dir / 'data'
data_dir.mkdir(exist_ok=True)
job_registry = JobRegistry(persist_dir=str(data_dir / 'jobs'))

# Import providers
from providers.tesseract_provider import TesseractOCRProvider
from providers.ollama_provider import OllamaProvider
from providers.lmstudio_provider import LMStudioProvider

# Tool definitions
TOOLS = [
    {
        "name": "extract_text",
        "description": "Extract text from a single image or document using OCR",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the image file to process"
                },
                "provider": {
                    "type": "string",
                    "description": "OCR provider to use",
                    "enum": ["tesseract", "ollama", "lmstudio"],
                    "default": "tesseract"
                },
                "language": {
                    "type": "string",
                    "description": "Language code (e.g., 'eng', 'fra', 'deu')",
                    "default": "eng"
                }
            },
            "required": ["image_path"]
        }
    },
    {
        "name": "process_folder",
        "description": "Process all images in a folder and return a job ID for status tracking",
        "inputSchema": {
            "type": "object",
            "properties": {
                "folder_path": {
                    "type": "string",
                    "description": "Path to folder containing images"
                },
                "provider": {
                    "type": "string",
                    "description": "OCR provider to use",
                    "enum": ["tesseract", "ollama", "lmstudio"],
                    "default": "tesseract"
                },
                "language": {
                    "type": "string",
                    "description": "Language code",
                    "default": "eng"
                },
                "file_pattern": {
                    "type": "string",
                    "description": "File pattern to match (e.g., '*.png', '*.*')",
                    "default": "*.*"
                }
            },
            "required": ["folder_path"]
        }
    },
    {
        "name": "get_ocr_status",
        "description": "Get the current status of an OCR folder processing job",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "string",
                    "description": "Job ID returned from process_folder"
                }
            },
            "required": ["job_id"]
        }
    },
    {
        "name": "get_ocr_results",
        "description": "Get results from a completed OCR job",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "string",
                    "description": "Job ID"
                },
                "file_name": {
                    "type": "string",
                    "description": "Specific file name to get results for (optional)"
                }
            },
            "required": ["job_id"]
        }
    }


def _get_provider(provider_name: str):
    """Get OCR provider instance by name"""
    provider_map = {
        "tesseract": TesseractOCRProvider,
        "ollama": OllamaProvider,
        "lmstudio": LMStudioProvider,
    }
    
    provider_class = provider_map.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider_name}")
    
    return provider_class()


def _get_image_files(folder_path: str, pattern: str = "*.*") -> list:
    """Get list of image files in folder"""
    folder = Path(folder_path)
    if not folder.exists():
        return []
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.gif', '.bmp', '.pdf'}
    files = []
    
    for file in folder.glob(pattern):
        if file.is_file() and file.suffix.lower() in image_extensions:
            files.append(file)
    
    return sorted(files)


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
    Extract text from a single image
    
    Args:
        params: Dictionary containing:
            - image_path: Path to image file
            - provider: OCR provider (default: 'tesseract')
            - language: Language code (default: 'eng')
    
    Returns:
        Dictionary containing extracted text and metadata
    """
    image_path = params.get("image_path")
    provider_name = params.get("provider", "tesseract")
    language = params.get("language", "eng")
    
    if not image_path:
        raise ValueError("image_path is required")
    
    try:
        provider = _get_provider(provider_name)
        result = await provider.extract_text(image_path, language)
        return result
    except Exception as e:
        logger.error(f"Error in extract_text: {e}", exc_info=True)
        raise


async def handle_process_folder(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process all images in a folder and return job ID
    
    Args:
        params: Dictionary containing:
            - folder_path: Path to folder
            - provider: OCR provider (default: 'tesseract')
            - language: Language code (default: 'eng')
            - file_pattern: File pattern (default: '*.*')
    
    Returns:
        Dictionary with job_id and initial status
    """
    folder_path = params.get("folder_path")
    provider_name = params.get("provider", "tesseract")
    language = params.get("language", "eng")
    file_pattern = params.get("file_pattern", "*.*")
    
    if not folder_path:
        raise ValueError("folder_path is required")
    
    folder = Path(folder_path)
    if not folder.exists():
        raise ValueError(f"Folder not found: {folder_path}")
    
    # Get list of image files
    files = _get_image_files(str(folder), file_pattern)
    if not files:
        raise ValueError(f"No image files found in {folder_path} matching {file_pattern}")
    
    # Create job
    job_id = await job_registry.create_job(
        job_type="ocr_folder",
        params={
            "folder_path": str(folder),
            "provider": provider_name,
            "language": language,
            "file_pattern": file_pattern
        }
    )
    
    # Update job with file count
    await job_registry.update_job_status(
        job_id,
        "pending",
        files_total=len(files),
        current_file=None
    )
    
    logger.info(f"Created job {job_id} for processing {len(files)} files")
    
    # Start background processing (don't wait)
    asyncio.create_task(_process_folder_background(job_id, files, provider_name, language))
    
    return {
        "job_id": job_id,
        "status": "pending",
        "files_to_process": len(files),
        "message": f"Job {job_id} created for processing {len(files)} files"
    }


async def _process_folder_background(job_id: str, files: list, provider_name: str, language: str):
    """Background task to process folder files"""
    try:
        provider = _get_provider(provider_name)
        
        # Update status to processing
        await job_registry.update_job_status(job_id, "processing")
        
        # Process each file
        for file_path in files:
            try:
                await job_registry.update_job_status(
                    job_id,
                    "processing",
                    current_file=file_path.name
                )
                
                logger.info(f"Processing {file_path.name} for job {job_id}")
                
                result = await provider.extract_text(str(file_path), language)
                
                await job_registry.append_result(
                    job_id,
                    file_path.name,
                    result.get("text", ""),
                    result.get("metadata", {}).get("provider", provider_name),
                    result.get("confidence", 0.0)
                )
                
                logger.info(f"Completed {file_path.name} for job {job_id}")
                
            except Exception as e:
                logger.error(f"Error processing {file_path.name}: {e}")
                await job_registry.append_error(job_id, file_path.name, str(e))
        
        # Mark job as completed
        await job_registry.update_job_status(job_id, "completed")
        logger.info(f"Completed job {job_id}")
        
    except Exception as e:
        logger.error(f"Fatal error in background processing for job {job_id}: {e}", exc_info=True)
        await job_registry.mark_failed(job_id, str(e))


async def handle_get_ocr_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get current status of an OCR job
    
    Args:
        params: Dictionary containing:
            - job_id: Job ID
    
    Returns:
        Dictionary with job status and progress
    """
    job_id = params.get("job_id")
    if not job_id:
        raise ValueError("job_id is required")
    
    job_dict = await job_registry.get_job_dict(job_id)
    if not job_dict:
        raise ValueError(f"Job not found: {job_id}")
    
    return job_dict


async def handle_get_ocr_results(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get results from an OCR job
    
    Args:
        params: Dictionary containing:
            - job_id: Job ID
            - file_name: Specific file (optional)
    
    Returns:
        Dictionary with results
    """
    job_id = params.get("job_id")
    file_name = params.get("file_name")
    
    if not job_id:
        raise ValueError("job_id is required")
    
    job_dict = await job_registry.get_job_dict(job_id)
    if not job_dict:
        raise ValueError(f"Job not found: {job_id}")
    
    if file_name:
        # Filter results for specific file
        results = [r for r in job_dict["results"] if r["file_name"] == file_name]
        job_dict["results"] = results
    
    return job_dict


async def handle_tools_invoke(params: Dict[str, Any], request_id: str) -> str:
    """Handle tools/invoke requests"""
    tool_name = params.get("toolName")
    arguments = params.get("arguments", {})
    
    logger.info(f"Invoking tool: {tool_name} with args: {arguments}")
    
    try:
        if tool_name == "extract_text":
            result = await handle_extract_text(arguments)
        elif tool_name == "process_folder":
            result = await handle_process_folder(arguments)
        elif tool_name == "get_ocr_status":
            result = await handle_get_ocr_status(arguments)
        elif tool_name == "get_ocr_results":
            result = await handle_get_ocr_results(arguments)
        else:
            return make_error(-32601, f"Unknown tool: {tool_name}", request_id)
        
        return make_response(result, request_id)
        
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
            "version": "2.0.0",
            "description": "Extract text from images and scanned documents with multi-provider support",
            "author": "Pala Platform",
            "capabilities": [
                "single_image_ocr",
                "batch_folder_processing",
                "job_status_tracking",
                "multi_provider_support"
            ]
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
    logger.info(f"Starting OCR Agent v2, connecting to {MCP_SERVER_URL}")
    
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

