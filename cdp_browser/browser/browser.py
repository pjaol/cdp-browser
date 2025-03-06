"""
Browser module for CDP Browser.
Contains the Browser class for managing Chrome browser instances.
"""
import asyncio
import json
import logging
import os
from typing import Dict, List, Optional, Union

import aiohttp

from cdp_browser.browser.page import Page
from cdp_browser.core.connection import CDPConnection
from cdp_browser.core.exceptions import CDPConnectionError, CDPError
from cdp_browser.core.protocol import CDPProtocol

logger = logging.getLogger(__name__)


class Browser:
    """
    Manages a Chrome browser instance via CDP.
    """

    def __init__(self, host: str = "localhost", port: int = 9222):
        """
        Initialize a Browser instance.

        Args:
            host: Chrome DevTools host
            port: Chrome DevTools port
        """
        self.host = host
        self.port = port
        self.connection = None
        self.pages = {}
        self.targets = {}
        self.debug_url = f"http://{host}:{port}"

    async def connect(self) -> None:
        """
        Connect to Chrome DevTools Protocol.
        """
        try:
            # Get browser WebSocket URL
            browser_ws_url = await self._get_browser_ws_url()
            
            # Connect to browser
            self.connection = CDPConnection(browser_ws_url)
            await self.connection.connect()
            
            # Get browser version
            version = await self.get_version()
            logger.info(f"Connected to Chrome {version.get('Browser')}")
            
            # Attach to targets
            await self._attach_to_targets()
        except Exception as e:
            raise CDPConnectionError(f"Failed to connect to browser: {str(e)}")

    async def disconnect(self) -> None:
        """
        Disconnect from Chrome DevTools Protocol.
        """
        if self.connection:
            await self.connection.disconnect()
            self.connection = None
            self.pages = {}
            self.targets = {}
            logger.info("Disconnected from browser")

    async def _get_browser_ws_url(self) -> str:
        """
        Get the WebSocket URL for the browser.

        Returns:
            WebSocket URL for browser connection
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.debug_url}/json/version") as response:
                    if response.status != 200:
                        raise CDPConnectionError(
                            f"Failed to get browser WebSocket URL: {response.status}"
                        )
                    
                    data = await response.json()
                    ws_url = data.get("webSocketDebuggerUrl")
                    
                    if not ws_url:
                        raise CDPConnectionError("WebSocket URL not found in response")
                    
                    return ws_url
        except aiohttp.ClientError as e:
            raise CDPConnectionError(f"Failed to connect to Chrome: {str(e)}")

    async def _attach_to_targets(self) -> None:
        """
        Attach to all available targets (pages).
        """
        if not self.connection:
            raise CDPConnectionError("Not connected to browser")
        
        # Get list of targets
        targets = await self.get_targets()
        
        # Attach to each page target
        for target in targets:
            target_id = target.get("targetId")
            target_type = target.get("type")
            
            if target_type == "page" and target_id:
                self.targets[target_id] = target
                
                # Create a page for this target
                page = Page(self, target_id, target)
                self.pages[target_id] = page
                
                # Attach to target
                await page.attach()

    async def get_version(self) -> Dict[str, str]:
        """
        Get Chrome version information.

        Returns:
            Dictionary with Chrome version information
        """
        if not self.connection:
            raise CDPConnectionError("Not connected to browser")
        
        return await self.connection.send_command("Browser.getVersion")

    async def get_targets(self) -> List[Dict[str, str]]:
        """
        Get list of available targets (pages).

        Returns:
            List of targets
        """
        if not self.connection:
            raise CDPConnectionError("Not connected to browser")
        
        result = await self.connection.send_command("Target.getTargets")
        return result.get("targetInfos", [])

    async def new_page(self) -> Page:
        """
        Create a new page (tab).

        Returns:
            Page object for the new page
        """
        if not self.connection:
            raise CDPConnectionError("Not connected to browser")
        
        # Create a new target (page)
        result = await self.connection.send_command(
            "Target.createTarget", {"url": "about:blank"}
        )
        
        target_id = result.get("targetId")
        if not target_id:
            raise CDPError("Failed to create new page")
        
        # Get target info
        targets = await self.get_targets()
        target = next((t for t in targets if t.get("targetId") == target_id), None)
        
        if not target:
            raise CDPError("Failed to get target info for new page")
        
        # Create a page for this target
        page = Page(self, target_id, target)
        self.pages[target_id] = page
        self.targets[target_id] = target
        
        # Attach to target
        await page.attach()
        
        return page

    async def close_page(self, target_id: str) -> None:
        """
        Close a page (tab).

        Args:
            target_id: Target ID of the page to close
        """
        if not self.connection:
            raise CDPConnectionError("Not connected to browser")
        
        if target_id in self.pages:
            page = self.pages[target_id]
            await page.detach()
            
            # Close the target
            await self.connection.send_command(
                "Target.closeTarget", {"targetId": target_id}
            )
            
            # Remove from pages and targets
            del self.pages[target_id]
            if target_id in self.targets:
                del self.targets[target_id] 