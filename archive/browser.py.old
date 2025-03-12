"""
Simple CDP Browser implementation.
"""
import asyncio
import json
import logging
import websockets
import requests
from typing import Optional, Dict, Any, AsyncGenerator, List, Set

from .page import Page

logger = logging.getLogger(__name__)

class BrowserError(Exception):
    """Base exception for browser-related errors."""
    pass

class ConnectionError(BrowserError):
    """Raised when connection to Chrome fails."""
    pass

class CommandError(BrowserError):
    """Raised when a CDP command fails."""
    pass

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
        self._ws = None
        self.command_id = 0
        self.max_retries = max_retries
        self._connected = False
        self._pages = {}  # Dictionary to track pages by target ID

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

    async def _connect_websocket(self, url: str) -> None:
        """
        Establish a WebSocket connection to Chrome.
        
        Args:
            url: The WebSocket URL to connect to.
            
        Raises:
            ConnectionError: If unable to establish connection after max retries.
        """
        retries = 0
        last_error = None
        
        while retries < self.max_retries:
            try:
                self._ws = await websockets.connect(
                    url,
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

    async def __aenter__(self) -> 'Browser':
        """
        Async context manager entry.
        
        Returns:
            The Browser instance.
            
        Raises:
            ConnectionError: If unable to establish connection.
        """
        try:
            url = await self._get_ws_url()
            await self._connect_websocket(url)
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
        """Close the browser connection and cleanup all targets."""
        try:
            # First close all pages we know about
            await self._close_pages()

            # Then get a list of any remaining targets and close them
            response = await self.send_command("Target.getTargets")
            if response and "targetInfos" in response:
                for target in response["targetInfos"]:
                    try:
                        await self.send_command("Target.closeTarget", {"targetId": target["targetId"]})
                    except Exception as e:
                        logger.warning(f"Failed to close target {target['targetId']}: {e}")

            # Finally close the websocket connection
            if self._ws:
                await self._ws.close()
                self._ws = None
                logger.info("Disconnected from Chrome")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
            raise BrowserError(f"Failed to close browser: {e}")

    async def _close_pages(self) -> None:
        """Close all tracked pages."""
        if not self._pages:
            return

        logger.debug(f"Closing {len(self._pages)} pages")
        for page in list(self._pages.values()):
            try:
                await page.close()
            except Exception as e:
                logger.warning(f"Error closing page: {e}")

    async def _ensure_connected(self) -> None:
        """
        Ensure we have a valid connection, reconnecting if necessary.
        
        Raises:
            ConnectionError: If unable to establish connection.
        """
        if not self._connected or not self._ws or self._ws.closed:
            logger.warning("Connection lost, attempting to reconnect...")
            await self.__aenter__()

    async def _receive_message(self) -> Dict[str, Any]:
        """
        Receive and parse a message from the WebSocket.
        
        Returns:
            The parsed message as a dictionary.
            
        Raises:
            BrowserError: If unable to receive or parse message.
        """
        try:
            message = await self._ws.recv()
            data = json.loads(message)
            logger.debug(f"Received message: {data}")
            return data
        except Exception as e:
            raise BrowserError(f"Error receiving message: {str(e)}")

    async def send_command(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        expect_event: bool = False
    ) -> Dict[str, Any]:
        """Send a command to Chrome and wait for the response."""
        await self._ensure_connected()

        if not params:
            params = {}

        command_id = self.command_id
        self.command_id += 1

        message = {
            "id": command_id,
            "method": method,
            "params": params
        }

        if session_id:
            message["sessionId"] = session_id

        logger.debug(f"Sending command: {method} with params: {params}")

        try:
            await self._ws.send(json.dumps(message))
            
            if expect_event:
                # For commands that trigger events, we need to wait for both the event and the response
                event_data = None
                response_data = None

                while not (event_data and response_data):
                    raw_message = await self._ws.recv()
                    data = json.loads(raw_message)
                    logger.debug(f"Received message: {data}")

                    if "method" in data:
                        # This is an event
                        await self._handle_event(data)
                        event_data = data
                    elif "id" in data and data["id"] == command_id:
                        # This is our command response
                        response_data = data

                if "error" in response_data:
                    raise CommandError(f"Command failed: {response_data['error']}")
                return {"event": event_data, "response": response_data}
            else:
                # For regular commands, we need to handle any events that come before our response
                while True:
                    raw_message = await self._ws.recv()
                    data = json.loads(raw_message)
                    logger.debug(f"Received message: {data}")

                    if "method" in data:
                        # This is an event, process it
                        await self._handle_event(data)
                    elif "id" in data and data["id"] == command_id:
                        # This is our command response
                        if "error" in data:
                            raise CommandError(f"Command failed: {data['error']}")
                        return data.get("result", {})

        except websockets.ConnectionClosed:
            logger.error(f"Connection lost while executing {method}")
            raise BrowserError(f"Connection lost while executing {method}")

    async def _handle_event(self, event_data: Dict[str, Any]) -> None:
        """Handle Chrome DevTools Protocol events."""
        method = event_data.get("method")
        params = event_data.get("params", {})

        if method == "Target.attachedToTarget":
            session_id = params.get("sessionId")
            target_info = params.get("targetInfo", {})
            target_id = target_info.get("targetId")
            target_type = target_info.get("type")

            if target_type == "page":
                # Create and track the page
                page = Page(self._ws, target_id, session_id)
                self._pages[target_id] = page
            elif target_type == "service_worker":
                # Track service worker targets
                if target_id in self._pages:
                    self._pages[target_id]._attached_targets[target_id] = session_id

        elif method == "Target.detachedFromTarget":
            session_id = params.get("sessionId")
            target_id = params.get("targetId")

            # Remove from attached targets if it exists
            for page in self._pages.values():
                if target_id in page._attached_targets:
                    del page._attached_targets[target_id]

    async def create_page(self) -> Page:
        """Create a new page and return it."""
        await self._ensure_connected()

        logger.debug("Creating new target...")
        response = await self.send_command("Target.createTarget", {"url": "about:blank"})
        target_id = response["targetId"]
        logger.debug(f"Created target with ID: {target_id}")

        logger.debug(f"Attaching to target {target_id}...")
        response = await self.send_command(
            "Target.attachToTarget",
            {"targetId": target_id, "flatten": True},
            expect_event=True
        )
        session_id = response["response"]["result"]["sessionId"]
        logger.debug(f"Attached to target with session ID: {session_id}")

        # Enable Target domain for auto-attaching to child targets
        logger.debug("Enabling Target domain...")
        await self.send_command(
            "Target.setAutoAttach",
            {
                "autoAttach": True,
                "waitForDebuggerOnStart": False,
                "flatten": True
            },
            session_id=session_id
        )

        # Get the page instance that was created by the event handler
        page = self._pages[target_id]

        # Enable Page domain
        logger.debug("Enabling Page domain...")
        await page.enable_domain("Page")

        return page

    async def close_page(self, target_id: str) -> None:
        """
        Close a specific page/tab.
        
        Args:
            target_id: The ID of the target to close.
            
        Raises:
            BrowserError: If unable to close the page.
        """
        # Find the page with the given target_id
        page_to_close = self._pages.get(target_id)
        if page_to_close:
            try:
                await page_to_close.close()
                del self._pages[target_id]
            except Exception as e:
                raise BrowserError(f"Failed to close page {target_id}: {str(e)}")
        else:
            logger.warning(f"No page found with target ID {target_id}") 