"""
Page module for CDP Browser.
Contains the Page class for managing browser pages/tabs.
"""
import asyncio
import base64
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urlparse, urlunparse

from cdp_browser.core.exceptions import CDPError, CDPTimeoutError
from cdp_browser.core.connection import CDPConnection

logger = logging.getLogger(__name__)


class Page:
    """
    Manages a browser page/tab via CDP.
    Supports async context manager protocol for automatic attachment/detachment.
    """

    def __init__(self, browser, target_id: str, target_info: Dict[str, Any]):
        """
        Initialize a Page instance.

        Args:
            browser: Browser instance
            target_id: Target ID for this page
            target_info: Target information
        """
        self.browser = browser
        self.target_id = target_id
        self.target_info = target_info
        self.connection = None
        self.frame_id = None
        self.url = target_info.get("url", "")
        self.title = target_info.get("title", "")
        self.attached = False
        self.navigation_promise = None

    async def __aenter__(self) -> "Page":
        """
        Enter async context, attaching to the page.

        Returns:
            Page instance
        """
        await self.attach()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit async context, detaching from the page.
        """
        await self.detach()

    async def attach(self) -> None:
        """
        Attach to the page target.
        """
        if not self.browser.connection:
            raise CDPError("Browser not connected")
        
        # Get the WebSocket URL for this page
        ws_url = self._get_ws_url()
        if not ws_url:
            raise CDPError("WebSocket URL not found for page")
        
        try:
            # Create a new CDP connection for this page
            self.connection = CDPConnection(ws_url)
            await self.connection.connect()
            
            # Enable necessary domains
            await self._send_command("Page.enable")
            await self._send_command("Runtime.enable")
            
            # Get frame ID
            result = await self._send_command("Page.getFrameTree")
            frame = result.get("frameTree", {}).get("frame", {})
            self.frame_id = frame.get("id")
            
            if not self.frame_id:
                raise CDPError("Failed to get frame ID")
            
            self.attached = True
            logger.info(f"Attached to page: {self.url}")
        except Exception as e:
            if self.connection:
                await self.connection.disconnect()
                self.connection = None
            raise CDPError(f"Failed to attach to page: {str(e)}")

    def _get_ws_url(self) -> Optional[str]:
        """
        Get the WebSocket URL for this page, ensuring correct host and port.

        Returns:
            WebSocket URL for the page
        """
        ws_url = self.target_info.get("webSocketDebuggerUrl")
        if not ws_url:
            return None
        
        # Parse the URL
        parsed = urlparse(ws_url)
        
        # Replace host and port if needed
        if "127.0.0.1" in parsed.netloc or "localhost" in parsed.netloc:
            netloc = f"{self.browser.host}:{self.browser.port}"
            parsed = parsed._replace(netloc=netloc)
        
        return urlunparse(parsed)

    async def detach(self) -> None:
        """
        Detach from the page target.
        """
        if not self.connection:
            return
        
        try:
            # Cancel any pending navigation
            if self.navigation_promise and not self.navigation_promise.done():
                self.navigation_promise.cancel()
                self.navigation_promise = None
            
            # Disable domains
            try:
                await self._send_command("Page.disable")
                await self._send_command("Runtime.disable")
            except Exception as e:
                logger.warning(f"Error disabling domains: {str(e)}")
            
            # Disconnect from page
            await self.connection.disconnect()
        except Exception as e:
            logger.warning(f"Error detaching from page: {str(e)}")
        finally:
            self.attached = False
            self.connection = None
            logger.info(f"Detached from page: {self.url}")

    async def _send_command(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Send a command to the page target.

        Args:
            method: CDP method name
            params: CDP method parameters

        Returns:
            Response from CDP
        """
        if not self.connection:
            raise CDPError("Not connected to page")
        
        try:
            return await self.connection.send_command(method, params or {})
        except Exception as e:
            raise CDPError(f"Failed to send command {method}: {str(e)}")

    async def navigate(self, url: str, timeout: int = 30) -> None:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to
            timeout: Timeout in seconds

        Raises:
            CDPTimeoutError: If navigation times out
            CDPError: If navigation fails
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        # Create a future for navigation completion
        navigation_complete = asyncio.Future()
        load_complete = asyncio.Future()
        
        # Add event listeners for navigation events
        async def on_frame_navigated(params):
            frame = params.get("frame", {})
            frame_id = frame.get("id")
            
            # Only consider main frame navigation
            if frame_id == self.frame_id:
                url = frame.get("url", "")
                self.url = url
                
                if not navigation_complete.done():
                    navigation_complete.set_result(True)
        
        async def on_load_event_fired(_):
            if not load_complete.done():
                load_complete.set_result(True)
        
        # Add event listeners
        self.connection.add_event_listener(
            "Page.frameNavigated", on_frame_navigated
        )
        self.connection.add_event_listener(
            "Page.loadEventFired", on_load_event_fired
        )
        
        try:
            # Navigate to URL
            result = await self._send_command("Page.navigate", {"url": url})
            
            if "errorText" in result:
                raise CDPError(f"Navigation failed: {result['errorText']}")
            
            # Wait for navigation and load to complete
            try:
                await asyncio.wait_for(
                    asyncio.gather(navigation_complete, load_complete),
                    timeout
                )
            except asyncio.TimeoutError:
                raise CDPTimeoutError(f"Navigation to {url} timed out after {timeout}s")
            
            # Update page info
            self.url = url
            
            # Get page title
            try:
                self.title = await self.evaluate("document.title") or ""
            except Exception as e:
                logger.warning(f"Failed to get page title: {str(e)}")
                self.title = ""
            
            logger.info(f"Navigated to: {url}")
        finally:
            # Remove event listeners
            self.connection.remove_event_listener(
                "Page.frameNavigated", on_frame_navigated
            )
            self.connection.remove_event_listener(
                "Page.loadEventFired", on_load_event_fired
            )

    async def evaluate(self, expression: str) -> Any:
        """
        Evaluate JavaScript expression.

        Args:
            expression: JavaScript expression to evaluate

        Returns:
            Result of the evaluation

        Raises:
            CDPError: If evaluation fails
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        try:
            result = await self._send_command(
                "Runtime.evaluate",
                {
                    "expression": expression,
                    "returnByValue": True,
                    "awaitPromise": True,
                },
            )
            
            # Check for errors
            if "exceptionDetails" in result:
                details = result["exceptionDetails"]
                error_text = details.get("text", "Unknown error")
                exception = details.get("exception", {})
                description = exception.get("description", "")
                raise CDPError(f"JavaScript error: {error_text} - {description}")
            
            # Get the result value
            result_obj = result.get("result", {})
            if result_obj.get("type") == "undefined":
                return None
            
            return result_obj.get("value")
        except CDPError:
            raise
        except Exception as e:
            raise CDPError(f"Failed to evaluate expression: {str(e)}")

    async def screenshot(self, format: str = "png", quality: int = 100) -> bytes:
        """
        Take a screenshot of the page.

        Args:
            format: Screenshot format (png or jpeg)
            quality: Screenshot quality (0-100, jpeg only)

        Returns:
            Screenshot as bytes

        Raises:
            CDPError: If screenshot capture fails
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        # Validate format
        if format not in ["png", "jpeg"]:
            raise ValueError("Format must be 'png' or 'jpeg'")
        
        try:
            # Take screenshot
            result = await self._send_command(
                "Page.captureScreenshot",
                {"format": format, "quality": quality},
            )
            
            # Decode base64 data
            data = result.get("data", "")
            if not data:
                raise CDPError("No screenshot data received")
            
            return base64.b64decode(data)
        except Exception as e:
            raise CDPError(f"Failed to capture screenshot: {str(e)}")

    async def get_cookies(self) -> List[Dict[str, Any]]:
        """
        Get cookies for the page.

        Returns:
            List of cookies

        Raises:
            CDPError: If getting cookies fails
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        try:
            result = await self._send_command("Network.getAllCookies")
            return result.get("cookies", [])
        except Exception as e:
            raise CDPError(f"Failed to get cookies: {str(e)}")

    async def set_cookies(self, cookies: List[Dict[str, Any]]) -> None:
        """
        Set cookies for the page.

        Args:
            cookies: List of cookies to set

        Raises:
            CDPError: If setting cookies fails
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        try:
            await self._send_command("Network.setCookies", {"cookies": cookies})
        except Exception as e:
            raise CDPError(f"Failed to set cookies: {str(e)}")

    async def wait_for_load(self, timeout: int = 30) -> None:
        """
        Wait for page load event.

        Args:
            timeout: Timeout in seconds

        Raises:
            CDPTimeoutError: If load times out
            CDPError: If waiting for load fails
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        load_complete = asyncio.Future()
        
        async def on_load_event_fired(_):
            if not load_complete.done():
                load_complete.set_result(True)
        
        self.connection.add_event_listener(
            "Page.loadEventFired", on_load_event_fired
        )
        
        try:
            await asyncio.wait_for(load_complete, timeout)
        except asyncio.TimeoutError:
            raise CDPTimeoutError(f"Page load timed out after {timeout}s")
        except Exception as e:
            raise CDPError(f"Failed to wait for page load: {str(e)}")
        finally:
            self.connection.remove_event_listener(
                "Page.loadEventFired", on_load_event_fired
            )

    async def click(self, selector: str) -> None:
        """
        Click an element on the page.

        Args:
            selector: CSS selector for the element
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        # Execute click via JavaScript
        await self.evaluate(f"""
            () => {{
                const element = document.querySelector('{selector}');
                if (!element) {{
                    throw new Error('Element not found: {selector}');
                }}
                element.click();
            }}
        """)

    async def type(self, selector: str, text: str, clear: bool = False) -> None:
        """
        Type text into an input element.

        Args:
            selector: CSS selector for the input element
            text: Text to type
            clear: Whether to clear the input before typing
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        # Execute typing via JavaScript
        await self.evaluate(f"""
            () => {{
                const element = document.querySelector('{selector}');
                if (!element) {{
                    throw new Error('Element not found: {selector}');
                }}
                if ({str(clear).lower()}) {{
                    element.value = '';
                }}
                element.value = '{text}';
                element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                element.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        """)

    async def select(self, selector: str, value: str) -> None:
        """
        Select an option in a select element.

        Args:
            selector: CSS selector for the select element
            value: Value of the option to select
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        # Execute selection via JavaScript
        await self.evaluate(f"""
            () => {{
                const element = document.querySelector('{selector}');
                if (!element) {{
                    throw new Error('Element not found: {selector}');
                }}
                element.value = '{value}';
                element.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        """)

    async def check(self, selector: str) -> None:
        """
        Check a checkbox element.

        Args:
            selector: CSS selector for the checkbox element
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        # Execute checking via JavaScript
        await self.evaluate(f"""
            () => {{
                const element = document.querySelector('{selector}');
                if (!element) {{
                    throw new Error('Element not found: {selector}');
                }}
                if (!element.checked) {{
                    element.click();
                }}
            }}
        """)

    async def uncheck(self, selector: str) -> None:
        """
        Uncheck a checkbox element.

        Args:
            selector: CSS selector for the checkbox element
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        # Execute unchecking via JavaScript
        await self.evaluate(f"""
            () => {{
                const element = document.querySelector('{selector}');
                if (!element) {{
                    throw new Error('Element not found: {selector}');
                }}
                if (element.checked) {{
                    element.click();
                }}
            }}
        """)

    async def press_keys(self, keys: List[str]) -> None:
        """
        Press a combination of keys.

        Args:
            keys: List of keys to press (e.g., ['Control', 'a'])
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        # Execute key press via JavaScript
        key_string = '+'.join(keys)
        await self.evaluate(f"""
            () => {{
                const event = new KeyboardEvent('keydown', {{
                    key: '{keys[-1]}',
                    code: '{keys[-1]}',
                    ctrlKey: {str('Control' in keys).lower()},
                    shiftKey: {str('Shift' in keys).lower()},
                    altKey: {str('Alt' in keys).lower()},
                    metaKey: {str('Meta' in keys).lower()},
                    bubbles: true
                }});
                document.dispatchEvent(event);
            }}
        """) 