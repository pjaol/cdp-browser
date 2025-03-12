"""
Simple CDP Browser Page implementation.
"""
from __future__ import annotations
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable, TypeVar, Generic, TYPE_CHECKING, Tuple
from websockets.client import WebSocketClientProtocol
from collections import defaultdict

from .exceptions import NavigationError, TimeoutError, PageError, BrowserError

if TYPE_CHECKING:
    from .browser import Browser

logger = logging.getLogger(__name__)

T = TypeVar('T')

class EventEmitter:
    """A simple event emitter class."""

    def __init__(self):
        """Initialize the event emitter."""
        self._event_futures: Dict[str, List[asyncio.Future]] = {}
        self._listeners: Dict[str, List[Callable]] = {}
        self._one_time_listeners: Dict[str, List[Callable]] = {}

    def on(self, event_name: str, callback: Callable) -> None:
        """Add a persistent event listener."""
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(callback)

    def once(self, event_name: str, callback: Callable) -> None:
        """Add a one-time event listener."""
        if event_name not in self._one_time_listeners:
            self._one_time_listeners[event_name] = []
        self._one_time_listeners[event_name].append(callback)

    async def emit(self, event_name: str, *args, **kwargs) -> None:
        """Emit an event with arguments."""
        # Handle regular listeners
        if event_name in self._listeners:
            for callback in self._listeners[event_name][:]:  # Create a copy to avoid modification during iteration
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(*args, **kwargs)
                    else:
                        callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in event listener for {event_name}: {e}")

        # Handle one-time listeners
        if event_name in self._one_time_listeners:
            listeners = self._one_time_listeners.pop(event_name, [])
            for callback in listeners:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(*args, **kwargs)
                    else:
                        callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in one-time event listener for {event_name}: {e}")

        # Handle futures waiting for this event
        if event_name in self._event_futures:
            futures = self._event_futures.pop(event_name, [])
            for future in futures:
                if not future.done():
                    future.set_result((args, kwargs))

    async def wait_for(self, event_name: str, timeout: Optional[float] = None) -> Tuple[Tuple, Dict]:
        """Wait for an event to occur."""
        if event_name not in self._event_futures:
            self._event_futures[event_name] = []

        future = asyncio.Future()
        self._event_futures[event_name].append(future)

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            if not future.done():
                future.cancel()
            if event_name in self._event_futures:
                try:
                    self._event_futures[event_name].remove(future)
                except ValueError:
                    pass
            raise
        except Exception:
            if not future.done():
                future.cancel()
            if event_name in self._event_futures:
                try:
                    self._event_futures[event_name].remove(future)
                except ValueError:
                    pass
            raise

    def clear(self) -> None:
        """Clear all event listeners and futures."""
        # Clear regular listeners
        self._listeners.clear()
        
        # Clear one-time listeners
        self._one_time_listeners.clear()
        
        # Cancel and clear all futures
        for futures in self._event_futures.values():
            for future in futures:
                if not future.done():
                    future.cancel()
        self._event_futures.clear()

class Page:
    """
    Manages a browser page/tab via CDP.
    
    This class provides methods to control a Chrome page/tab using the Chrome DevTools Protocol.
    It handles navigation, events, and page interactions.
    
    Args:
        browser: The browser instance.
        target_id: The ID of the target (page/tab).
    """
    def __init__(self, browser: "Browser", target_id: str) -> None:
        """Initialize a new page.

        Args:
            browser: The browser instance that created this page.
            target_id: The target ID of the page.
        """
        self.browser = browser
        self.target_id = target_id
        self.session_id = None
        self._closed = False
        self._closing = False
        self._command_id = 0
        self._command_futures = {}
        self._navigation_timeout = 30.0
        self._navigation_lock = asyncio.Lock()
        self._cleanup_lock = asyncio.Lock()
        self._message_handler_task = None
        self._events = EventEmitter()
        self._main_frame_id = None  # Will be set when frame is created
        self._navigation_state = {
            'load_complete': False,
            'navigation_complete': False,
            'frame_stopped_loading': False,
            'load_event_fired': False,
            'dom_content_event_fired': False,
            'network_idle': True
        }
        self._pending_network_requests = set()
        self._navigation_request_id = None
        self._navigation_start_time = None
        self.url = "about:blank"
        self._attached_targets: Dict[str, str] = {}
        self.logger = logging.getLogger(__name__)
        self._execution_context_id = None
        
        # Navigation state tracking
        self._navigation_events = {
            "load": asyncio.Event(),
            "domcontentloaded": asyncio.Event(),
            "networkidle": asyncio.Event()
        }
        
        # Set up default event handlers
        self._setup_default_handlers()

    def _setup_default_handlers(self) -> None:
        """Set up default event handlers for page events."""
        self._events.on("Page.frameStartedLoading", self._handle_frame_started_loading)
        self._events.on("Page.frameStoppedLoading", self._handle_frame_stopped_loading)
        self._events.on("Page.loadEventFired", self._handle_load_event_fired)
        self._events.on("Page.domContentEventFired", self._handle_dom_content_fired)
        self._events.on("Page.frameNavigated", self._handle_frame_navigated)
        self._events.on("Network.requestWillBeSent", self._handle_request_will_be_sent)
        self._events.on("Network.responseReceived", self._handle_response_received)
        self._events.on("Network.loadingFinished", self._handle_loading_finished)
        self._events.on("Network.loadingFailed", self._handle_loading_failed)
        self._events.on("Runtime.executionContextCreated", self._handle_execution_context_created)
        self._events.on("Page.navigationRequested", self._handle_navigation_requested)
        self._events.on("Page.crashedOrError", self._handle_page_crashed)

    async def _handle_frame_started_loading(self, params: Dict) -> None:
        """Handle frame started loading event."""
        frame_id = params.get("frameId")
        # Store the main frame ID when it's first created
        if not self._main_frame_id:
            self._main_frame_id = frame_id
            logger.debug(f"Set main frame ID to: {frame_id}")
            
        if frame_id == self._main_frame_id:
            logger.debug("Main frame started loading")
            self._navigation_state.update({
                "frame_stopped_loading": False,
                "load_complete": False,
                "navigation_complete": False,
                "load_event_fired": False,
                "dom_content_event_fired": False,
                "network_idle": False  # Set to False when navigation starts
            })
            # Clear all navigation events
            for event in self._navigation_events.values():
                event.clear()
            self._pending_network_requests.clear()

    async def _handle_frame_stopped_loading(self, params: Dict) -> None:
        """Handle frame stopped loading event."""
        frame_id = params.get("frameId")
        if frame_id == self._main_frame_id:
            logger.debug("Main frame stopped loading")
            self._navigation_state["frame_stopped_loading"] = True
            
            # If load event has fired, mark load as complete
            if self._navigation_state["load_event_fired"]:
                logger.debug("Load event already fired, marking load as complete")
                self._navigation_state["load_complete"] = True
                self._navigation_events["load"].set()
                
                # Check if network is idle, if so mark navigation as complete
                if self._navigation_state["network_idle"]:
                    logger.debug("Network is idle, marking navigation as complete")
                    self._navigation_state["navigation_complete"] = True
                
                # Check network idle state anyway
                await self._check_network_idle()

    async def _handle_load_event_fired(self, params: Dict) -> None:
        """Handle load event fired."""
        logger.debug("Load event fired")
        self._navigation_state["load_event_fired"] = True
        
        # If frame has already stopped loading, mark load as complete
        if self._navigation_state["frame_stopped_loading"]:
            logger.debug("Frame already stopped loading, marking load as complete")
            self._navigation_state["load_complete"] = True
            self._navigation_events["load"].set()
            
            # Check if network is idle, if so mark navigation as complete
            if self._navigation_state["network_idle"]:
                logger.debug("Network is idle, marking navigation as complete")
                self._navigation_state["navigation_complete"] = True
            
            # Check network idle state anyway
            await self._check_network_idle()

    async def _handle_dom_content_fired(self, params: Dict) -> None:
        """Handle DOMContentLoaded event."""
        self._navigation_state["dom_content_event_fired"] = True
        self._navigation_events["domcontentloaded"].set()
        logger.debug("DOMContentLoaded event fired")

    async def _handle_frame_navigated(self, params: Dict) -> None:
        """Handle frame navigated event."""
        frame = params.get("frame", {})
        if frame.get("id") == self.target_id:
            self.url = frame.get("url", self.url)

    async def _handle_execution_context_created(self, params: Dict) -> None:
        """Handle execution context created event."""
        context = params.get("context", {})
        if context.get("auxData", {}).get("isDefault"):
            self._execution_context_id = context.get("id")
            self.logger.debug(f"Updated execution context ID to: {self._execution_context_id}")

    async def _handle_navigation_requested(self, params: Dict) -> None:
        """Handle navigation requested event."""
        self._navigation_start_time = asyncio.get_event_loop().time()
        self._navigation_state.update({
            "frame_stopped_loading": False,
            "load_event_fired": False,
            "dom_content_event_fired": False,
            "network_idle": False,  # Set to False when navigation starts since we expect network activity
            "load_complete": False,
            "navigation_complete": False
        })
        self._pending_network_requests.clear()
        self._navigation_request_id = None
        logger.debug("Navigation requested, reset navigation state")

    async def _handle_request_will_be_sent(self, params: Dict) -> None:
        """Handle new network request."""
        request_id = params.get("requestId")
        if request_id:
            self._pending_network_requests.add(request_id)
            self._navigation_state["network_idle"] = False
            self._navigation_events["networkidle"].clear()
            self._navigation_state["navigation_complete"] = False
        if params.get("type") == "Document":
            self._navigation_request_id = request_id
        logger.debug(f"Network request started: {request_id}")

    async def _handle_response_received(self, params: Dict) -> None:
        """Handle network request completion."""
        request_id = params.get("requestId")
        if request_id in self._pending_network_requests:
            self._pending_network_requests.remove(request_id)
            if not self._pending_network_requests:
                self._navigation_state["network_idle"] = True
                self._navigation_events["networkidle"].set()
                if self._navigation_state["frame_stopped_loading"]:
                    self._navigation_state["navigation_complete"] = True
        logger.debug(f"Network request finished: {request_id}")

    async def _handle_loading_finished(self, params: Dict) -> None:
        """Handle network request completion."""
        request_id = params.get("requestId")
        if request_id in self._pending_network_requests:
            self._pending_network_requests.remove(request_id)
            if not self._pending_network_requests:
                self._navigation_state["network_idle"] = True
                self._navigation_events["networkidle"].set()
                if self._navigation_state["frame_stopped_loading"]:
                    logger.debug("Frame stopped loading and network is idle, marking navigation as complete")
                    self._navigation_state["navigation_complete"] = True
        logger.debug(f"Network request finished: {request_id}")

    async def _handle_loading_failed(self, params: Dict) -> None:
        """Handle network request failure."""
        request_id = params.get("requestId")
        if request_id in self._pending_network_requests:
            self._pending_network_requests.remove(request_id)
            if not self._pending_network_requests:
                self._navigation_state["network_idle"] = True
                self._navigation_events["networkidle"].set()
                if self._navigation_state["frame_stopped_loading"]:
                    logger.debug("Frame stopped loading and network is idle, marking navigation as complete")
                    self._navigation_state["navigation_complete"] = True
        if request_id == self._navigation_request_id:
            # Main document request failed
            self._navigation_events["load"].set()
            self._navigation_events["domcontentloaded"].set()
            self._navigation_state["load_complete"] = True
            self._navigation_state["navigation_complete"] = True
        logger.debug(f"Network request failed: {request_id}")

    async def _handle_page_crashed(self, params: Dict) -> None:
        """Handle page crashed event."""
        self._navigation_state.update({
            "frame_stopped_loading": True,
            "load_event_fired": True,
            "dom_content_event_fired": True,
            "network_idle": True,
            "load_complete": True,
            "navigation_complete": True
        })
        self._navigation_events["load"].set()
        self._navigation_events["domcontentloaded"].set()
        self._navigation_events["networkidle"].set()

    async def close(self) -> None:
        """Close the page and clean up resources."""
        if self._closed:
            return

        async with self._cleanup_lock:
            if self._closing:
                return
            self._closing = True

            try:
                if self._message_handler_task is not None:
                    self._message_handler_task.cancel()
                    try:
                        await self._message_handler_task
                    except asyncio.CancelledError:
                        pass
                    self._message_handler_task = None

                # Clear event listeners and command waiters
                self._events.clear()
                for future in self._command_futures.values():
                    if not future.done():
                        future.cancel()
                self._command_futures.clear()

                # Detach from target first (if session still exists)
                if self.session_id:
                    try:
                        await self.browser.send_command("Target.detachFromTarget", {"sessionId": self.session_id})
                    except Exception as e:
                        # If the session is not found, that's expected in some cases, so only log as debug
                        if "Session with given id not found" in str(e):
                            logger.debug(f"Session {self.session_id} already detached")
                        else:
                            logger.error(f"Error detaching from target: {e}")
                else:
                    logger.debug("No session ID available for detaching from target")

                # Close target after detaching (or trying to)
                try:
                    await self.browser.send_command("Target.closeTarget", {"targetId": self.target_id})
                except Exception as e:
                    logger.error(f"Error closing target: {e}")

                self._closed = True
                logger.debug(f"Page {self.target_id} closed")
            except Exception as e:
                logger.error(f"Error during page cleanup: {e}")
                raise PageError(f"Failed to close page: {e}")
            finally:
                self._closing = False

    async def _close_target(self, target_id: str) -> None:
        """Close a specific target with timeout."""
        try:
            await asyncio.wait_for(
                self.browser.send_command("Target.closeTarget", {"targetId": target_id}),
                timeout=5.0
            )
        except Exception as e:
            logger.warning(f"Error closing target {target_id}: {e}")

    async def __aenter__(self) -> 'Page':
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def initialize(self) -> None:
        """Initialize the page by attaching to the target and enabling required domains."""
        try:
            # First attach to the target with flatten mode
            result = await asyncio.wait_for(
                self.browser.send_command("Target.attachToTarget", {
                    "targetId": self.target_id,
                    "flatten": True
                }),
                timeout=5.0
            )
            self.session_id = result.get("sessionId")
            if not self.session_id:
                raise PageError("Failed to get session ID from target attachment")
            
            logger.debug(f"Attached to target {self.target_id} with session {self.session_id}")

            # Enable target discovery
            await asyncio.wait_for(
                self.browser.send_command("Target.setDiscoverTargets", {"discover": True}),
                timeout=5.0
            )
            logger.debug("Target discovery enabled")

            # Bind session to target
            await asyncio.wait_for(
                self.browser.send_command("Target.activateTarget", {
                    "targetId": self.target_id
                }),
                timeout=5.0
            )
            logger.debug(f"Session bound to target {self.target_id}")

            # Now enable required domains
            domains = ["Runtime", "Network", "Page"]
            for domain in domains:
                try:
                    await asyncio.wait_for(
                        self.enable_domain(domain),
                        timeout=5.0
                    )
                except Exception as e:
                    logger.warning(f"Failed to enable {domain} domain: {str(e)}")

            logger.debug("Page initialization complete")

        except asyncio.TimeoutError as e:
            logger.error(f"Timeout during page initialization: {str(e)}")
            await self.close()
            raise PageError(f"Timeout during page initialization: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to initialize page: {str(e)}")
            await self.close()
            raise PageError(f"Failed to initialize page: {str(e)}")

    async def _handle_messages(self) -> None:
        """Background task to handle incoming messages for this page."""
        try:
            logger.debug(f"Starting message handler for page {self.target_id}")
            await self._events.emit("ready")  # Signal that we're ready to handle messages
            
            while True:
                try:
                    message = await self._events.wait_for("message")
                    logger.debug(f"Page {self.target_id} received message: {message}")
                    
                    # Handle events
                    if "method" in message:
                        method = message["method"]
                        params = message.get("params", {})
                        
                        # Call event handlers
                        await self._events.emit(method, params)
                        
                        # Notify waiters
                        waiters = self._events.waiters.get(method, [])
                        if waiters:
                            logger.debug(f"Found {len(waiters)} waiters for event {method}")
                            # Set result for all waiters
                            for waiter in waiters:
                                if not waiter.done():
                                    waiter.set_result(params)
                            # Clear waiters
                            self._events.waiters[method].clear()
                            
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Error handling message in page {self.target_id}: {e}")
                    
        except asyncio.CancelledError:
            logger.debug(f"Message handler for page {self.target_id} cancelled")
        except Exception as e:
            logger.error(f"Message handler for page {self.target_id} failed: {e}")
        finally:
            await self._events.emit("ready", False)

    async def send_command(self, method: str, params: Optional[Dict] = None) -> Dict:
        """
        Send a command to the page.

        Args:
            method: The method to call.
            params: Optional parameters for the method.

        Returns:
            The result of the command.

        Raises:
            PageError: If the command fails.
        """
        if params is None:
            params = {}

        # Include the session ID in the parameters for flat protocol
        if self.session_id:
            params["sessionId"] = self.session_id

        try:
            return await self.browser.send_command(method, params)
        except Exception as e:
            raise PageError(f"Failed to send command {method}: {str(e)}")

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
            result = await self.send_command(f"{domain}.enable", {
                "targetId": self.target_id
            })
            logger.debug(f"Successfully enabled {domain} domain with result: {result}")
        except Exception as e:
            logger.error(f"Failed to enable {domain} domain: {str(e)}")
            raise PageError(f"Failed to enable {domain} domain: {str(e)}")

    async def navigate(self, url: str, wait_until: str = "load", timeout: Optional[float] = None) -> None:
        """
        Navigate to a URL and wait for the specified condition.
        
        Args:
            url: The URL to navigate to.
            wait_until: What to wait for - 'load', 'networkidle', 'domcontentloaded', or 'any'.
            timeout: Maximum time to wait in seconds.
            
        Raises:
            NavigationError: If navigation fails or times out.
        """
        if self._closed:
            raise PageError("Page is closed")
            
        timeout = timeout or self._navigation_timeout
        
        async with self._navigation_lock:
            try:
                # Reset navigation state
                for event in self._navigation_events.values():
                    event.clear()
                self._navigation_state.update({
                    "frame_stopped_loading": False,
                    "load_complete": False,
                    "navigation_complete": False,
                    "load_event_fired": False,
                    "dom_content_event_fired": False,
                    "network_idle": False
                })
                self._pending_network_requests.clear()
                self._navigation_request_id = None
                self._navigation_start_time = asyncio.get_event_loop().time()
                
                # Enable required domains
                await self.enable_domain("Page")
                await self.enable_domain("Network")
                
                # Start navigation
                logger.debug(f"Starting navigation to {url}")
                result = await self.send_command("Page.navigate", {"url": url})
                if "errorText" in result:
                    raise NavigationError(f"Navigation failed: {result['errorText']}")
                
                # Wait for the specified condition using our improved wait_for_navigation method
                try:
                    logger.debug(f"Waiting for navigation with strategy: {wait_until}")
                    await self.wait_for_navigation(timeout=timeout, wait_until=wait_until)
                    logger.debug("Navigation completed successfully")
                    
                except TimeoutError as e:
                    raise NavigationError(f"Navigation timeout: {str(e)}")
                    
                # Update current URL
                self.url = await self.get_current_url()
                
            except Exception as e:
                logger.error(f"Navigation failed: {e}")
                raise NavigationError(f"Navigation failed: {str(e)}")

    async def get_current_url(self) -> str:
        """Get the current URL of the page."""
        try:
            result = await self.send_command("Page.getNavigationHistory")
            entries = result.get("entries", [])
            current_index = result.get("currentIndex", -1)
            
            if 0 <= current_index < len(entries):
                return entries[current_index].get("url", self.url)
            return self.url
            
        except Exception as e:
            logger.error(f"Failed to get current URL: {e}")
            return self.url

    async def get_content(self) -> str:
        """
        Get the page's HTML content.
        
        Returns:
            The HTML content of the page.
        """
        result = await self.evaluate("() => document.documentElement.outerHTML")
        return result if isinstance(result, str) else str(result)

    async def get_title(self) -> str:
        """
        Get the page's title.
        
        Returns:
            The title of the page.
        """
        result = await self.evaluate("() => document.title")
        return result if isinstance(result, str) else str(result)

    async def wait_for_event(self, event: str, timeout: Optional[float] = None) -> Any:
        """Wait for a specific event with timeout."""
        try:
            return await self._events.wait_for(event, timeout or self._navigation_timeout)
        except TimeoutError:
            raise PageError(f"Timeout waiting for event: {event}")

    async def wait_for_navigation(self, timeout: Optional[float] = None, wait_until: str = "load") -> None:
        """Wait for navigation to complete with proper timeout.
        
        Args:
            timeout: Maximum time to wait in seconds.
            wait_until: What to wait for - 'load', 'networkidle', 'domcontentloaded', or 'any'.
        
        Raises:
            TimeoutError: If navigation doesn't complete within the timeout.
        """
        timeout = timeout or self._navigation_timeout
        valid_wait_options = ["load", "networkidle", "domcontentloaded", "any"]
        
        if wait_until not in valid_wait_options:
            raise ValueError(f"Invalid wait_until value: {wait_until}. Must be one of {valid_wait_options}")
        
        try:
            if wait_until == "any":
                # Wait for either load, domcontentloaded, or networkidle, whichever comes first
                done, pending = await asyncio.wait(
                    [
                        self._navigation_events["load"].wait(),
                        self._navigation_events["domcontentloaded"].wait(),
                        self._navigation_events["networkidle"].wait()
                    ],
                    timeout=timeout,
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancel any pending tasks
                for task in pending:
                    task.cancel()
                    
            elif wait_until in ["load", "networkidle", "domcontentloaded"]:
                # Wait for the specific event
                await asyncio.wait_for(
                    self._navigation_events[wait_until].wait(),
                    timeout=timeout
                )
            
            # Validate that navigation is actually complete
            if not self._navigation_state["navigation_complete"] and not self._navigation_state["network_idle"]:
                # If we've reached here but navigation isn't complete, give a short grace period
                for _ in range(5):  # Try a few times with a short delay
                    if self._navigation_state["navigation_complete"] or self._navigation_state["network_idle"]:
                        break
                    await asyncio.sleep(0.1)
            
            logger.debug(f"Navigation completed with state: {self._navigation_state}")
                
        except asyncio.TimeoutError:
            pending = len(self._pending_network_requests)
            state = {k: v for k, v in self._navigation_state.items()}
            raise TimeoutError(
                f"Navigation timeout after {timeout} seconds. "
                f"State: {state}, Pending requests: {pending}"
            )

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

    async def evaluate(self, expression: str, await_promise: bool = True) -> Any:
        """
        Evaluate JavaScript code in the context of the page.
        
        Args:
            expression: JavaScript expression or function to evaluate
            await_promise: Whether to wait for any promise to resolve
            
        Returns:
            The result of the expression
        """
        try:
            # First try simple evaluation with Runtime.evaluate
            raw_result = await self.send_command(
                "Runtime.evaluate",
                {
                    "expression": expression,
                    "returnByValue": True,
                    "awaitPromise": await_promise
                }
            )
            self.logger.debug(f"Raw evaluate result: {raw_result.get('result', {})}")

            # If we got a function, execute it in the current context
            if raw_result.get("result", {}).get("type") == "function":
                if not self._execution_context_id:
                    # If we don't have an execution context ID, try reloading the page
                    self.logger.warning("No execution context found, attempting to reload page")
                    await self.send_command("Page.reload")
                    await asyncio.sleep(3)  # Wait for page to reload
                    
                    # Try evaluating again after reload
                    return await self.evaluate(expression, await_promise)

                raw_result = await self.send_command(
                    "Runtime.callFunctionOn",
                    {
                        "functionDeclaration": expression,
                        "executionContextId": self._execution_context_id,
                        "returnByValue": True,
                        "awaitPromise": await_promise
                    }
                )

            result = raw_result.get("result", {})

            # Handle primitive values
            if result.get("type") in ["string", "number", "boolean", "undefined"]:
                self.logger.debug(f"Found primitive value: {result.get('value')}")
                return result.get("value")

            # Handle object references
            if "objectId" in result:
                props = await self.send_command(
                    "Runtime.getProperties",
                    {"objectId": result["objectId"], "ownProperties": True}
                )
                
                obj = {}
                for prop in props.get("result", []):
                    if prop.get("enumerable") and "value" in prop:
                        obj[prop["name"]] = prop["value"].get("value")
                return obj

            return result.get("value")

        except Exception as e:
            self.logger.error(f"Error evaluating JavaScript: {e}")
            # If we got an execution context error, try refreshing the page and evaluating again
            if "execution context" in str(e).lower() and "Cannot find context" in str(e):
                self.logger.warning("Execution context error, trying to reload page and retry evaluation")
                try:
                    await self.send_command("Page.reload")
                    await asyncio.sleep(3)  # Wait for page to reload
                    return await self.evaluate(expression, await_promise)
                except Exception as retry_error:
                    self.logger.error(f"Retry evaluation failed: {retry_error}")
            raise

    async def type(self, selector: str, text: str) -> None:
        """
        Type text into an element.
        
        Args:
            selector: CSS selector for the input element.
            text: The text to type.
        """
        await self.wait_for_selector(selector)
        # Focus the element and clear its value
        await self.evaluate(f'''
            (function() {{
                const el = document.querySelector("{selector}");
                el.focus();
                el.value = "";
                return true;
            }})()
        ''')
        # Type the text in one go for efficiency
        await self.send_command("Input.insertText", {"text": text})

    async def click(self, selector: str, wait_for_navigation: bool = True, wait_until: str = "any") -> None:
        """
        Click an element.
        
        Args:
            selector: CSS selector for the element to click.
            wait_for_navigation: Whether to wait for navigation after the click.
            wait_until: Navigation wait strategy - 'load', 'networkidle', 'domcontentloaded', or 'any'.
        """
        await self.wait_for_selector(selector)
        
        # Get element position for proper mouse click
        box = await self.evaluate(f'''
            (function() {{
                const el = document.querySelector("{selector}");
                const rect = el.getBoundingClientRect();
                return {{
                    x: rect.left + rect.width / 2,
                    y: rect.top + rect.height / 2
                }};
            }})()
        ''')
        
        # Simulate mouse click with proper events
        events = [
            {"type": "mousePressed", "button": "left", "clickCount": 1},
            {"type": "mouseReleased", "button": "left", "clickCount": 1}
        ]
        
        for event in events:
            await self.send_command("Input.dispatchMouseEvent", {
                "type": event["type"],
                "x": box["x"],
                "y": box["y"],
                "button": event["button"],
                "clickCount": event["clickCount"]
            })
        
        if wait_for_navigation:
            try:
                logger.debug(f"Waiting for navigation after click with strategy: {wait_until}")
                await self.wait_for_navigation(timeout=self._navigation_timeout, wait_until=wait_until)
            except TimeoutError as e:
                logger.error(f"Navigation timeout after click on {selector}: {e}")
                raise

    async def _handle_event(self, event: Dict) -> None:
        """Handle a CDP event."""
        try:
            method = event.get("method")
            params = event.get("params", {})
            
            if not method:
                return
                
            # Handle target-related events
            if method == "Target.attachedToTarget":
                session_id = params.get("sessionId")
                target_info = params.get("targetInfo", {})
                target_id = target_info.get("targetId")
                if target_id == self.target_id:
                    self.session_id = session_id
                    logger.debug(f"Attached to target {target_id} with session {session_id}")
                elif target_id and session_id:
                    self._attached_targets[target_id] = session_id
                    
            elif method == "Target.detachedFromTarget":
                session_id = params.get("sessionId")
                target_id = params.get("targetId")
                if session_id == self.session_id:
                    self.session_id = None
                    logger.debug(f"Detached from target {target_id}")
                elif target_id in self._attached_targets:
                    del self._attached_targets[target_id]
                    
            elif method == "Target.targetDestroyed":
                target_id = params.get("targetId")
                if target_id == self.target_id:
                    self.target_id = None
                    logger.debug(f"Target {target_id} destroyed")
                elif target_id in self._attached_targets:
                    del self._attached_targets[target_id]
            
            # Emit event for all listeners
            await self._events.emit(method, params)
            
        except Exception as e:
            logger.error(f"Error handling event: {e}")
            # Don't raise the error to avoid breaking the event loop 

    @property
    def _load_complete(self):
        """Check if page load is complete."""
        return self._navigation_state['load_complete']

    @property
    def _navigation_complete(self):
        """Check if navigation is complete."""
        return self._navigation_state['navigation_complete']

    async def _handle_page_event(self, method, params):
        """Handle Page domain events."""
        if method == 'Page.loadEventFired':
            self._navigation_state['load_event_fired'] = True
            self._navigation_state['load_complete'] = True
            self._navigation_state['navigation_complete'] = True
            await self._events.emit('load')
        elif method == 'Page.domContentEventFired':
            self._navigation_state['dom_content_event_fired'] = True
            await self._events.emit('domcontentloaded')
        elif method == 'Page.frameStoppedLoading':
            self._navigation_state['frame_stopped_loading'] = True
            await self._events.emit('framestoppedloading')
        elif method == 'Page.frameNavigated':
            # Reset navigation state on new navigation
            self._navigation_state['load_complete'] = False
            self._navigation_state['navigation_complete'] = False
            self._navigation_state['frame_stopped_loading'] = False
            self._navigation_state['load_event_fired'] = False
            self._navigation_state['dom_content_event_fired'] = False
            self._navigation_state['network_idle'] = False
            await self._events.emit('framenavigated', params)

    async def _handle_network_event(self, method, params):
        """Handle Network domain events."""
        if method == 'Network.requestWillBeSent':
            request_id = params['requestId']
            self._pending_network_requests.add(request_id)
            if params.get('type') == 'Document' and not params.get('redirectResponse'):
                self._navigation_request_id = request_id
                self._navigation_start_time = params['timestamp']
        elif method == 'Network.loadingFinished':
            request_id = params['requestId']
            self._pending_network_requests.discard(request_id)
            if len(self._pending_network_requests) == 0:
                self._navigation_state['network_idle'] = True
                await self._events.emit('networkidle')
        elif method == 'Network.loadingFailed':
            request_id = params['requestId']
            self._pending_network_requests.discard(request_id)
            if len(self._pending_network_requests) == 0:
                self._navigation_state['network_idle'] = True
                await self._events.emit('networkidle') 

    async def _check_network_idle(self) -> None:
        """Check if there are any pending network requests and update navigation state."""
        if not self._pending_network_requests:
            # Wait a short time to ensure no new requests start
            await asyncio.sleep(0.1)
            if not self._pending_network_requests:
                logger.debug("Network is idle (no pending requests)")
                self._navigation_state["network_idle"] = True
                self._navigation_events["networkidle"].set()
                
                # If frame has stopped loading, mark navigation as complete
                if self._navigation_state["frame_stopped_loading"]:
                    logger.debug("Frame stopped loading and network is idle, marking navigation as complete")
                    self._navigation_state["navigation_complete"] = True
                    
                    # Even if load event hasn't fired, we can consider a SPA navigation complete
                    # when frame has stopped loading and network is idle
                    if not self._navigation_state["load_complete"] and not self._navigation_state["load_event_fired"]:
                        logger.debug("SPA navigation: setting load_complete even though load event didn't fire")
                        self._navigation_state["load_complete"] = True
                        self._navigation_events["load"].set()
        else:
            logger.debug(f"Network not idle, {len(self._pending_network_requests)} pending requests")