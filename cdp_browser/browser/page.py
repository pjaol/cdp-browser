"""
Simple CDP Browser Page implementation.
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable, TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar('T')

class PageError(Exception):
    """Base exception for page-related errors."""
    pass

class NavigationError(PageError):
    """Raised when navigation fails."""
    pass

class EventHandler(Generic[T]):
    """
    Handles CDP events for a specific event type.
    
    Args:
        event_name: The name of the event to handle.
    """
    def __init__(self, event_name: str):
        self.event_name = event_name
        self.handlers: List[Callable[[T], Awaitable[None]]] = []

    def add_handler(self, handler: Callable[[T], Awaitable[None]]) -> None:
        """Add a handler function for this event."""
        self.handlers.append(handler)

    async def handle(self, params: T) -> None:
        """Call all registered handlers with the event parameters."""
        for handler in self.handlers:
            try:
                await handler(params)
            except Exception as e:
                logger.error(f"Error in event handler for {self.event_name}: {str(e)}")

class Page:
    """
    Manages a browser page/tab via CDP.
    
    This class provides methods to control a Chrome page/tab using the Chrome DevTools Protocol.
    It handles navigation, events, and page interactions.
    
    Args:
        websocket: The WebSocket connection to Chrome.
        target_id: The ID of the target (page/tab).
        session_id: The session ID for this target.
    """
    def __init__(self, websocket, target_id: str, session_id: str):
        self.websocket = websocket
        self.target_id = target_id
        self.session_id = session_id
        self.command_id = 0
        self._event_handlers: Dict[str, EventHandler[Dict[str, Any]]] = {}
        self._navigation_complete = False
        self._load_complete = False
        self._crashed = False
        self._closed = False
        self.url = "about:blank"
        self._attached_targets: Dict[str, str] = {}  # targetId -> sessionId

        # Set up default event handlers
        self._setup_default_handlers()

    async def __aenter__(self) -> 'Page':
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """
        Close the page and cleanup resources.
        
        This method will:
        1. Close all attached targets
        2. Detach from all targets
        3. Close the main target
        4. Clean up event handlers
        
        Raises:
            PageError: If unable to close the page properly.
        """
        if self._closed:
            return

        try:
            logger.debug(f"Closing page {self.target_id}")
            
            # First close all attached targets
            for target_id, session_id in list(self._attached_targets.items()):
                try:
                    logger.debug(f"Closing attached target {target_id}")
                    await self.send_command("Target.closeTarget", {"targetId": target_id})
                    await self.send_command("Target.detachFromTarget", {"sessionId": session_id})
                except Exception as e:
                    logger.warning(f"Error closing attached target {target_id}: {str(e)}")

            # Then detach from the main target
            try:
                await self.send_command("Target.detachFromTarget", {
                    "sessionId": self.session_id
                })
                logger.debug(f"Detached from target {self.target_id}")
            except Exception as e:
                logger.warning(f"Error detaching from target: {str(e)}")

            # Finally close the main target
            try:
                await self.send_command("Target.closeTarget", {
                    "targetId": self.target_id
                })
                logger.debug(f"Closed target {self.target_id}")
            except Exception as e:
                logger.warning(f"Error closing target: {str(e)}")

            # Clear event handlers and state
            self._event_handlers.clear()
            self._attached_targets.clear()
            self._closed = True
            
        except Exception as e:
            logger.error(f"Error during page cleanup: {str(e)}")
            raise PageError(f"Failed to close page: {str(e)}")

    def _setup_default_handlers(self) -> None:
        """Set up default event handlers for navigation and page events."""
        self.add_event_handler("Page.loadEventFired", self._handle_load_event)
        self.add_event_handler("Page.navigatedWithinDocument", self._handle_client_navigation)
        self.add_event_handler("Page.frameStoppedLoading", self._handle_frame_stopped)
        self.add_event_handler("Inspector.targetCrashed", self._handle_crash)
        self.add_event_handler("Target.attachedToTarget", self._handle_target_attached)
        self.add_event_handler("Target.detachedFromTarget", self._handle_target_detached)

    def add_event_handler(self, event_name: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """
        Add a handler for a specific CDP event.
        
        Args:
            event_name: The name of the CDP event to handle.
            handler: The async function to call when the event occurs.
        """
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = EventHandler(event_name)
        self._event_handlers[event_name].add_handler(handler)

    async def _handle_load_event(self, params: Dict[str, Any]) -> None:
        """Handle Page.loadEventFired event."""
        logger.debug("Load event fired")
        self._navigation_complete = True
        self._load_complete = True

    async def _handle_client_navigation(self, params: Dict[str, Any]) -> None:
        """Handle Page.navigatedWithinDocument event."""
        logger.debug("Client-side navigation completed")
        self._navigation_complete = True
        self._load_complete = True

    async def _handle_frame_stopped(self, params: Dict[str, Any]) -> None:
        """Handle Page.frameStoppedLoading event."""
        logger.debug("Frame stopped loading")
        self._load_complete = True

    async def _handle_crash(self, params: Dict[str, Any]) -> None:
        """Handle Inspector.targetCrashed event."""
        logger.error("Page crashed!")
        self._crashed = True

    async def _handle_target_attached(self, params: Dict[str, Any]) -> None:
        """Handle Target.attachedToTarget event."""
        session_id = params.get("sessionId")
        target_info = params.get("targetInfo", {})
        target_id = target_info.get("targetId")
        target_type = target_info.get("type")
        
        if session_id and target_id:
            logger.debug(f"Target attached: {target_type} {target_id} with session {session_id}")
            self._attached_targets[target_id] = session_id

    async def _handle_target_detached(self, params: Dict[str, Any]) -> None:
        """Handle Target.detachedFromTarget event."""
        session_id = params.get("sessionId")
        target_id = params.get("targetId")
        
        if target_id in self._attached_targets:
            logger.debug(f"Target detached: {target_id}")
            del self._attached_targets[target_id]

    async def _handle_event(self, event: Dict[str, Any]) -> None:
        """
        Handle CDP events by dispatching them to registered handlers.
        
        Args:
            event: The CDP event to handle.
        """
        method = event.get("method", "")
        logger.debug(f"Handling event: {method}")
        
        if method in self._event_handlers:
            await self._event_handlers[method].handle(event.get("params", {}))

    async def send_command(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a command to the browser and wait for the response.
        
        Args:
            method: The CDP method to call.
            params: Parameters for the method.
            
        Returns:
            The command response as a dictionary.
            
        Raises:
            PageError: If the command fails or connection is lost.
        """
        if params is None:
            params = {}
            
        self.command_id += 1
        message = {
            "id": self.command_id,
            "method": method,
            "params": params,
            "sessionId": self.session_id
        }
        
        logger.debug(f"Sending command: {method} with params: {params}")
        
        try:
            await self.websocket.send(json.dumps(message))
            
            while True:
                response = await self.websocket.recv()
                data = json.loads(response)
                logger.debug(f"Received message: {data}")
                
                if "method" in data:
                    await self._handle_event(data)
                    continue
                
                if "id" in data and data["id"] == self.command_id:
                    if "error" in data:
                        raise PageError(f"Command failed: {data['error']}")
                    return data.get("result", {})
            
        except Exception as e:
            logger.error(f"Error sending command {method}: {str(e)}")
            raise PageError(str(e))

    async def enable_domain(self, domain: str) -> None:
        """
        Enable a CDP domain.
        
        Args:
            domain: The name of the CDP domain to enable.
            
        Raises:
            PageError: If unable to enable the domain.
        """
        try:
            logger.debug(f"Attempting to enable {domain} domain...")
            result = await self.send_command(f"{domain}.enable")
            logger.debug(f"Successfully enabled {domain} domain with result: {result}")
        except Exception as e:
            logger.error(f"Failed to enable {domain} domain: {str(e)}")
            raise PageError(f"Failed to enable {domain} domain: {str(e)}")

    async def _wait_for_event(self, event_name: str, timeout: int) -> None:
        """
        Wait for a specific event to occur.
        
        Args:
            event_name: The name of the event to wait for.
            timeout: Maximum time to wait in seconds.
            
        Raises:
            TimeoutError: If the event doesn't occur within the timeout.
            PageError: If the page crashes while waiting.
        """
        logger.debug(f"Waiting for {event_name} event...")
        start_time = asyncio.get_event_loop().time()
        
        while True:
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(
                    f"Timeout waiting for {event_name} after {timeout} seconds. "
                    f"Navigation complete: {self._navigation_complete}, "
                    f"Load complete: {self._load_complete}"
                )

            if self._crashed:
                raise PageError("Page crashed while waiting for event")

            try:
                response = await self.websocket.recv()
                data = json.loads(response)
                logger.debug(f"Received message while waiting for {event_name}: {data}")
                
                if "method" in data:
                    await self._handle_event(data)
                    if data["method"] == event_name:
                        return
            except Exception as e:
                logger.error(f"Error while waiting for {event_name}: {str(e)}")
                raise PageError(str(e))

    async def navigate(self, url: str, timeout: int = 30) -> None:
        """
        Navigate to a URL and wait for the page to load.
        
        Args:
            url: The URL to navigate to.
            timeout: Maximum time to wait for navigation in seconds.
            
        Raises:
            NavigationError: If navigation fails or times out.
        """
        logger.info(f"Navigating to {url}")

        # Reset navigation state
        self._navigation_complete = False
        self._load_complete = False
        self._crashed = False

        try:
            # Enable necessary domains
            logger.debug("Enabling Page domain")
            await self.enable_domain("Page")

            # Start navigation
            logger.debug(f"Sending Page.navigate command to {url}")
            result = await self.send_command("Page.navigate", {"url": url})
            logger.debug(f"Navigation started with result: {result}")

            # Wait for the page to load
            await self._wait_for_event("Page.loadEventFired", timeout)
            logger.debug("Navigation completed successfully")

        except Exception as e:
            logger.error(f"Navigation failed: {str(e)}")
            raise NavigationError(str(e))

    async def wait_for_navigation(self, timeout: int = 30) -> None:
        """
        Wait for navigation to complete.
        
        Args:
            timeout: Maximum time to wait in seconds.
            
        Raises:
            TimeoutError: If navigation doesn't complete within the timeout.
            PageError: If the page crashes during navigation.
        """
        # If navigation is already complete, return immediately
        if self._navigation_complete and self._load_complete:
            logger.debug("Navigation was already complete")
            return
            
        # Only reset flags if navigation isn't already complete
        self._navigation_complete = False
        self._load_complete = False
        
        logger.debug("Waiting for navigation to complete...")
        start_time = asyncio.get_event_loop().time()
        
        while True:
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(
                    f"Navigation timeout after {timeout} seconds. "
                    f"Navigation complete: {self._navigation_complete}, "
                    f"Load complete: {self._load_complete}"
                )

            if self._crashed:
                raise PageError("Page crashed during navigation")

            try:
                response = await self.websocket.recv()
                data = json.loads(response)
                logger.debug(f"Received message while waiting for navigation: {data}")
                
                if "method" in data:
                    await self._handle_event(data)
                    if self._navigation_complete and self._load_complete:
                        logger.debug("Navigation completed successfully")
                        return
            except Exception as e:
                logger.error(f"Error while waiting for navigation: {str(e)}")
                raise PageError(str(e))

    async def wait_for_selector(self, selector: str, timeout: int = 30) -> None:
        """
        Wait for an element to be present and visible on the page.
        
        Args:
            selector: CSS selector for the element.
            timeout: Maximum time to wait in seconds.
            
        Raises:
            TimeoutError: If the element doesn't appear within the timeout.
        """
        start_time = asyncio.get_event_loop().time()
        while True:
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(f"Timeout waiting for selector: {selector}")
            
            is_visible = await self.evaluate(f"""
                (function() {{
                    const el = document.querySelector("{selector}");
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    return el.offsetParent !== null && style.visibility !== 'hidden';
                }})()
            """)
            
            if is_visible:
                break
            
            await asyncio.sleep(0.1)

    async def evaluate(self, expression: str) -> Any:
        """
        Evaluate a JavaScript expression.
        
        Args:
            expression: The JavaScript code to evaluate.
            
        Returns:
            The result of the evaluation.
        """
        result = await self.send_command("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True
        })
        return result.get("result", {}).get("value")

    async def type(self, selector: str, text: str) -> None:
        """
        Type text into an element.
        
        Args:
            selector: CSS selector for the input element.
            text: The text to type.
        """
        await self.wait_for_selector(selector)
        await self.evaluate(f'document.querySelector("{selector}").focus();')
        for char in text:
            await self.send_command("Input.insertText", {"text": char})
            await asyncio.sleep(0.05)  # Small delay between keystrokes

    async def click(self, selector: str) -> None:
        """
        Click an element.
        
        Args:
            selector: CSS selector for the element to click.
        """
        await self.wait_for_selector(selector)
        await self.evaluate(f'document.querySelector("{selector}").click();')

    async def get_current_url(self) -> str:
        """Get the current URL of the page.

        Returns:
            str: The current URL.

        Raises:
            PageError: If unable to get the current URL.
        """
        try:
            result = await self.send_command("Page.getNavigationHistory")
            current_index = result["currentIndex"]
            entries = result["entries"]
            if entries and 0 <= current_index < len(entries):
                return entries[current_index]["url"]
            return self.url
        except Exception as e:
            logger.error(f"Error getting current URL: {e}")
            raise PageError(f"Failed to get current URL: {e}") 