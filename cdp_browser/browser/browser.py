"""
Simple CDP Browser implementation.
"""
import asyncio
import json
import logging
import aiohttp
import requests
import websockets
from typing import Optional, Dict, Any, AsyncGenerator, List, Set
from websockets.client import WebSocketClientProtocol

from .exceptions import BrowserError, ConnectionError, CommandError
from .page import Page, EventEmitter

logger = logging.getLogger(__name__)

class Browser:
    """
    Simple Chrome DevTools Protocol browser controller.
    
    This class manages the connection to Chrome's DevTools Protocol and provides
    methods to create and control browser pages/tabs.
    
    Args:
        host: The hostname where Chrome is running.
        port: The port number for Chrome's remote debugging protocol.
        max_retries: Maximum number of connection retry attempts.
    """
    def __init__(self, host: str = "localhost", port: int = 9222, max_retries: int = 3) -> None:
        """Initialize a new Browser instance."""
        self.host = host
        self.port = port
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.command_id = 0
        self.max_retries = max_retries
        self._connected = False
        self._pages: List[Page] = []
        self._ws_lock = asyncio.Lock()
        self._events = EventEmitter()
        self._command_futures: Dict[int, asyncio.Future] = {}
        self._default_timeout = 30.0  # Default timeout in seconds
        self._ws_handler_task = None
        self._message_queue = asyncio.Queue()
        self._ready = asyncio.Event()
        self._command_ids: Dict[int, Page] = {}  # Track which page sent which command
        self._command_waiters: Dict[int, asyncio.Future] = {}  # Track command responses
        self._closing = False  # Flag to indicate browser is closing
        self._cleanup_lock = asyncio.Lock()  # Lock for cleanup operations

    async def connect(self):
        """Connect to Chrome DevTools and start message handler."""
        try:
            # Get the WebSocket debugger URL
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://{self.host}:{self.port}/json/version") as response:
                    data = await response.json()
                    ws_url = data["webSocketDebuggerUrl"]
            
            # Connect to the WebSocket
            self.websocket = await websockets.connect(ws_url)
            logger.info("Connected to Chrome")
            
            # Start WebSocket handler task before doing anything else
            self._ws_handler_task = asyncio.create_task(self._handle_websocket())
            
            # Wait for handler to be ready with timeout
            try:
                await asyncio.wait_for(self._ready.wait(), timeout=5.0)
                logger.debug("WebSocket handler is ready")
            except asyncio.TimeoutError:
                await self.close()
                raise ConnectionError("Timeout waiting for WebSocket handler to be ready")
            
        except Exception as e:
            logger.error(f"Failed to connect to Chrome: {e}")
            await self.close()
            raise

    async def __aenter__(self) -> 'Browser':
        """
        Async context manager entry.
        
        Returns:
            The Browser instance.
            
        Raises:
            ConnectionError: If unable to establish connection.
        """
        try:
            await self.connect()
            return self
        except Exception as e:
            raise ConnectionError(f"Failed to establish connection: {str(e)}")

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Async context manager exit.
        
        Ensures proper cleanup of WebSocket connection and all pages.
        """
        await self.close()

    async def close(self) -> None:
        """Close all pages and disconnect from Chrome."""
        async with self._cleanup_lock:
            if self._closing:
                return
            self._closing = True
            
            logger.debug("Closing browser...")
            
            # Cancel all pending command futures
            for future in self._command_futures.values():
                if not future.done():
                    future.cancel()
            self._command_futures.clear()
            
            # Cancel all command waiters
            for future in self._command_waiters.values():
                if not future.done():
                    future.cancel()
            self._command_waiters.clear()
            
            # Close all pages with timeout
            close_tasks = []
            for page in self._pages[:]:
                task = asyncio.create_task(self._close_page_with_timeout(page))
                close_tasks.append(task)
            
            if close_tasks:
                await asyncio.gather(*close_tasks, return_exceptions=True)
            self._pages.clear()
            
            # Cancel WebSocket handler task
            if self._ws_handler_task and not self._ws_handler_task.done():
                self._ws_handler_task.cancel()
                try:
                    await asyncio.shield(self._ws_handler_task)
                except (asyncio.CancelledError, Exception) as e:
                    logger.debug(f"WebSocket handler cancelled: {e}")
            
            # Close WebSocket connection
            if self.websocket:
                try:
                    await asyncio.wait_for(self.websocket.close(), timeout=5.0)
                except (asyncio.TimeoutError, Exception) as e:
                    logger.debug(f"Error closing WebSocket: {e}")
                finally:
                    self.websocket = None
            
            # Clear all remaining state
            self._command_ids.clear()
            self._events = EventEmitter()  # Create new event emitter
            self._connected = False
            self._closing = False
            logger.info("Browser closed")

    async def _close_page_with_timeout(self, page: Page) -> None:
        """Close a page with timeout handling."""
        try:
            await asyncio.wait_for(page.close(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout closing page {page.target_id}")
        except Exception as e:
            logger.warning(f"Error closing page: {e}")
        finally:
            if page in self._pages:
                self._pages.remove(page)

    async def _handle_websocket(self):
        """Background task to handle incoming WebSocket messages."""
        try:
            logger.debug("Starting WebSocket handler")
            self._ready.set()  # Signal that we're ready to handle messages
            
            while not self._closing:
                try:
                    if not self.websocket or self.websocket.closed:
                        if not self._closing:
                            logger.error("WebSocket connection closed unexpectedly")
                        break
                        
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    if self._closing:
                        break
                        
                    data = json.loads(message)
                    logger.debug(f"Received WebSocket message: {data}")
                    
                    # First check if this is a command response
                    if "id" in data:
                        cmd_id = data["id"]
                        if cmd_id in self._command_futures:
                            future = self._command_futures.pop(cmd_id)
                            if not future.done():
                                future.set_result(data)
                            continue
                    
                    # If not a command response, emit event
                    method = data.get("method")
                    if method:
                        await self._events.emit(method, data.get("params", {}))
                        
                        # Route events to appropriate page
                        session_id = data.get("sessionId")
                        if session_id:
                            for page in self._pages:
                                if page.session_id == session_id:
                                    await page._handle_event(data)
                                    break
                        elif method.startswith("Target."):
                            # Handle target-related events
                            params = data.get("params", {})
                            target_info = params.get("targetInfo", {})
                            target_id = target_info.get("targetId")
                            if target_id:
                                for page in self._pages:
                                    if page.target_id == target_id:
                                        await page._handle_event(data)
                                        break
                            
                except asyncio.TimeoutError:
                    continue
                except websockets.ConnectionClosed:
                    if not self._closing:
                        logger.error("WebSocket connection closed")
                    break
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode WebSocket message: {e}")
                    continue
                except Exception as e:
                    if not self._closing:
                        logger.error(f"Error handling WebSocket message: {e}")
                    
        except asyncio.CancelledError:
            logger.debug("WebSocket handler cancelled")
            raise
        except Exception as e:
            if not self._closing:
                logger.error(f"WebSocket handler error: {e}")
            raise
        finally:
            self._ready.clear()
            # Ensure all pending futures are cancelled
            for future in self._command_futures.values():
                if not future.done():
                    future.cancel()
            self._command_futures.clear()

    async def send_command(self, method: str, params: Optional[Dict] = None, timeout: Optional[float] = None) -> Dict:
        """Send a command to the browser and wait for the response with timeout."""
        if params is None:
            params = {}

        command_id = self._next_command_id()
        future = asyncio.Future()
        self._command_futures[command_id] = future

        try:
            # For flat protocol, if we have a sessionId, include it in the outer message
            session_id = params.pop("sessionId", None)
            message = {
                "id": command_id,
                "method": method,
                "params": params
            }

            if session_id:
                message["sessionId"] = session_id

            await self.websocket.send(json.dumps(message))

            try:
                response = await asyncio.wait_for(
                    future,
                    timeout=timeout or self._default_timeout
                )
                if "error" in response:
                    error = response["error"]
                    raise BrowserError(f"Command {method} failed: {error['message']}")
                return response.get("result", {})
            except asyncio.TimeoutError:
                raise BrowserError(f"Command {method} timed out after {timeout or self._default_timeout} seconds")

        except Exception as e:
            raise BrowserError(f"Failed to send command {method}: {str(e)}")
        finally:
            self._command_futures.pop(command_id, None)

    async def create_page(self) -> Page:
        """Create a new page (target) and return it."""
        logger.debug("Creating new page")
        # Create a new target (page)
        result = await self.send_command(
            "Target.createTarget",
            {"url": "about:blank"}
        )
        target_id = result["targetId"]
        logger.debug(f"Created target with ID: {target_id}")
        
        # Create and initialize the page
        page = Page(self, target_id)
        self._pages.append(page)  # Add to pages list before initialization
        await page.initialize()
        logger.debug(f"Page initialized with target ID: {target_id}")
        
        return page

    async def _handle_event(self, event: Dict[str, Any]) -> None:
        """
        Handle CDP events.
        
        Args:
            event: The CDP event to handle.
        """
        method = event.get("method", "")
        params = event.get("params", {})
        session_id = event.get("sessionId")

        if method == "Target.attachedToTarget":
            target_info = params.get("targetInfo", {})
            target_id = target_info.get("targetId")
            session_id = params.get("sessionId")
            if target_id and session_id:
                logger.debug(f"Target attached: {target_id} with session {session_id}")
                for page in self._pages:
                    if page.target_id == target_id:
                        await page._handle_event(event)

        elif method == "Target.detachedFromTarget":
            target_id = params.get("targetId")
            if target_id:
                logger.debug(f"Target detached: {target_id}")
                for page in self._pages:
                    if page.target_id == target_id:
                        await page._handle_event(event)

        elif session_id:
            # If the event has a session ID, it belongs to a page
            for page in self._pages:
                if page.session_id == session_id:
                    await page._handle_event(event)
                    break

    async def _ensure_connected(self) -> None:
        """
        Ensure we have a valid connection, reconnecting if necessary.
        
        Raises:
            ConnectionError: If unable to establish connection.
        """
        if not self._connected or not self.websocket or self.websocket.closed:
            logger.warning("Connection lost, attempting to reconnect...")
            await self.__aenter__()

    async def _close_pages(self) -> None:
        """Close all tracked pages."""
        if not self._pages:
            return

        logger.debug(f"Closing {len(self._pages)} pages")
        for page in self._pages:
            try:
                await page.close()
            except Exception as e:
                logger.warning(f"Failed to close page: {e}")

    async def _get_ws_url(self) -> str:
        """
        Get the WebSocket URL from Chrome's debugging interface.
        
        Returns:
            The WebSocket URL to connect to.
            
        Raises:
            ConnectionError: If unable to get the WebSocket URL.
        """
        try:
            response = requests.get(f"http://{self.host}:{self.port}/json/version")
            data = response.json()
            ws_url = data["webSocketDebuggerUrl"]
            if "localhost:9222" in ws_url:
                ws_url = ws_url.replace("localhost:9222", f"{self.host}:{self.port}")
            return ws_url
        except Exception as e:
            raise ConnectionError(f"Failed to get WebSocket URL: {str(e)}")

    async def _connect_websocket(self) -> None:
        """
        Establish a WebSocket connection to Chrome.
        
        Raises:
            ConnectionError: If unable to establish connection after max retries.
        """
        if self.websocket:
            return
            
        retries = 0
        last_error = None
        
        while retries < self.max_retries:
            try:
                self.websocket = await websockets.connect(
                    await self._get_ws_url(),
                    ping_interval=None,  # Disable ping to avoid timeouts
                    max_size=None,  # No limit on message size
                    close_timeout=5  # 5 seconds timeout for close
                )
                self._connected = True
                logger.info("Connected to Chrome")
                return
            except Exception as e:
                last_error = e
                retries += 1
                if retries < self.max_retries:
                    logger.warning(f"Connection attempt {retries} failed, retrying...")
                    await asyncio.sleep(1)
        
        raise ConnectionError(f"Failed to connect after {self.max_retries} attempts: {str(last_error)}")

    def _next_command_id(self):
        self.command_id += 1
        return self.command_id 