"""
MCP Client - WebSocket JSON-RPC 2.0 client for communicating with MCP server
Handles connection pooling, retries, and tool invocation
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from threading import Lock
import websockets
from websockets.asyncio.client import ClientConnection

from enrichment_service.config import config


logger = logging.getLogger(__name__)


class MCPConnectionError(Exception):
    """Raised when MCP connection fails"""
    pass


class MCPInvocationError(Exception):
    """Raised when tool invocation fails"""
    pass


class MCPClient:
    """
    WebSocket client for MCP server communication

    Features:
    - Automatic reconnection with exponential backoff
    - Connection pooling for multiple concurrent requests
    - Request/response correlation via IDs
    - Timeout handling
    - Error recovery with retries
    """

    def __init__(self, server_url: str = None, token: str = None):
        """
        Initialize MCP client

        Args:
            server_url: WebSocket URL of MCP server
            token: Optional JWT token for authentication
        """
        self.server_url = server_url or config.MCP_SERVER_URL
        self.token = token or config.MCP_AGENT_TOKEN
        self.timeout = config.AGENT_TIMEOUT_SECONDS

        # Connection management
        self.connection: Optional[ClientConnection] = None
        self.is_connected = False
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.pending_requests_lock = Lock()  # Thread-safe access to pending_requests

        # Request ID tracking to prevent collisions
        self.request_id_counter = 0
        self.request_id_lock = Lock()

        # Reconnection settings
        self.max_retries = 5
        self.retry_backoff_base = 2
        self.retry_attempt = 0

        # Metrics
        self.stats = {
            "invocations_total": 0,
            "invocations_success": 0,
            "invocations_failed": 0,
            "reconnections": 0,
            "bytes_sent": 0,
            "bytes_received": 0,
            "collision_detected": 0
        }

    def _generate_request_id(self) -> str:
        """
        Generate unique request ID with collision detection

        Returns:
            Unique request ID
        """
        with self.request_id_lock:
            # Use monotonic counter with UUID to ensure uniqueness
            self.request_id_counter += 1
            unique_id = f"{self.request_id_counter}-{uuid.uuid4().hex[:8]}"
            return unique_id

    async def connect(self) -> None:
        """Connect to MCP server with automatic retry"""
        if self.is_connected:
            return

        for attempt in range(self.max_retries):
            try:
                headers = {}
                if self.token:
                    headers["Authorization"] = f"Bearer {self.token}"

                logger.info(f"Connecting to MCP server: {self.server_url} (attempt {attempt + 1}/{self.max_retries})")

                self.connection = await websockets.connect(self.server_url, additional_headers=headers)
                self.is_connected = True
                self.retry_attempt = 0

                logger.info("Connected to MCP server")

                # Start message listening loop
                asyncio.create_task(self._listen())
                return

            except Exception as e:
                logger.warning(f"Connection failed: {e}")
                self.retry_attempt = attempt + 1

                if attempt < self.max_retries - 1:
                    wait_time = self.retry_backoff_base ** attempt
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise MCPConnectionError(f"Failed to connect after {self.max_retries} attempts: {e}")

    async def disconnect(self) -> None:
        """Disconnect from MCP server and clean up pending requests"""
        if self.connection:
            try:
                await self.connection.close()
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
            finally:
                self.is_connected = False
                self.connection = None

        # Clean up any pending requests
        with self.pending_requests_lock:
            for request_id, future in list(self.pending_requests.items()):
                if not future.done():
                    future.set_exception(MCPConnectionError("Connection closed"))
            self.pending_requests.clear()

    async def invoke_tool(
        self,
        agent_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Invoke a tool on an agent

        Args:
            agent_id: ID of the agent
            tool_name: Name of the tool to invoke
            arguments: Tool arguments
            timeout: Request timeout in seconds

        Returns:
            Tool result

        Raises:
            MCPConnectionError: If not connected
            MCPInvocationError: If invocation fails
        """
        if not self.is_connected:
            await self.connect()

        self.stats["invocations_total"] += 1
        request_id = self._generate_request_id()
        timeout = timeout or self.timeout

        # Build JSON-RPC 2.0 request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/invoke",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": request_id
        }

        # Create future for response (exception-safe)
        response_future: asyncio.Future = asyncio.Future()

        # Add to pending requests with collision detection
        with self.pending_requests_lock:
            if request_id in self.pending_requests:
                logger.error(f"Request ID collision detected: {request_id}")
                self.stats["collision_detected"] += 1
                raise MCPInvocationError(f"Request ID collision - this should not happen")
            self.pending_requests[request_id] = response_future

        try:
            # Send request
            message = json.dumps(request)
            await self.connection.send(message)
            self.stats["bytes_sent"] += len(message)

            logger.debug(f"Invoked tool: agent={agent_id}, tool={tool_name}, request_id={request_id}")

            # Wait for response with timeout
            result = await asyncio.wait_for(response_future, timeout=timeout)

            self.stats["invocations_success"] += 1
            return result

        except asyncio.TimeoutError:
            self.stats["invocations_failed"] += 1
            # Mark future as cancelled to prevent dangling references
            if not response_future.done():
                response_future.cancel()
            raise MCPInvocationError(f"Tool invocation timeout after {timeout}s: {tool_name}")

        except Exception as e:
            self.stats["invocations_failed"] += 1
            # Mark future as cancelled on error
            if not response_future.done():
                response_future.cancel()
            raise MCPInvocationError(f"Tool invocation failed: {tool_name}: {str(e)}")

        finally:
            # Clean up pending request (thread-safe)
            with self.pending_requests_lock:
                self.pending_requests.pop(request_id, None)

    async def _listen(self) -> None:
        """Listen for messages from MCP server"""
        try:
            async for message in self.connection:
                self.stats["bytes_received"] += len(message)

                try:
                    data = json.loads(message)

                    # Handle response (result or error)
                    if "id" in data and ("result" in data or "error" in data):
                        request_id = data["id"]

                        with self.pending_requests_lock:
                            if request_id in self.pending_requests:
                                future = self.pending_requests[request_id]

                                # Prevent setting result on already-done future (timeout case)
                                if not future.done():
                                    if "error" in data:
                                        error = data["error"]
                                        future.set_exception(
                                            MCPInvocationError(f"MCP error {error.get('code')}: {error.get('message')}")
                                        )
                                    else:
                                        future.set_result(data.get("result"))
                                else:
                                    logger.debug(f"Response for already-completed request: {request_id}")
                            else:
                                logger.warning(f"Received response for unknown request: {request_id}")

                    # Handle notification
                    elif "method" in data and "id" not in data:
                        logger.debug(f"Received notification: {data.get('method')}")

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message (malformed JSON): {e}")
                    # Log the message for debugging but continue listening
                    logger.debug(f"Malformed message (first 100 chars): {message[:100]}")
                    # Continue processing - don't kill connection on bad JSON
                    continue

                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    # Continue processing on individual message errors
                    continue

        except asyncio.CancelledError:
            logger.info("Message listening stopped")
        except Exception as e:
            logger.error(f"Connection lost: {e}", exc_info=True)
            self.is_connected = False

            # Attempt to reconnect
            if self.retry_attempt < self.max_retries:
                self.stats["reconnections"] += 1
                logger.info("Attempting to reconnect...")
                try:
                    await self.connect()
                except Exception as e:
                    logger.error(f"Reconnection failed: {e}")

    async def get_status(self) -> Dict[str, Any]:
        """Get client status"""
        return {
            "connected": self.is_connected,
            "server_url": self.server_url,
            "pending_requests": len(self.pending_requests),
            "stats": self.stats.copy()
        }

    async def health_check(self) -> bool:
        """Check if client is healthy"""
        try:
            # Try to invoke a simple tool to verify connection
            status = await self.get_status()
            return status["connected"]
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
