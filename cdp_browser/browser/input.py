"""
Input module for CDP Browser.
Contains functions for simulating user input.
"""
import asyncio
import logging
import random
from typing import Dict, List, Optional, Tuple, Union

from cdp_browser.core.exceptions import CDPError

logger = logging.getLogger(__name__)


class Input:
    """
    Simulates user input via CDP.
    """

    def __init__(self, page):
        """
        Initialize an Input instance.

        Args:
            page: Page instance
        """
        self.page = page

    async def click(self, selector: str, button: str = "left", click_count: int = 1) -> None:
        """
        Click on an element.

        Args:
            selector: CSS selector for the element
            button: Mouse button (left, middle, right)
            click_count: Number of clicks
        """
        if not self.page.attached:
            raise CDPError("Not attached to page")
        
        # Get element node ID
        node_id = await self._get_node_id(selector)
        if not node_id:
            raise CDPError(f"Element not found: {selector}")
        
        # Get element box model
        box_model = await self._get_box_model(node_id)
        if not box_model:
            raise CDPError(f"Failed to get box model for element: {selector}")
        
        # Calculate click position (center of the element)
        x, y = self._calculate_click_position(box_model)
        
        # Map button string to CDP button enum
        button_map = {"left": "left", "middle": "middle", "right": "right"}
        button_type = button_map.get(button.lower(), "left")
        
        # Simulate mouse events
        await self._mouse_event("mousePressed", x, y, button_type, click_count)
        await self._mouse_event("mouseReleased", x, y, button_type, click_count)

    async def type(self, selector: str, text: str, delay: int = 50) -> None:
        """
        Type text into an element.

        Args:
            selector: CSS selector for the element
            text: Text to type
            delay: Delay between keystrokes in milliseconds
        """
        if not self.page.attached:
            raise CDPError("Not attached to page")
        
        # Focus on the element
        await self.click(selector)
        
        # Type each character with delay
        for char in text:
            # Send keyDown event
            await self._key_event("keyDown", char)
            
            # Send keyUp event
            await self._key_event("keyUp", char)
            
            # Add delay between keystrokes
            if delay > 0:
                await asyncio.sleep(delay / 1000)

    async def select(self, selector: str, values: List[str]) -> None:
        """
        Select options in a <select> element.

        Args:
            selector: CSS selector for the select element
            values: Values to select
        """
        if not self.page.attached:
            raise CDPError("Not attached to page")
        
        # Use JavaScript to select options
        script = f"""
        (function() {{
            const select = document.querySelector('{selector}');
            if (!select) return false;
            
            select.value = undefined;
            const options = Array.from(select.options);
            
            const values = {values};
            for (const option of options) {{
                option.selected = values.includes(option.value);
            }}
            
            select.dispatchEvent(new Event('input', {{ bubbles: true }}));
            select.dispatchEvent(new Event('change', {{ bubbles: true }}));
            
            return true;
        }})()
        """
        
        result = await self.page.evaluate(script)
        success = result.get("result", {}).get("value", False)
        
        if not success:
            raise CDPError(f"Failed to select options in element: {selector}")

    async def _get_node_id(self, selector: str) -> Optional[int]:
        """
        Get node ID for an element.

        Args:
            selector: CSS selector for the element

        Returns:
            Node ID or None if not found
        """
        # Use DOM.querySelector to find the element
        result = await self.page._send_command(
            "DOM.querySelector",
            {"nodeId": 1, "selector": selector},
        )
        
        return result.get("nodeId")

    async def _get_box_model(self, node_id: int) -> Optional[Dict]:
        """
        Get box model for an element.

        Args:
            node_id: Node ID of the element

        Returns:
            Box model or None if not available
        """
        result = await self.page._send_command(
            "DOM.getBoxModel",
            {"nodeId": node_id},
        )
        
        return result.get("model")

    def _calculate_click_position(self, box_model: Dict) -> Tuple[float, float]:
        """
        Calculate click position (center of the element).

        Args:
            box_model: Box model of the element

        Returns:
            (x, y) coordinates
        """
        # Get content box
        content = box_model.get("content", [])
        
        # Calculate center point
        x1, y1 = content[0], content[1]
        x2, y2 = content[2], content[3]
        
        x = (x1 + x2) / 2
        y = (y1 + y2) / 2
        
        return x, y

    async def _mouse_event(
        self, type: str, x: float, y: float, button: str, click_count: int
    ) -> None:
        """
        Send a mouse event.

        Args:
            type: Event type (mousePressed, mouseReleased, mouseMoved)
            x: X coordinate
            y: Y coordinate
            button: Mouse button (left, middle, right)
            click_count: Number of clicks
        """
        await self.page._send_command(
            "Input.dispatchMouseEvent",
            {
                "type": type,
                "x": x,
                "y": y,
                "button": button,
                "clickCount": click_count,
            },
        )

    async def _key_event(self, type: str, key: str) -> None:
        """
        Send a keyboard event.

        Args:
            type: Event type (keyDown, keyUp)
            key: Key to press
        """
        # Get key code and modifiers
        text = key
        key_code = ord(key) if len(key) == 1 else 0
        
        await self.page._send_command(
            "Input.dispatchKeyEvent",
            {
                "type": type,
                "text": text,
                "key": key,
                "code": key,
                "keyCode": key_code,
                "location": 0,
            },
        ) 