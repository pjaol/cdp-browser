"""
Browser module for CDP Browser.
Contains the Browser class for managing Chrome browser instances.
"""
import asyncio
import json
import logging
import os
from typing import Dict, List, Optional, Union, Callable

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

    def __init__(self, host: str = "localhost", port: int = 9223):
        """
        Initialize a Browser instance.

        Args:
            host: Chrome DevTools host
            port: Chrome DevTools port (default: 9223 for the proxy)
        """
        self.host = host
        self.port = port
        self.connection = None
        self.pages = {}
        self.targets = {}
        self.debug_url = f"http://{host}:{port}"
        self._target_created_listeners = []
        self._target_destroyed_listeners = []
        self._is_listening_for_targets = False

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
            
            # Start listening for target events
            await self._start_target_discovery()
            
            # Get list of available targets
            targets = await self.get_targets()
            
            # Create pages for each target
            for target in targets:
                target_id = target.get("id")
                target_type = target.get("type")
                
                if target_type == "page" and target_id:
                    self.targets[target_id] = target
                    
                    # Create a page for this target
                    page = Page(self, target_id, target)
                    self.pages[target_id] = page
        except Exception as e:
            raise CDPConnectionError(f"Failed to connect to browser: {str(e)}")

    async def disconnect(self) -> None:
        """
        Disconnect from Chrome DevTools Protocol.
        """
        if self.connection:
            # Stop listening for target events
            await self._stop_target_discovery()
            
            # Detach from all pages
            for target_id, page in list(self.pages.items()):
                try:
                    await page.detach()
                except Exception as e:
                    logger.warning(f"Error detaching from page {target_id}: {str(e)}")
            
            # Disconnect from browser
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

    async def _start_target_discovery(self) -> None:
        """
        Start listening for target created/destroyed events.
        """
        if not self.connection or self._is_listening_for_targets:
            return
        
        # Enable target discovery
        try:
            await self.connection.send_command("Target.setDiscoverTargets", {"discover": True})
            self._is_listening_for_targets = True
            logger.debug("Started target discovery")
        except Exception as e:
            logger.warning(f"Error enabling target discovery: {str(e)}")

    async def _stop_target_discovery(self) -> None:
        """
        Stop listening for target created/destroyed events.
        """
        if not self.connection or not self._is_listening_for_targets:
            return
        
        # Disable target discovery
        try:
            await self.connection.send_command("Target.setDiscoverTargets", {"discover": False})
        except Exception as e:
            logger.warning(f"Error disabling target discovery: {str(e)}")
        
        self._is_listening_for_targets = False
        logger.debug("Stopped target discovery")

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
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.debug_url}/json/list") as response:
                    if response.status != 200:
                        raise CDPConnectionError(
                            f"Failed to get targets: {response.status}"
                        )
                    
                    return await response.json()
        except aiohttp.ClientError as e:
            raise CDPConnectionError(f"Failed to get targets: {str(e)}")

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
        target = next((t for t in targets if t.get("id") == target_id), None)
        
        if not target:
            raise CDPError("Failed to get target info for new page")
        
        # Create a page for this target
        page = Page(self, target_id, target)
        self.pages[target_id] = page
        self.targets[target_id] = target
        
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

    async def get_page_by_url(self, url_pattern: str) -> Optional[Page]:
        """
        Find a page by URL pattern.

        Args:
            url_pattern: URL pattern to match

        Returns:
            Page object or None if not found
        """
        for page in self.pages.values():
            if url_pattern in page.url:
                return page
        return None

    async def get_page_by_title(self, title_pattern: str) -> Optional[Page]:
        """
        Find a page by title pattern.

        Args:
            title_pattern: Title pattern to match

        Returns:
            Page object or None if not found
        """
        for page in self.pages.values():
            if title_pattern in page.title:
                return page
        return None

    def add_target_created_listener(self, listener: Callable) -> None:
        """
        Add a listener for target created events.

        Args:
            listener: Callback function for the event
        """
        if listener not in self._target_created_listeners:
            self._target_created_listeners.append(listener)

    def remove_target_created_listener(self, listener: Callable) -> None:
        """
        Remove a listener for target created events.

        Args:
            listener: Callback function to remove
        """
        if listener in self._target_created_listeners:
            self._target_created_listeners.remove(listener)

    def add_target_destroyed_listener(self, listener: Callable) -> None:
        """
        Add a listener for target destroyed events.

        Args:
            listener: Callback function for the event
        """
        if listener not in self._target_destroyed_listeners:
            self._target_destroyed_listeners.append(listener)

    def remove_target_destroyed_listener(self, listener: Callable) -> None:
        """
        Remove a listener for target destroyed events.

        Args:
            listener: Callback function to remove
        """
        if listener in self._target_destroyed_listeners:
            self._target_destroyed_listeners.remove(listener)

    async def activate_page(self, target_id: str) -> None:
        """
        Activate a page (bring to front).

        Args:
            target_id: Target ID of the page to activate
        """
        if not self.connection:
            raise CDPConnectionError("Not connected to browser")
        
        if target_id not in self.pages:
            raise CDPError(f"Page not found: {target_id}")
        
        await self.connection.send_command(
            "Target.activateTarget", {"targetId": target_id}
        ) 