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
import time

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
        session_id: Optional session ID.
    """
    def __init__(self, browser: "Browser", target_id: str, session_id: str = None) -> None:
        """Initialize a new page.

        Args:
            browser: The browser instance that created this page.
            target_id: The target ID of the page.
            session_id: Optional session ID.
        """
        self.browser = browser
        self.target_id = target_id
        self.session_id = session_id
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

        self._frame_id = target_id  # Initialize frame_id to target_id
        self._inflight_requests = set()
        self._load_promise = None
        self._dom_content_promise = None

        # Start message handling task
        self._message_handler_task = asyncio.create_task(self._handle_messages())

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
        """Initialize the page.

        This method should be called after creating a new page.
        It sets up the necessary event handlers and enables required domains.

        Raises:
            PageError: If initialization fails.
        """
        try:
            logger.debug(f"Initializing page with target ID: {self.target_id}")

            # Attach to target if we have a target ID but no session ID
            if self.target_id and not self.session_id:
                logger.debug("Attaching to target...")
                result = await self.browser.send_command(
                    "Target.attachToTarget",
                    {"targetId": self.target_id, "flatten": True}
                )
                if "sessionId" in result:
                    self.session_id = result["sessionId"]
                    logger.debug(f"Attached to target with session ID: {self.session_id}")
                else:
                    raise PageError("Failed to get session ID when attaching to target")

            # Enable required domains in parallel with a shorter timeout
            logger.debug("Enabling required domains...")
            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        self.enable_domain("Page"),
                        self.enable_domain("Runtime"),
                        self.enable_domain("Network"),
                        self.enable_domain("DOM")
                    ),
                    timeout=3.0
                )
                logger.debug("Required domains enabled")
            except Exception as e:
                raise PageError(f"Failed to enable required domains: {str(e)}")

            # Initialize execution context with a shorter timeout
            logger.debug("Initializing execution context...")
            try:
                await self.wait_for_execution_context(timeout=2.0)
                logger.debug("Execution context initialized")
            except Exception as e:
                raise PageError(f"Failed to initialize execution context: {str(e)}")

            logger.debug("Page initialization completed successfully")

        except Exception as e:
            logger.error(f"Page initialization failed: {str(e)}")
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
            
            # Ensure we have a session ID
            if not self.session_id:
                logger.debug("No session ID found, attempting to attach to target...")
                result = await self.browser.send_command(
                    "Target.attachToTarget",
                    {"targetId": self.target_id, "flatten": True}
                )
                if "sessionId" in result:
                    self.session_id = result["sessionId"]
                    logger.debug(f"Successfully attached to target with session ID: {self.session_id}")
                else:
                    raise PageError("Failed to get session ID when attaching to target")
            
            # Send enable command with session ID
            result = await self.browser.send_command(
                f"{domain}.enable",
                {"sessionId": self.session_id},
                timeout=5.0  # Use a shorter timeout for enable commands
            )
            logger.debug(f"Successfully enabled {domain} domain with result: {result}")
            
        except Exception as e:
            logger.error(f"Failed to enable {domain} domain: {str(e)}")
            raise PageError(f"Failed to enable {domain} domain: {str(e)}")

    async def wait_for_execution_context(self, timeout: float = 30.0) -> None:
        """Wait for the main execution context to be ready.

        Args:
            timeout: Maximum time to wait in seconds.

        Raises:
            PageError: If the execution context is not ready within the timeout.
        """
        try:
            # Create an event to track execution context creation
            context_ready = asyncio.Event()
            self._execution_context_id = None

            # Set up event handler for execution context creation
            async def on_context_created(params):
                context = params.get("context", {})
                logger.debug(f"Received execution context: {context}")
                if context.get("auxData", {}).get("isDefault"):
                    self._execution_context_id = context.get("id")
                    logger.debug(f"Setting execution context ID: {self._execution_context_id}")
                    context_ready.set()

            # Register event handler
            self._events.on("Runtime.executionContextCreated", on_context_created)

            try:
                # Enable runtime if not already enabled
                logger.debug("Enabling Runtime domain...")
                await self.enable_domain("Runtime")

                # Try to evaluate a simple expression to check for existing context
                logger.debug("Checking for existing context...")
                try:
                    result = await self.send_command("Runtime.evaluate", {
                        "expression": "1 + 1",
                        "returnByValue": True
                    })
                    if result.get("result", {}).get("value") == 2:
                        logger.debug("Found existing context")
                        # If we can evaluate, we have a context
                        # Try to get the context ID from the result
                        if "contextId" in result:
                            self._execution_context_id = result["contextId"]
                            logger.debug(f"Got context ID from evaluation: {self._execution_context_id}")
                        context_ready.set()
                except Exception as e:
                    logger.debug(f"No existing context found: {e}")

                # If no existing context, wait for one to be created
                if not context_ready.is_set():
                    logger.debug("Waiting for context creation...")
                    try:
                        await asyncio.wait_for(context_ready.wait(), timeout)
                    except asyncio.TimeoutError:
                        logger.error(f"Timeout waiting for execution context after {timeout} seconds")
                        # Try to force context creation
                        logger.debug("Attempting to force context creation...")
                        try:
                            result = await self.send_command("Runtime.evaluate", {
                                "expression": "void(0)",
                                "awaitPromise": True
                            })
                            # Wait a bit for context to be created
                            await asyncio.sleep(1)
                            if not context_ready.is_set():
                                # Try one more evaluation
                                try:
                                    result = await self.send_command("Runtime.evaluate", {
                                        "expression": "1 + 1",
                                        "returnByValue": True
                                    })
                                    if result.get("result", {}).get("value") == 2:
                                        logger.debug("Found context after force")
                                        # Try to get the context ID from the result
                                        if "contextId" in result:
                                            self._execution_context_id = result["contextId"]
                                            logger.debug(f"Got context ID from forced evaluation: {self._execution_context_id}")
                                        context_ready.set()
                                except Exception as e:
                                    logger.error(f"Failed to verify forced context: {e}")
                                if not context_ready.is_set():
                                    raise PageError(f"Execution context not ready after {timeout} seconds")
                        except Exception as e:
                            logger.error(f"Failed to force context creation: {e}")
                            raise PageError(f"Execution context not ready after {timeout} seconds")

                # If we still don't have a context ID, try to get it from the Runtime domain
                if not self._execution_context_id:
                    logger.debug("No context ID set, trying to get it from Runtime domain...")
                    try:
                        result = await self.send_command("Runtime.evaluate", {
                            "expression": "1",
                            "returnByValue": True,
                            "generatePreview": False
                        })
                        if "contextId" in result:
                            self._execution_context_id = result["contextId"]
                            logger.debug(f"Got context ID from final evaluation: {self._execution_context_id}")
                    except Exception as e:
                        logger.error(f"Failed to get context ID from Runtime domain: {e}")

                # Verify context is usable by evaluating a simple expression
                logger.debug("Verifying execution context...")
                try:
                    result = await self.send_command("Runtime.evaluate", {
                        "expression": "1 + 1",
                        "returnByValue": True
                    })
                    logger.debug(f"Context verification result: {result}")
                    if "result" not in result or result.get("result", {}).get("value") != 2:
                        raise PageError("Execution context verification failed")
                    # One last attempt to get the context ID if we still don't have it
                    if not self._execution_context_id and "contextId" in result:
                        self._execution_context_id = result["contextId"]
                        logger.debug(f"Got context ID from verification: {self._execution_context_id}")
                except Exception as e:
                    logger.error(f"Execution context verification failed: {str(e)}")
                    raise PageError(f"Execution context verification failed: {str(e)}")

                # If we still don't have a context ID, but we can evaluate, use a default
                if not self._execution_context_id:
                    logger.debug("No context ID found but context is working, using default ID")
                    self._execution_context_id = 1

            except asyncio.TimeoutError:
                logger.error(f"Timeout waiting for execution context after {timeout} seconds")
                raise PageError(f"Execution context not ready after {timeout} seconds")
            except Exception as e:
                logger.error(f"Error waiting for execution context: {str(e)}")
                raise
            finally:
                # Clean up event handler
                if "Runtime.executionContextCreated" in self._events._listeners:
                    self._events._listeners["Runtime.executionContextCreated"].remove(on_context_created)

        except Exception as e:
            logger.error(f"Failed to wait for execution context: {str(e)}")
            raise PageError(f"Failed to wait for execution context: {str(e)}")

        logger.debug("Execution context ready")

    async def evaluate(self, expression: str, return_by_value: bool = True) -> Any:
        """Evaluate JavaScript expression in the page context.

        Args:
            expression: JavaScript expression to evaluate.
            return_by_value: Whether to return the result by value.

        Returns:
            The result of the evaluation.

        Raises:
            PageError: If evaluation fails.
        """
        try:
            # First, try to get the current execution context
            if not self._execution_context_id:
                logger.debug("No execution context ID set, attempting to get current context...")
                try:
                    # Try to get the current execution context
                    result = await self.send_command("Runtime.evaluate", {
                        "expression": "1",
                        "returnByValue": True
                    })
                    if "contextId" in result:
                        self._execution_context_id = result["contextId"]
                        logger.debug(f"Got context ID from evaluation: {self._execution_context_id}")
                except Exception as e:
                    logger.debug(f"Failed to get context ID from evaluation: {e}")
                    # If that fails, try to force a new context
                    try:
                        logger.debug("Attempting to force new context creation...")
                        await self.send_command("Page.enable")
                        await self.send_command("Runtime.enable")
                        # Wait a bit for context to be created
                        await asyncio.sleep(0.5)
                        # Try evaluation again
                        result = await self.send_command("Runtime.evaluate", {
                            "expression": "1",
                            "returnByValue": True
                        })
                        if "contextId" in result:
                            self._execution_context_id = result["contextId"]
                            logger.debug(f"Got context ID from forced creation: {self._execution_context_id}")
                    except Exception as e2:
                        logger.error(f"Failed to force context creation: {e2}")

            # Now try to evaluate the expression
            try:
                # Wrap the expression in a try-catch block to capture JavaScript errors
                wrapped_expression = f"""
                    (() => {{
                        try {{
                            const result = {expression};
                            return result;
                        }} catch (e) {{
                            return {{ __error__: e.message }};
                        }}
                    }})()
                """

                result = await self.send_command(
                    "Runtime.evaluate",
                    {
                        "expression": wrapped_expression,
                        "returnByValue": return_by_value,
                        "awaitPromise": True,
                        "userGesture": True,  # Allow certain operations that require user gesture
                        "timeout": 5000,  # 5 second timeout for evaluation
                        "generatePreview": True  # Get a preview of the result for better error messages
                    }
                )
            except Exception as e:
                if "Cannot find context with specified id" in str(e):
                    logger.debug("Context not found, trying without context ID...")
                    # Try without context ID
                    result = await self.send_command(
                        "Runtime.evaluate",
                        {
                            "expression": wrapped_expression,
                            "returnByValue": return_by_value,
                            "awaitPromise": True,
                            "userGesture": True,
                            "timeout": 5000,
                            "generatePreview": True
                        }
                    )
                else:
                    raise

            if "exceptionDetails" in result:
                details = result["exceptionDetails"]
                error_message = details.get('text', 'Unknown error')
                if 'exception' in details:
                    error_message += f": {details['exception'].get('description', '')}"
                raise PageError(f"JavaScript evaluation failed: {error_message}")

            if "result" not in result:
                logger.error(f"No result in evaluation response: {result}")
                return None

            # Handle different result types
            result_obj = result["result"]
            result_type = result_obj.get("type")
            result_value = result_obj.get("value")

            if result_type == "undefined":
                return None
            elif result_type == "object" and result_obj.get("subtype") == "null":
                return None
            elif result_type == "object":
                if return_by_value:
                    if isinstance(result_value, dict) and "__error__" in result_value:
                        raise PageError(f"JavaScript error: {result_value['__error__']}")
                    return result_value if result_value is not None else {}
                else:
                    # For objects when not returning by value, return the remote object
                    return result_obj
            else:
                return result_value

        except Exception as e:
            logger.error(f"Error evaluating JavaScript: {str(e)}")
            raise PageError(f"Failed to evaluate JavaScript: {str(e)}")

        finally:
            logger.debug("JavaScript evaluation completed")

    async def detach(self) -> None:
        """Detach from the target.

        Raises:
            PageError: If detaching fails.
        """
        try:
            if self.session_id:
                logger.debug(f"Detaching from target with session ID: {self.session_id}")
                await self.send_command("Target.detachFromTarget", {
                    "sessionId": self.session_id
                })
            else:
                logger.debug("No session ID available for detaching")
        except Exception as e:
            logger.error(f"Error detaching from target: {str(e)}")
            raise PageError(f"Failed to detach from target: {str(e)}")

    async def navigate(self, url: str, wait_until: str = "load", timeout: float = 30.0) -> None:
        """Navigate to a URL and wait for the page to load.

        Args:
            url: The URL to navigate to.
            wait_until: When to consider navigation succeeded. One of: "load", "domcontentloaded", "networkidle".
            timeout: Maximum time to wait in seconds.

        Raises:
            PageError: If navigation fails or times out.
        """
        try:
            # Create events for tracking navigation state
            load_event = asyncio.Event()
            dom_content_event = asyncio.Event()
            network_idle_event = asyncio.Event()
            navigation_complete = False

            # Set up event handlers
            async def on_frame_navigated(params):
                frame = params.get("frame", {})
                if frame.get("id") == self._frame_id:
                    logger.debug("Frame navigated")
                    nonlocal navigation_complete
                    navigation_complete = True

            async def on_load_event_fired(_):
                logger.debug("Load event fired")
                load_event.set()

            async def on_dom_content_event_fired(_):
                logger.debug("DOMContentLoaded event fired")
                dom_content_event.set()

            async def on_network_almost_idle(_):
                if navigation_complete:
                    logger.debug("Network almost idle")
                    network_idle_event.set()

            # Register event handlers
            self._events.on("Page.frameNavigated", on_frame_navigated)
            self._events.on("Page.loadEventFired", on_load_event_fired)
            self._events.on("Page.domContentEventFired", on_dom_content_event_fired)
            self._events.on("Network.loadingFinished", on_network_almost_idle)

            try:
                # Enable required domains in parallel with a shorter timeout
                await asyncio.wait_for(
                    asyncio.gather(
                        self.enable_domain("Page"),
                        self.enable_domain("Network"),
                        self.enable_domain("Runtime")
                    ),
                    timeout=2.0
                )

                # Start navigation
                logger.debug(f"Navigating to {url}")
                await self.send_command("Page.navigate", {"url": url})

                # Create tasks for different navigation events with shorter timeouts
                tasks = []
                event_timeout = min(timeout * 0.3, 3.0)  # Use shorter timeout for individual events

                if wait_until in ["load", "networkidle"]:
                    tasks.append(asyncio.create_task(asyncio.wait_for(load_event.wait(), event_timeout)))
                if wait_until in ["domcontentloaded", "networkidle"]:
                    tasks.append(asyncio.create_task(asyncio.wait_for(dom_content_event.wait(), event_timeout)))
                if wait_until == "networkidle":
                    tasks.append(asyncio.create_task(asyncio.wait_for(network_idle_event.wait(), event_timeout)))

                # Wait for all required events
                try:
                    await asyncio.gather(*tasks)
                    logger.debug(f"Navigation completed with wait_until: {wait_until}")
                except asyncio.TimeoutError:
                    # If we hit the event timeout but navigation is complete, consider it successful
                    if navigation_complete:
                        logger.debug("Navigation complete but some events timed out")
                    else:
                        raise PageError(f"Navigation timeout of {timeout} seconds exceeded")

                # Ensure execution context is ready with a shorter timeout
                await self.wait_for_execution_context(timeout=2.0)

            finally:
                # Clean up event handlers
                if "Page.frameNavigated" in self._events._listeners:
                    self._events._listeners["Page.frameNavigated"].remove(on_frame_navigated)
                if "Page.loadEventFired" in self._events._listeners:
                    self._events._listeners["Page.loadEventFired"].remove(on_load_event_fired)
                if "Page.domContentEventFired" in self._events._listeners:
                    self._events._listeners["Page.domContentEventFired"].remove(on_dom_content_event_fired)
                if "Network.loadingFinished" in self._events._listeners:
                    self._events._listeners["Network.loadingFinished"].remove(on_network_almost_idle)

        except Exception as e:
            logger.error(f"Navigation failed: {str(e)}")
            raise PageError(f"Navigation failed: {str(e)}")

        finally:
            logger.debug("Navigation attempt completed")

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
        """Get the page content.

        Returns:
            The page content as a string.

        Raises:
            PageError: If getting the content fails.
        """
        try:
            # First ensure we have a valid execution context
            await self.wait_for_execution_context()

            # Try different methods to get the content
            for expression in [
                "document.documentElement.outerHTML",
                "document.documentElement.innerHTML",
                "document.body.outerHTML",
                "document.body.innerHTML"
            ]:
                try:
                    logger.debug(f"Attempting to get content using: {expression}")
                    content = await self.evaluate(expression)
                    if content and isinstance(content, str) and len(content.strip()) > 0:
                        logger.debug(f"Successfully got content using: {expression}")
                        return content
                    logger.debug(f"Empty content returned from: {expression}")
                except Exception as e:
                    logger.debug(f"Failed to get content using {expression}: {e}")
                    continue

            # If all methods failed, try a more robust approach
            logger.debug("Trying robust content extraction...")
            try:
                # Enable DOM domain if not already enabled
                await self.enable_domain("DOM")
                
                # Get the document
                root = await self.send_command("DOM.getDocument", {
                    "depth": -1,
                    "pierce": True
                })
                
                if root and "root" in root:
                    # Get outer HTML of root node
                    result = await self.send_command("DOM.getOuterHTML", {
                        "nodeId": root["root"]["nodeId"]
                    })
                    if result and "outerHTML" in result:
                        content = result["outerHTML"]
                        if content and len(content.strip()) > 0:
                            logger.debug("Successfully got content using DOM.getOuterHTML")
                            return content
                        logger.debug("Empty content returned from DOM.getOuterHTML")
            except Exception as e:
                logger.debug(f"Failed to get content using DOM methods: {e}")

            # If we still don't have content, try one last method
            try:
                logger.debug("Trying final content extraction method...")
                script = """
                    (() => {
                        const html = document.documentElement.outerHTML;
                        if (html) return html;
                        const body = document.body.outerHTML;
                        if (body) return body;
                        return document.documentElement.textContent;
                    })()
                """
                content = await self.evaluate(script)
                if content and isinstance(content, str) and len(content.strip()) > 0:
                    logger.debug("Successfully got content using final method")
                    return content
                logger.debug("Empty content returned from final method")
            except Exception as e:
                logger.debug(f"Failed to get content using final method: {e}")

            raise PageError("Failed to get page content: all methods returned empty content")

        except Exception as e:
            logger.error(f"Error getting page content: {str(e)}")
            raise PageError(f"Failed to get page content: {str(e)}")

        finally:
            logger.debug("Content extraction attempt completed")

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

    async def wait_for_network_idle(self, timeout: float = 30.0, max_inflight_requests: int = 0) -> None:
        """Wait for network to be idle.

        Args:
            timeout: Maximum time to wait in seconds.
            max_inflight_requests: Maximum number of inflight requests to consider network idle.

        Raises:
            PageError: If network does not become idle within timeout.
        """
        try:
            # Enable Network domain if not already enabled
            await self.enable_domain("Network")

            idle_event = asyncio.Event()
            check_idle_handle = None
            last_request_time = time.time()

            def check_network_idle():
                nonlocal check_idle_handle
                if len(self._inflight_requests) <= max_inflight_requests:
                    if time.time() - last_request_time >= 0.5:  # Network considered idle after 0.5s of no activity
                        idle_event.set()
                        return
                if check_idle_handle:
                    check_idle_handle.cancel()
                check_idle_handle = asyncio.get_event_loop().call_later(0.1, check_network_idle)

            # Set up request tracking
            async def on_request_sent(params):
                nonlocal last_request_time
                request_id = params.get("requestId")
                if request_id:
                    self._inflight_requests.add(request_id)
                    last_request_time = time.time()
                    check_network_idle()

            async def on_request_finished(params):
                nonlocal last_request_time
                request_id = params.get("requestId")
                if request_id and request_id in self._inflight_requests:
                    self._inflight_requests.remove(request_id)
                    last_request_time = time.time()
                    check_network_idle()

            # Register event handlers
            self._events.on("Network.requestWillBeSent", on_request_sent)
            self._events.on("Network.loadingFinished", on_request_finished)
            self._events.on("Network.loadingFailed", on_request_finished)

            try:
                # Start checking network state
                check_network_idle()

                # Wait for network to become idle
                try:
                    await asyncio.wait_for(idle_event.wait(), timeout)
                    logger.debug("Network is idle")
                except asyncio.TimeoutError:
                    raise PageError(f"Network did not become idle within {timeout} seconds")

            finally:
                # Clean up event handlers and idle check
                if check_idle_handle:
                    check_idle_handle.cancel()
                if "Network.requestWillBeSent" in self._events._listeners:
                    self._events._listeners["Network.requestWillBeSent"].remove(on_request_sent)
                if "Network.loadingFinished" in self._events._listeners:
                    self._events._listeners["Network.loadingFinished"].remove(on_request_finished)
                if "Network.loadingFailed" in self._events._listeners:
                    self._events._listeners["Network.loadingFailed"].remove(on_request_finished)

        except Exception as e:
            logger.error(f"Error waiting for network idle: {str(e)}")
            raise PageError(f"Failed to wait for network idle: {str(e)}")

        finally:
            logger.debug("Network idle check completed")

    async def wait_for_load(self, timeout: float = 30.0) -> None:
        """Wait for the page load event.

        Args:
            timeout: Maximum time to wait in seconds.

        Raises:
            PageError: If the load event is not fired within the timeout.
        """
        try:
            # Create an event to track load completion
            load_event = asyncio.Event()

            # Set up event handler
            async def on_load(_):
                load_event.set()

            # Register event handler
            self._events.on("Page.loadEventFired", on_load)

            try:
                # Wait for load event
                await asyncio.wait_for(load_event.wait(), timeout)
            except asyncio.TimeoutError:
                raise PageError(f"Page load timeout after {timeout} seconds")
            finally:
                # Clean up event handler
                if "Page.loadEventFired" in self._events._listeners:
                    self._events._listeners["Page.loadEventFired"].remove(on_load)

        except Exception as e:
            raise PageError(f"Failed to wait for page load: {str(e)}")

    async def wait_for_dom_content(self, timeout: float = 30.0) -> None:
        """Wait for the DOMContentLoaded event.

        Args:
            timeout: Maximum time to wait in seconds.

        Raises:
            PageError: If the DOMContentLoaded event is not fired within the timeout.
        """
        try:
            # Create an event to track DOMContentLoaded completion
            dom_event = asyncio.Event()

            # Set up event handler
            async def on_dom_content(_):
                dom_event.set()

            # Register event handler
            self._events.on("Page.domContentEventFired", on_dom_content)

            try:
                # Wait for DOMContentLoaded event
                await asyncio.wait_for(dom_event.wait(), timeout)
            except asyncio.TimeoutError:
                raise PageError(f"DOMContentLoaded timeout after {timeout} seconds")
            finally:
                # Clean up event handler
                if "Page.domContentEventFired" in self._events._listeners:
                    self._events._listeners["Page.domContentEventFired"].remove(on_dom_content)

        except Exception as e:
            raise PageError(f"Failed to wait for DOMContentLoaded: {str(e)}")

    async def get_cookies(self) -> List[Dict]:
        """Get all cookies for the current page.

        Returns:
            A list of cookie objects.

        Raises:
            PageError: If getting cookies fails.
        """
        try:
            # Enable Network domain if not already enabled
            await self.enable_domain("Network")

            # Get all cookies
            result = await self.send_command("Network.getAllCookies")
            if "cookies" in result:
                logger.debug(f"Retrieved {len(result['cookies'])} cookies")
                return result["cookies"]
            
            logger.debug("No cookies found in response")
            return []

        except Exception as e:
            logger.error(f"Error getting cookies: {str(e)}")
            raise PageError(f"Failed to get cookies: {str(e)}")

        finally:
            logger.debug("Cookie retrieval completed")