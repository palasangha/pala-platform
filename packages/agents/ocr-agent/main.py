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
import tempfile
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
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "ws://localhost:4000")

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
from services.pdf_service import PDFService

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
                    "description": "Path to the image file to process (optional if image_data provided)"
                },
                "image_data": {
                    "type": "string",
                    "description": "Base64-encoded image data (optional if image_path provided)"
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
            "required": []
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
]


def _get_provider(provider_name: str):
    """Get OCR provider instance by name"""
    logger.info(f"[TRACE] _get_provider called with provider_name: {provider_name}")
    
    provider_map = {
        "tesseract": TesseractOCRProvider,
        "ollama": OllamaProvider,
        "lmstudio": LMStudioProvider,
    }
    
    logger.info(f"[TRACE] Available providers: {list(provider_map.keys())}")
    
    provider_class = provider_map.get(provider_name.lower())
    if not provider_class:
        logger.error(f"[TRACE] Unknown provider: {provider_name}")
        raise ValueError(f"Unknown provider: {provider_name}")
    
    logger.info(f"[TRACE] Creating instance of provider class: {provider_class.__name__}")
    instance = provider_class()
    logger.info(f"[TRACE] Provider instance created successfully: {instance}")
    return instance


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


async def _extract_text_for_file(provider, file_path: str, language: str) -> Dict[str, Any]:
    """
    Extract text for one file, with explicit PDF page conversion support.
    """
    source_path = Path(file_path)
    
    logger.info(f"[TRACE] _extract_text_for_file called: file_path={file_path}, language={language}")
    logger.info(f"[TRACE] Provider type: {type(provider).__name__}")
    logger.info(f"[TRACE] File exists: {source_path.exists()}")

    if PDFService.is_pdf(str(source_path)):
        logger.info(f"[TRACE] PDF detected, converting pages before OCR: {source_path}")
        images = PDFService.pdf_to_images(str(source_path))
        if not images:
            raise ValueError(f"Failed to convert PDF to images: {source_path}")

        page_texts = []
        confidences = []

        with tempfile.TemporaryDirectory(prefix="ocr_pdf_") as temp_dir:
            for page_index, image in enumerate(images, start=1):
                page_path = Path(temp_dir) / f"page_{page_index}.jpg"
                image.convert("RGB").save(page_path, format="JPEG", quality=95)
                
                logger.info(f"[TRACE] Processing PDF page {page_index}, saved to: {page_path}")
                page_result = await provider.extract_text(str(page_path), language)
                page_text = (page_result.get("text") or "").strip()
                logger.info(f"[TRACE] Page {page_index} extraction result - text_length={len(page_text)}, confidence={page_result.get('confidence')}")
                if page_text:
                    page_texts.append(f"--- Page {page_index} ---\n{page_text}")
                confidences.append(float(page_result.get("confidence", 0.0) or 0.0))

        combined_text = "\n\n".join(page_texts).strip()
        if not combined_text:
            raise ValueError(
                f"OCR returned empty text for PDF: {source_path.name}. "
                "Check model/provider support for document OCR."
            )

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        provider_name = provider.__class__.__name__.replace("Provider", "").lower()
        logger.info(f"[TRACE] PDF processing complete - pages={len(images)}, combined_text_length={len(combined_text)}, provider={provider_name}")
        return {
            "text": combined_text,
            "confidence": avg_confidence,
            "word_confidence": [],
            "language": language,
            "metadata": {
                "provider": provider_name,
                "source_file": str(source_path),
                "source_type": "pdf",
                "pages": len(images),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    logger.info(f"[TRACE] Image file detected (not PDF), calling provider.extract_text()")
    result = await provider.extract_text(str(source_path), language)
    text = (result.get("text") or "").strip()
    provider_used = result['metadata'].get('provider', 'unknown')
    logger.info(f"[TRACE] Image extraction result - text_length={len(text)}, confidence={result.get('confidence')}, provider={provider_used}")
    logger.info(f"[TRACE] TEXT CONTENT (first 200 chars): {text[:200]}")
    if not text:
        raise ValueError(
            f"OCR returned empty text for file: {source_path.name}. "
            "Try a different provider/model or higher-quality input."
        )
    return result


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


async def _progress_wrapper(coro, operation_name: str):
    """Wrap async operation with periodic progress logging"""
    import asyncio
    
    logger.info(f"[PROGRESS] Starting: {operation_name}")
    
    task = asyncio.create_task(coro)
    start_time = asyncio.get_event_loop().time()
    
    # Log progress every 30 seconds
    while not task.done():
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=30)
        except asyncio.TimeoutError:
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.info(f"[PROGRESS] {operation_name} still processing... ({elapsed:.0f} seconds elapsed)")
            continue
    
    elapsed = asyncio.get_event_loop().time() - start_time
    logger.info(f"[PROGRESS] Completed: {operation_name} (took {elapsed:.1f} seconds)")
    
    return await task


async def handle_extract_text(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract text from a single image
    
    Args:
        params: Dictionary containing:
            - image_path: Path to image file OR
            - image_data: Base64-encoded image data
            - provider: OCR provider (default: 'tesseract')
            - language: Language code (default: 'eng')
    
    Returns:
        Dictionary containing extracted text and metadata
    """
    image_path = params.get("image_path")
    image_data = params.get("image_data")
    file_name = params.get("file_name", "document")
    provider_name = params.get("provider", "tesseract")
    language = params.get("language", "eng")
    
    logger.info(f"[TRACE] handle_extract_text called with params keys: {list(params.keys())}")
    logger.info(f"[TRACE] Parsed - has_image_path={bool(image_path)}, has_image_data={bool(image_data)}, file_name={file_name}, provider={provider_name}, language={language}")
    
    if not image_path and not image_data:
        raise ValueError("Either image_path or image_data is required")
    
    # If base64 data provided, save to temp file
    if image_data and not image_path:
        import base64
        import os as os_module
        logger.info(f"[TRACE] Decoding base64 image data (length: {len(image_data)})")
        try:
            # Remove data URL prefix if present
            if ',' in image_data:
                image_data = image_data.split(',', 1)[1]
            
            decoded = base64.b64decode(image_data)
            logger.info(f"[TRACE] Decoded image size: {len(decoded)} bytes")
            
            # Get file extension from file_name or use default
            _, ext = os_module.path.splitext(file_name)
            if not ext:
                ext = '.png'
            logger.info(f"[TRACE] Using file extension: {ext}")
            
            # Create temp file with proper extension
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            temp_file.write(decoded)
            temp_file.close()
            image_path = temp_file.name
            logger.info(f"[TRACE] Saved to temp file: {image_path}")
        except Exception as e:
            logger.error(f"[TRACE] Failed to decode base64 image: {e}")
            raise ValueError(f"Failed to decode base64 image data: {e}")
    
    try:
        logger.info(f"[TRACE] Getting provider instance for: {provider_name}")
        provider = _get_provider(provider_name)
        logger.info(f"[TRACE] Provider instance created: {type(provider).__name__}")
        
        logger.info(f"[TRACE] Starting extraction from file: {image_path}")
        # Wrap extraction with progress logging every 30 seconds
        result = await _progress_wrapper(
            _extract_text_for_file(provider, image_path, language),
            f"OCR extraction using {provider_name}"
        )
        logger.info(f"[TRACE] Extraction successful, extracted text length: {len(result.get('text', ''))}")
        logger.info(f"[TRACE] Result metadata: provider={result['metadata'].get('provider')}, confidence={result.get('confidence')}")
        return result
    except Exception as e:
        logger.error(f"[TRACE] Error in extract_text: {e}", exc_info=True)
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
                
                result = await _extract_text_for_file(provider, str(file_path), language)
                
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
    tool_name = params.get("name") or params.get("toolName")
    arguments = params.get("arguments", {})
    
    logger.info(f"[TRACE] handle_tools_invoke called - tool_name={tool_name}")
    logger.info(f"[TRACE] Full params received: {params}")
    logger.info(f"[TRACE] Arguments: {arguments}")
    logger.info(f"Invoking tool: {tool_name} with args: {arguments}")
    
    try:
        if tool_name == "extract_text":
            logger.info(f"[TRACE] Calling handle_extract_text with arguments: {arguments}")
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
    tool_defs = []
    for tool in TOOLS:
        tool_def = dict(tool)
        tool_def["agentId"] = AGENT_ID
        tool_defs.append(tool_def)

    request = make_request(
        "tools/register",
        {"tools": tool_defs},
        f"reg-{uuid.uuid4()}"
    )
    await websocket.send(request)
    logger.info(f"Registered {len(tool_defs)} OCR tools")


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

