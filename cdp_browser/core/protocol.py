"""
Protocol module for CDP Browser.
Contains functions for handling CDP protocol messages.
"""
import json
import logging
from typing import Any, Dict, List, Optional, Union

from cdp_browser.core.exceptions import CDPProtocolError

logger = logging.getLogger(__name__)


class CDPProtocol:
    """
    Handles CDP protocol messages.
    """

    @staticmethod
    def parse_ws_url(debug_url: str) -> str:
        """
        Parse WebSocket URL from Chrome debug URL.

        Args:
            debug_url: Chrome debug URL (e.g., http://localhost:9222/json/version)

        Returns:
            WebSocket URL for CDP connection
        """
        if debug_url.startswith("ws://") or debug_url.startswith("wss://"):
            return debug_url
        
        if not debug_url.startswith("http"):
            debug_url = f"http://{debug_url}"
        
        return debug_url.replace("http://", "ws://").replace("https://", "wss://")

    @staticmethod
    def format_command(method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Format a CDP command.

        Args:
            method: CDP method name
            params: CDP method parameters

        Returns:
            Formatted CDP command
        """
        command = {"method": method}
        if params:
            command["params"] = params
        return command

    @staticmethod
    def parse_response(response: Dict[str, Any]) -> Any:
        """
        Parse a CDP response.

        Args:
            response: CDP response

        Returns:
            Parsed response data

        Raises:
            CDPProtocolError: If the response contains an error
        """
        if "error" in response:
            error = response["error"]
            message = error.get("message", "Unknown CDP error")
            code = error.get("code", -1)
            raise CDPProtocolError(f"CDP Error {code}: {message}")
        
        return response.get("result")

    @staticmethod
    def format_event_name(domain: str, event: str) -> str:
        """
        Format a CDP event name.

        Args:
            domain: CDP domain (e.g., Page, Network)
            event: CDP event (e.g., loadEventFired)

        Returns:
            Formatted event name (e.g., Page.loadEventFired)
        """
        return f"{domain}.{event}" 