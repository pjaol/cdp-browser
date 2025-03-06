"""
Page module for CDP Browser.
Contains the Page class for managing browser pages/tabs.
"""
import asyncio
import base64
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Union

from cdp_browser.core.exceptions import CDPError, CDPTimeoutError

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
        self.session_id = None
        self.frame_id = None
        self.url = target_info.get("url", "")
        self.title = target_info.get("title", "")
        self.attached = False
        self.navigation_promise = None

    async def attach(self) -> None:
        """
        Attach to the page target.
        """
        if not self.browser.connection:
            raise CDPError("Browser not connected")
        
        # Attach to target
        result = await self.browser.connection.send_command(
            "Target.attachToTarget", {"targetId": self.target_id, "flatten": True}
        )
        
        self.session_id = result.get("sessionId")
        if not self.session_id:
            raise CDPError("Failed to attach to target")
        
        # Enable necessary domains
        await self._send_command("Page.enable")
        await self._send_command("Runtime.enable")
        
        # Get frame ID
        result = await self._send_command("Page.getFrameTree")
        frame = result.get("frameTree", {}).get("frame", {})
        self.frame_id = frame.get("id")
        
        self.attached = True
        logger.info(f"Attached to page: {self.url}")

    async def detach(self) -> None:
        """
        Detach from the page target.
        """
        if not self.browser.connection or not self.session_id:
            return
        
        try:
            # Disable domains
            await self._send_command("Page.disable")
            await self._send_command("Runtime.disable")
            
            # Detach from target
            await self.browser.connection.send_command(
                "Target.detachFromTarget", {"sessionId": self.session_id}
            )
        except Exception as e:
            logger.warning(f"Error detaching from page: {str(e)}")
        finally:
            self.attached = False
            self.session_id = None
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
        if not self.browser.connection:
            raise CDPError("Browser not connected")
        
        if not self.session_id:
            raise CDPError("Not attached to page")
        
        # Add sessionId to params
        command_params = {"sessionId": self.session_id}
        if params:
            command_params.update(params)
        
        return await self.browser.connection.send_command(method, command_params)

    async def navigate(self, url: str, timeout: int = 30) -> None:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to
            timeout: Timeout in seconds

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
                self.url = url
                
                if not navigation_complete.done():
                    navigation_complete.set_result(True)
        
        # Add event listener
        self.browser.connection.add_event_listener(
            "Page.frameNavigated", on_frame_navigated
        )
        
        try:
            # Navigate to URL
            result = await self._send_command("Page.navigate", {"url": url})
            
            # Wait for navigation to complete
            try:
                await asyncio.wait_for(navigation_complete, timeout)
            except asyncio.TimeoutError:
                raise CDPTimeoutError(f"Navigation to {url} timed out after {timeout}s")
            
            # Update page info
            self.url = url
            
            # Get page title
            result = await self.evaluate("document.title")
            self.title = result.get("result", {}).get("value", "")
            
            logger.info(f"Navigated to: {url}")
        finally:
            # Remove event listener
            self.browser.connection.remove_event_listener(
                "Page.frameNavigated", on_frame_navigated
            )

    async def evaluate(self, expression: str) -> Dict[str, Any]:
        """
        Evaluate JavaScript expression.

        Args:
            expression: JavaScript expression to evaluate

        Returns:
            Result of the evaluation
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        return await self._send_command(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            },
        )

    async def screenshot(self, format: str = "png", quality: int = 100) -> bytes:
        """
        Take a screenshot of the page.

        Args:
            format: Screenshot format (png or jpeg)
            quality: Screenshot quality (0-100, jpeg only)

        Returns:
            Screenshot as bytes
        """
        if not self.attached:
            raise CDPError("Not attached to page")
        
        # Validate format
        if format not in ["png", "jpeg"]:
            raise ValueError("Format must be 'png' or 'jpeg'")
        
        # Take screenshot
        result = await self._send_command(
            "Page.captureScreenshot",
            {"format": format, "quality": quality},
        )
        
        # Decode base64 data
        data = result.get("data", "")
        return base64.b64decode(data)

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