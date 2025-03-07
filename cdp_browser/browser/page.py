"""
Page module for CDP Browser.
Contains the Page class for managing browser pages/tabs.
"""
import asyncio
import base64
import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Union, Tuple

import aiohttp

from cdp_browser.core.exceptions import CDPError, CDPTimeoutError, CDPNavigationError

logger = logging.getLogger(__name__)


class Page:
    """
    Manages a browser page/tab via CDP.
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
        self.ws_url = target_info.get("webSocketDebuggerUrl", "")
        self.url = target_info.get("url", "")
        self.title = target_info.get("title", "")
        self.connection = None
        self.attached = False
        self.load_event_fired = asyncio.Event()
        self.dom_content_loaded = asyncio.Event()
        self._event_listeners = {}
        self._navigation_history = []
        self._can_go_back = False
        self._can_go_forward = False

    async def attach(self) -> None:
        """
        Attach to the page target.
        """
        if not self.ws_url:
            # If no WebSocket URL is provided, try to construct it
            if self.browser.is_browserless:
                self.ws_url = f"ws://{self.browser.host}:{self.browser.port}/devtools/page/{self.target_id}"
            else:
                raise CDPError("WebSocket URL not found in target info")
        
        # Create a new connection to the page
        self.connection = aiohttp.ClientSession()
        self.attached = True
        logger.info(f"Attached to page: {self.url}")

    async def detach(self) -> None:
        """
        Detach from the page target.
        """
        if self.connection:
            await self.connection.close()
            self.connection = None
        
        self.attached = False
        logger.info(f"Detached from page: {self.url}")

    def _setup_event_listeners(self) -> None:
        """
        Set up event listeners for page events.
        """
        if not self.connection:
            return
        
        # Page load event
        async def on_load_event_fired(params):
            self.load_event_fired.set()
            # Reset for next navigation
            asyncio.create_task(self._reset_load_event())
        
        # DOM content loaded event
        async def on_dom_content_loaded(params):
            self.dom_content_loaded.set()
            # Reset for next navigation
            asyncio.create_task(self._reset_dom_content_loaded())
        
        # Frame navigated event
        async def on_frame_navigated(params):
            frame = params.get("frame", {})
            frame_id = frame.get("id")
            
            # Only consider main frame navigation
            if frame_id == self.frame_id:
                url = frame.get("url", "")
                self.url = url
                
                # Update navigation history
                asyncio.create_task(self._update_navigation_history())
        
        # Add event listeners
        self.browser.connection.add_event_listener("Page.loadEventFired", on_load_event_fired)
        self.browser.connection.add_event_listener("Page.domContentEventFired", on_dom_content_loaded)
        self.browser.connection.add_event_listener("Page.frameNavigated", on_frame_navigated)
        
        # Store listeners for cleanup
        self._event_listeners = {
            "Page.loadEventFired": on_load_event_fired,
            "Page.domContentEventFired": on_dom_content_loaded,
            "Page.frameNavigated": on_frame_navigated,
        }

    async def _reset_load_event(self) -> None:
        """
        Reset the load event for the next navigation.
        """
        self.load_event_fired.clear()

    async def _reset_dom_content_loaded(self) -> None:
        """
        Reset the DOM content loaded event for the next navigation.
        """
        self.dom_content_loaded.clear()

    async def _send_command(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Send a command to the page target.

        Args:
            method: CDP method name
            params: CDP method parameters

        Returns:
            Response from CDP
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        if not self.connection:
            raise CDPError("No connection to page")
        
        # Create message
        message_id = id(method) % 10000  # Simple ID generation
        message = {
            "id": message_id,
            "method": method,
            "params": params or {}
        }
        
        # Send message via WebSocket
        try:
            async with self.connection.ws_connect(self.ws_url) as ws:
                await ws.send_json(message)
                
                # Wait for response
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        if data.get("id") == message_id:
                            if "result" in data:
                                return data["result"]
                            elif "error" in data:
                                raise CDPError(f"CDP Error: {data['error']}")
        except Exception as e:
            logger.error(f"Error sending command {method}: {str(e)}")
            raise CDPError(f"Failed to send command {method}: {str(e)}")

    async def _update_navigation_history(self) -> None:
        """
        Update the navigation history.
        """
        if not self.attached:
            return
        
        try:
            result = await self._send_command("Page.getNavigationHistory")
            entries = result.get("entries", [])
            current_index = result.get("currentIndex", 0)
            
            self._navigation_history = entries
            self._can_go_back = current_index > 0
            self._can_go_forward = current_index < len(entries) - 1
        except Exception as e:
            logger.warning(f"Error updating navigation history: {str(e)}")

    async def navigate(self, url: str, timeout: int = 30, wait_until: str = "load") -> None:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to
            timeout: Timeout in seconds
            wait_until: When to consider navigation complete:
                        "load" - wait for load event
                        "domcontentloaded" - wait for DOMContentLoaded event
                        "networkidle" - wait for network to be idle

        Raises:
            CDPTimeoutError: If navigation times out
            CDPNavigationError: If navigation fails
        """
        if self.browser.is_browserless:
            # For browserless, we'll use the direct API
            try:
                content = await self.browser.get_content(url)
                self.url = url
                
                # Try to extract title from content
                title_match = re.search(r"<title>(.*?)</title>", content)
                if title_match:
                    self.title = title_match.group(1)
                else:
                    self.title = url
                
                logger.info(f"Navigated to: {url}")
            except Exception as e:
                logger.error(f"Error navigating to {url}: {str(e)}")
                raise CDPNavigationError(f"Failed to navigate to {url}: {str(e)}")
        else:
            # For regular Chrome, use CDP
            if not self.attached:
                raise CDPError("Not attached to page")
            
            try:
                # Navigate to URL
                async with self.connection.ws_connect(self.ws_url) as ws:
                    # Send navigate command
                    await ws.send_json({
                        "id": 1,
                        "method": "Page.navigate",
                        "params": {"url": url}
                    })
                    
                    # Wait for response
                    navigation_complete = False
                    load_event_fired = False
                    dom_content_loaded = False
                    
                    start_time = asyncio.get_event_loop().time()
                    
                    while asyncio.get_event_loop().time() - start_time < timeout:
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                
                                # Check for navigation response
                                if data.get("id") == 1:
                                    if "error" in data:
                                        raise CDPNavigationError(f"Navigation failed: {data['error']}")
                                    navigation_complete = True
                                
                                # Check for load event
                                if data.get("method") == "Page.loadEventFired":
                                    load_event_fired = True
                                
                                # Check for DOMContentLoaded event
                                if data.get("method") == "Page.domContentEventFired":
                                    dom_content_loaded = True
                                
                                # Check if we're done based on wait_until
                                if navigation_complete:
                                    if wait_until == "load" and load_event_fired:
                                        break
                                    elif wait_until == "domcontentloaded" and dom_content_loaded:
                                        break
                                    elif wait_until == "networkidle":
                                        # For networkidle, we'll just wait a bit after navigation
                                        await asyncio.sleep(0.5)
                                        break
                                    elif wait_until is None:
                                        break
                        
                            # Check if we've waited long enough
                            if asyncio.get_event_loop().time() - start_time >= timeout:
                                raise CDPTimeoutError(f"Navigation to {url} timed out after {timeout}s")
                
                # Update page info
                self.url = url
                
                # Get page title
                result = await self.evaluate("document.title")
                self.title = result
                
                logger.info(f"Navigated to: {url}")
            except CDPTimeoutError:
                raise
            except CDPNavigationError:
                raise
            except Exception as e:
                logger.error(f"Error navigating to {url}: {str(e)}")
                raise CDPError(f"Failed to navigate to {url}: {str(e)}")

    async def reload(self, ignore_cache: bool = False, timeout: int = 30) -> None:
        """
        Reload the current page.

        Args:
            ignore_cache: Whether to ignore cache during reload
            timeout: Timeout in seconds

        Raises:
            CDPTimeoutError: If reload times out
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        # Reset events
        self.load_event_fired.clear()
        
        # Reload the page
        await self._send_command("Page.reload", {"ignoreCache": ignore_cache})
        
        # Wait for load event
        try:
            await asyncio.wait_for(self.load_event_fired.wait(), timeout)
        except asyncio.TimeoutError:
            raise CDPTimeoutError(f"Page reload timed out after {timeout}s")
        
        # Update page info
        result = await self.evaluate("document.title")
        self.title = result
        
        # Update navigation history
        await self._update_navigation_history()
        
        logger.info(f"Reloaded page: {self.url}")

    async def go_back(self, timeout: int = 30) -> bool:
        """
        Navigate back in history.

        Args:
            timeout: Timeout in seconds

        Returns:
            True if successful, False if no history available

        Raises:
            CDPTimeoutError: If navigation times out
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        # Check if we can go back
        if not self._can_go_back:
            return False
        
        # Reset events
        self.load_event_fired.clear()
        
        # Get current history index
        result = await self._send_command("Page.getNavigationHistory")
        current_index = result.get("currentIndex", 0)
        
        if current_index <= 0:
            return False
        
        # Go back
        await self._send_command("Page.navigateToHistoryEntry", {"entryId": current_index - 1})
        
        # Wait for load event
        try:
            await asyncio.wait_for(self.load_event_fired.wait(), timeout)
        except asyncio.TimeoutError:
            raise CDPTimeoutError(f"Back navigation timed out after {timeout}s")
        
        # Update page info
        result = await self.evaluate("document.title")
        self.title = result
        self.url = self._navigation_history[current_index - 1].get("url", "")
        
        # Update navigation history
        await self._update_navigation_history()
        
        logger.info(f"Navigated back to: {self.url}")
        return True

    async def go_forward(self, timeout: int = 30) -> bool:
        """
        Navigate forward in history.

        Args:
            timeout: Timeout in seconds

        Returns:
            True if successful, False if no forward history available

        Raises:
            CDPTimeoutError: If navigation times out
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        # Check if we can go forward
        if not self._can_go_forward:
            return False
        
        # Reset events
        self.load_event_fired.clear()
        
        # Get current history index
        result = await self._send_command("Page.getNavigationHistory")
        current_index = result.get("currentIndex", 0)
        entries = result.get("entries", [])
        
        if current_index >= len(entries) - 1:
            return False
        
        # Go forward
        await self._send_command("Page.navigateToHistoryEntry", {"entryId": current_index + 1})
        
        # Wait for load event
        try:
            await asyncio.wait_for(self.load_event_fired.wait(), timeout)
        except asyncio.TimeoutError:
            raise CDPTimeoutError(f"Forward navigation timed out after {timeout}s")
        
        # Update page info
        result = await self.evaluate("document.title")
        self.title = result
        self.url = self._navigation_history[current_index + 1].get("url", "")
        
        # Update navigation history
        await self._update_navigation_history()
        
        logger.info(f"Navigated forward to: {self.url}")
        return True

    async def evaluate(self, expression: str, return_by_value: bool = True, await_promise: bool = True) -> Any:
        """
        Evaluate JavaScript expression.

        Args:
            expression: JavaScript expression to evaluate
            return_by_value: Whether to return the result by value
            await_promise: Whether to await any promise in the expression

        Returns:
            Result of the evaluation
        """
        if self.browser.is_browserless:
            # For browserless, we'll use the /function endpoint
            try:
                function = f"async ({ page }) => {{ return {expression}; }}"
                result = await self.browser.execute_function(self.url, function)
                return result
            except Exception as e:
                logger.error(f"Error evaluating expression: {str(e)}")
                raise CDPError(f"Failed to evaluate expression: {str(e)}")
        else:
            # For regular Chrome, use CDP
            if not self.attached:
                raise CDPError("Not attached to page")
            
            try:
                async with self.connection.ws_connect(self.ws_url) as ws:
                    # Send evaluate command
                    await ws.send_json({
                        "id": 1,
                        "method": "Runtime.evaluate",
                        "params": {
                            "expression": expression,
                            "returnByValue": return_by_value,
                            "awaitPromise": await_promise
                        }
                    })
                    
                    # Wait for response
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            if data.get("id") == 1:
                                if "result" in data:
                                    result = data["result"]
                                    if "result" in result:
                                        return result["result"].get("value")
                                    return result
                                elif "error" in data:
                                    raise CDPError(f"Evaluation error: {data['error']}")
            except Exception as e:
                logger.error(f"Error evaluating expression: {str(e)}")
                raise CDPError(f"Failed to evaluate expression: {str(e)}")

    async def wait_for_selector(self, selector: str, timeout: int = 30, visible: bool = False) -> bool:
        """
        Wait for an element matching the selector to appear.

        Args:
            selector: CSS selector
            timeout: Timeout in seconds
            visible: Whether to wait for the element to be visible

        Returns:
            True if the element was found, False if timed out

        Raises:
            CDPTimeoutError: If waiting times out
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            # Check if element exists
            if visible:
                script = f"""
                (function() {{
                    const el = document.querySelector('{selector}');
                    if (!el) return false;
                    
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    
                    return style.display !== 'none' && 
                           style.visibility !== 'hidden' && 
                           style.opacity !== '0' &&
                           rect.width > 0 &&
                           rect.height > 0;
                }})()
                """
            else:
                script = f"!!document.querySelector('{selector}')"
            
            result = await self.evaluate(script)
            value = result.get("result", {}).get("value", False)
            
            if value:
                return True
            
            # Wait a bit before trying again
            await asyncio.sleep(0.1)
        
        return False

    async def wait_for_navigation(self, timeout: int = 30, url_pattern: Optional[str] = None) -> None:
        """
        Wait for navigation to complete.

        Args:
            timeout: Timeout in seconds
            url_pattern: Optional URL pattern to wait for

        Raises:
            CDPTimeoutError: If navigation times out
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        # Create a future for navigation completion
        navigation_complete = asyncio.Future()
        
        # Add event listener for navigation events
        async def on_frame_navigated(params):
            frame = params.get("frame", {})
            frame_id = frame.get("id")
            
            # Only consider main frame navigation
            if frame_id == self.frame_id:
                url = frame.get("url", "")
                
                # Check URL pattern if provided
                if url_pattern is None or (url_pattern and re.search(url_pattern, url)):
                    if not navigation_complete.done():
                        navigation_complete.set_result(True)
        
        # Add event listener
        self.browser.connection.add_event_listener(
            "Page.frameNavigated", on_frame_navigated
        )
        
        try:
            # Wait for navigation to complete
            try:
                await asyncio.wait_for(navigation_complete, timeout)
                
                # Wait for load event
                await asyncio.wait_for(self.load_event_fired.wait(), timeout)
            except asyncio.TimeoutError:
                raise CDPTimeoutError(f"Navigation timed out after {timeout}s")
            
            # Update page info
            result = await self.evaluate("document.title")
            self.title = result
            
            # Update navigation history
            await self._update_navigation_history()
        finally:
            # Remove event listener
            self.browser.connection.remove_event_listener(
                "Page.frameNavigated", on_frame_navigated
            )

    async def screenshot(self, format: str = "png", quality: int = 100, full_page: bool = False) -> bytes:
        """
        Take a screenshot of the page.

        Args:
            format: Screenshot format (png or jpeg)
            quality: Screenshot quality (0-100, jpeg only)
            full_page: Whether to take a screenshot of the full page

        Returns:
            Screenshot as bytes
        """
        if self.browser.is_browserless:
            # For browserless, we'll use the /screenshot endpoint
            options = {
                "fullPage": full_page,
                "type": format,
                "quality": quality
            }
            
            return await self.browser.take_screenshot(self.url, options)
        else:
            # For regular Chrome, use CDP
            if not self.attached:
                raise CDPError("Not attached to page")
            
            # Validate format
            if format not in ["png", "jpeg"]:
                raise ValueError("Format must be 'png' or 'jpeg'")
            
            try:
                async with self.connection.ws_connect(self.ws_url) as ws:
                    if full_page:
                        # Get page dimensions
                        await ws.send_json({
                            "id": 1,
                            "method": "Runtime.evaluate",
                            "params": {
                                "expression": """
                                ({
                                    width: Math.max(document.body.scrollWidth, document.documentElement.scrollWidth),
                                    height: Math.max(document.body.scrollHeight, document.documentElement.scrollHeight),
                                    deviceScaleFactor: window.devicePixelRatio || 1,
                                    mobile: false
                                })
                                """,
                                "returnByValue": True
                            }
                        })
                        
                        # Wait for dimensions response
                        dimensions = None
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                if data.get("id") == 1:
                                    if "result" in data and "result" in data["result"]:
                                        dimensions = data["result"]["result"].get("value", {})
                                    break
                        
                        if dimensions:
                            # Set viewport to full page size
                            await ws.send_json({
                                "id": 2,
                                "method": "Emulation.setDeviceMetricsOverride",
                                "params": {
                                    "width": dimensions.get("width", 800),
                                    "height": dimensions.get("height", 600),
                                    "deviceScaleFactor": 1,
                                    "mobile": False
                                }
                            })
                            
                            # Wait for viewport response
                            async for msg in ws:
                                if msg.type == aiohttp.WSMsgType.TEXT:
                                    data = json.loads(msg.data)
                                    if data.get("id") == 2:
                                        break
                    
                    # Take screenshot
                    await ws.send_json({
                        "id": 3,
                        "method": "Page.captureScreenshot",
                        "params": {
                            "format": format,
                            "quality": quality
                        }
                    })
                    
                    # Wait for screenshot response
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            if data.get("id") == 3:
                                if "result" in data and "data" in data["result"]:
                                    screenshot_data = data["result"]["data"]
                                    return base64.b64decode(screenshot_data)
                                elif "error" in data:
                                    raise CDPError(f"Screenshot error: {data['error']}")
                    
                    if full_page:
                        # Reset viewport
                        await ws.send_json({
                            "id": 4,
                            "method": "Emulation.clearDeviceMetricsOverride"
                        })
            except Exception as e:
                logger.error(f"Error taking screenshot: {str(e)}")
                raise CDPError(f"Failed to take screenshot: {str(e)}")
            
            raise CDPError("Failed to take screenshot: No data received")

    async def get_cookies(self) -> List[Dict[str, Any]]:
        """
        Get cookies for the page.

        Returns:
            List of cookies
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        result = await self._send_command("Network.getAllCookies")
        return result.get("cookies", [])

    async def set_cookies(self, cookies: List[Dict[str, Any]]) -> None:
        """
        Set cookies for the page.

        Args:
            cookies: List of cookies to set
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        await self._send_command("Network.setCookies", {"cookies": cookies})

    async def clear_cookies(self) -> None:
        """
        Clear all cookies.
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        await self._send_command("Network.clearBrowserCookies")

    async def get_html(self) -> str:
        """
        Get the HTML content of the page.

        Returns:
            HTML content as string
        """
        if self.browser.is_browserless:
            # For browserless, we'll use the /content endpoint
            return await self.browser.get_content(self.url)
        else:
            # For regular Chrome, use CDP
            if not self.attached:
                raise CDPError("Not attached to page")
            
            result = await self.evaluate("document.documentElement.outerHTML")
            return result

    async def get_text(self) -> str:
        """
        Get the text content of the page.

        Returns:
            Text content as string
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        result = await self.evaluate("document.body.innerText")
        return result

    async def wait_for_function(self, function: str, timeout: int = 30, polling: int = 100) -> Any:
        """
        Wait for a function to return a truthy value.

        Args:
            function: JavaScript function to evaluate
            timeout: Timeout in seconds
            polling: Polling interval in milliseconds

        Returns:
            Result of the function

        Raises:
            CDPTimeoutError: If waiting times out
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            result = await self.evaluate(function)
            value = result.get("result", {}).get("value")
            
            if value:
                return value
            
            # Wait before trying again
            await asyncio.sleep(polling / 1000)
        
        raise CDPTimeoutError(f"Function timed out after {timeout}s: {function}")

    async def set_viewport(self, width: int, height: int, device_scale_factor: float = 1, mobile: bool = False) -> None:
        """
        Set the viewport size.

        Args:
            width: Viewport width
            height: Viewport height
            device_scale_factor: Device scale factor
            mobile: Whether to emulate a mobile device
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        await self._send_command(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": width,
                "height": height,
                "deviceScaleFactor": device_scale_factor,
                "mobile": mobile
            }
        )

    async def reset_viewport(self) -> None:
        """
        Reset the viewport to default.
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        await self._send_command("Emulation.clearDeviceMetricsOverride") 