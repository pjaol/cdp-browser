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
    Supports async context manager protocol for automatic connection handling.
    """

    def __init__(self, host: str = "localhost", port: int = 9223):
        """
        Initialize a Browser instance.

        Args:
            host: Chrome DevTools host (default: localhost)
            port: Chrome DevTools port (default: 9223 for Docker setup)
        """
        self.host = host
        self.port = port
        self.connection = None
        self.pages = {}
        self.targets = {}
        self.debug_url = f"http://{host}:{port}"

    async def __aenter__(self) -> "Browser":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()

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
        except aiohttp.ClientError as e:
            raise CDPConnectionError(f"Failed to connect to Chrome: {str(e)}")
        except Exception as e:
            raise CDPConnectionError(f"Failed to connect to browser: {str(e)}")

    async def disconnect(self) -> None:
        """
        Disconnect from Chrome DevTools Protocol.
        """
        if self.connection:
            try:
                # Close all pages first
                page_ids = list(self.pages.keys())
                for target_id in page_ids:
                    try:
                        await self.close_page(target_id)
                    except Exception as e:
                        logger.warning(f"Error closing page {target_id}: {str(e)}")
                
                # Ensure all pages are detached
                for target_id in page_ids:
                    if target_id in self.pages:
                        page = self.pages[target_id]
                        try:
                            await page.detach()
                        except Exception as e:
                            logger.warning(f"Error detaching page {target_id}: {str(e)}")
                
                # Disconnect from browser
                await self.connection.disconnect()
            except Exception as e:
                logger.error(f"Error during browser disconnect: {str(e)}")
            finally:
                self.connection = None
                self.pages.clear()
                self.targets.clear()
                logger.info("Disconnected from browser")

    async def _get_browser_ws_url(self) -> str:
        """
        Get the WebSocket URL for the browser.

        Returns:
            WebSocket URL for browser connection
        
        Raises:
            CDPConnectionError: If unable to get WebSocket URL
        """
        try:
            async with aiohttp.ClientSession() as session:
                # First try /json/version endpoint
                async with session.get(f"{self.debug_url}/json/version") as response:
                    if response.status == 200:
                        data = await response.json()
                        ws_url = data.get("webSocketDebuggerUrl")
                        if ws_url:
                            # Ensure the WebSocket URL uses the correct host and port
                            if "127.0.0.1" in ws_url or "localhost" in ws_url:
                                ws_url = ws_url.replace("127.0.0.1", self.host)
                                ws_url = ws_url.replace("localhost", self.host)
                                if f":{self.port}" not in ws_url:
                                    ws_url = ws_url.replace("/devtools", f":{self.port}/devtools")
                            return ws_url
                
                # If /json/version doesn't work, try /json/list
                async with session.get(f"{self.debug_url}/json/list") as response:
                    if response.status == 200:
                        data = await response.json()
                        if isinstance(data, list) and len(data) > 0:
                            browser_target = next(
                                (t for t in data if t.get("type") == "browser"), None
                            )
                            if browser_target and browser_target.get("webSocketDebuggerUrl"):
                                ws_url = browser_target["webSocketDebuggerUrl"]
                                # Ensure the WebSocket URL uses the correct host and port
                                if "127.0.0.1" in ws_url or "localhost" in ws_url:
                                    ws_url = ws_url.replace("127.0.0.1", self.host)
                                    ws_url = ws_url.replace("localhost", self.host)
                                    if f":{self.port}" not in ws_url:
                                        ws_url = ws_url.replace("/devtools", f":{self.port}/devtools")
                                return ws_url
                
                raise CDPConnectionError(
                    f"Failed to get browser WebSocket URL from {self.debug_url}"
                )
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
            target_id = target.get("id") or target.get("targetId")
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
        try:
            # First try the CDP command if we have a connection
            if self.connection:
                try:
                    result = await self.connection.send_command("Target.getTargets")
                    if result and "targetInfos" in result:
                        return result["targetInfos"]
                except Exception as e:
                    logger.warning(f"Failed to get targets via CDP: {str(e)}")
            
            # Fallback to HTTP endpoint
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.debug_url}/json/list") as response:
                    if response.status != 200:
                        raise CDPConnectionError(
                            f"Failed to get targets: {response.status}"
                        )
                    
                    data = await response.json()
                    if not isinstance(data, list):
                        raise CDPConnectionError("Invalid response format for targets")
                    
                    # Ensure we have at least one target
                    if not data:
                        # Try to create a new target if none exist
                        async with session.put(f"{self.debug_url}/json/new") as new_response:
                            if new_response.status == 200:
                                # Retry getting targets
                                async with session.get(f"{self.debug_url}/json/list") as retry_response:
                                    if retry_response.status == 200:
                                        data = await retry_response.json()
                    
                    return data
        except aiohttp.ClientError as e:
            raise CDPConnectionError(f"Failed to get targets: {str(e)}")
        except json.JSONDecodeError as e:
            raise CDPConnectionError(f"Invalid JSON response for targets: {str(e)}")

    async def new_page(self) -> Page:
        """
        Create a new page (tab).

        Returns:
            Page object for the new page
        """
        if not self.connection:
            raise CDPConnectionError("Not connected to browser")
        
        try:
            # Create a new target (page) using PUT request
            async with aiohttp.ClientSession() as session:
                async with session.put(f"{self.debug_url}/json/new") as response:
                    if response.status != 200:
                        raise CDPError(f"Failed to create new page: {response.status}")
                    
                    target = await response.json()
                    if not isinstance(target, dict):
                        raise CDPError("Invalid response format for new page")
                    
                    target_id = target.get("id")
                    if not target_id:
                        raise CDPError("Target ID not found in response")
                    
                    # Create a page for this target
                    page = Page(self, target_id, target)
                    self.pages[target_id] = page
                    self.targets[target_id] = target
                    
                    # Attach to target
                    await page.attach()
                    
                    return page
        except aiohttp.ClientError as e:
            raise CDPError(f"Failed to create new page: {str(e)}")
        except json.JSONDecodeError as e:
            raise CDPError(f"Invalid JSON response for new page: {str(e)}")

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
            
            try:
                # Close the target using HTTP endpoint
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.debug_url}/json/close/{target_id}") as response:
                        if response.status != 200:
                            logger.warning(f"Failed to close target {target_id}: {response.status}")
            except Exception as e:
                logger.warning(f"Error closing target {target_id}: {str(e)}")
            finally:
                # Remove from pages and targets
                del self.pages[target_id]
                if target_id in self.targets:
                    del self.targets[target_id] 