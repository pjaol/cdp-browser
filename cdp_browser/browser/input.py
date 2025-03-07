"""
Input module for CDP Browser.
Contains functions for simulating user input.
"""
import asyncio
import logging
import random
import string
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
        self._modifiers = 0
        self._keyboard_map = self._init_keyboard_map()

    def _init_keyboard_map(self) -> Dict[str, Dict[str, Union[int, str]]]:
        """
        Initialize keyboard mapping for special keys.

        Returns:
            Dictionary mapping key names to key codes
        """
        # Map of special keys to their key codes and text values
        return {
            "Enter": {"keyCode": 13, "key": "Enter", "code": "Enter"},
            "Tab": {"keyCode": 9, "key": "Tab", "code": "Tab"},
            "Escape": {"keyCode": 27, "key": "Escape", "code": "Escape"},
            "Backspace": {"keyCode": 8, "key": "Backspace", "code": "Backspace"},
            "Delete": {"keyCode": 46, "key": "Delete", "code": "Delete"},
            "ArrowUp": {"keyCode": 38, "key": "ArrowUp", "code": "ArrowUp"},
            "ArrowDown": {"keyCode": 40, "key": "ArrowDown", "code": "ArrowDown"},
            "ArrowLeft": {"keyCode": 37, "key": "ArrowLeft", "code": "ArrowLeft"},
            "ArrowRight": {"keyCode": 39, "key": "ArrowRight", "code": "ArrowRight"},
            "Home": {"keyCode": 36, "key": "Home", "code": "Home"},
            "End": {"keyCode": 35, "key": "End", "code": "End"},
            "PageUp": {"keyCode": 33, "key": "PageUp", "code": "PageUp"},
            "PageDown": {"keyCode": 34, "key": "PageDown", "code": "PageDown"},
            "Control": {"keyCode": 17, "key": "Control", "code": "ControlLeft"},
            "Shift": {"keyCode": 16, "key": "Shift", "code": "ShiftLeft"},
            "Alt": {"keyCode": 18, "key": "Alt", "code": "AltLeft"},
            "Meta": {"keyCode": 91, "key": "Meta", "code": "MetaLeft"},
        }

    async def click(
        self, 
        selector: str, 
        button: str = "left", 
        click_count: int = 1,
        delay: int = 0,
        force: bool = False
    ) -> None:
        """
        Click on an element.

        Args:
            selector: CSS selector for the element
            button: Mouse button (left, middle, right)
            click_count: Number of clicks
            delay: Delay between mouseDown and mouseUp in milliseconds
            force: Whether to click even if the element is not visible
        """
        if not self.page.attached:
            raise CDPError("Not attached to page")
        
        # Wait for element to be available if not forcing
        if not force:
            element_found = await self.page.wait_for_selector(selector, visible=True)
            if not element_found:
                raise CDPError(f"Element not found or not visible: {selector}")
        
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
        
        # Add delay between mouseDown and mouseUp if specified
        if delay > 0:
            await asyncio.sleep(delay / 1000)
        
        await self._mouse_event("mouseReleased", x, y, button_type, click_count)

    async def double_click(self, selector: str, button: str = "left") -> None:
        """
        Double-click on an element.

        Args:
            selector: CSS selector for the element
            button: Mouse button (left, middle, right)
        """
        await self.click(selector, button, click_count=2)

    async def hover(self, selector: str) -> None:
        """
        Hover over an element.

        Args:
            selector: CSS selector for the element
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
        
        # Calculate hover position (center of the element)
        x, y = self._calculate_click_position(box_model)
        
        # Simulate mouse move event
        await self._mouse_event("mouseMoved", x, y, "none", 0)

    async def type(
        self, 
        selector: str, 
        text: str, 
        delay: int = 50,
        clear: bool = False
    ) -> None:
        """
        Type text into an element.

        Args:
            selector: CSS selector for the element
            text: Text to type
            delay: Delay between keystrokes in milliseconds
            clear: Whether to clear the input field before typing
        """
        if not self.page.attached:
            raise CDPError("Not attached to page")
        
        # Focus on the element
        await self.click(selector)
        
        # Clear the input field if requested
        if clear:
            await self.page.evaluate(f"""
            (function() {{
                const el = document.querySelector('{selector}');
                if (el) {{
                    el.value = '';
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }})()
            """)
        
        # Type each character with delay
        for char in text:
            # Handle special keys
            if char in self._keyboard_map:
                key_info = self._keyboard_map[char]
                await self._key_event("keyDown", key_info["key"], key_code=key_info["keyCode"], code=key_info["code"])
                await self._key_event("keyUp", key_info["key"], key_code=key_info["keyCode"], code=key_info["code"])
            else:
                # Send keyDown event
                await self._key_event("keyDown", char)
                
                # Send keyUp event
                await self._key_event("keyUp", char)
            
            # Add delay between keystrokes
            if delay > 0:
                await asyncio.sleep(delay / 1000)

    async def press(self, key: str) -> None:
        """
        Press a single key.

        Args:
            key: Key to press (e.g., 'Enter', 'Tab', 'a', etc.)
        """
        if not self.page.attached:
            raise CDPError("Not attached to page")
        
        # Handle special keys
        if key in self._keyboard_map:
            key_info = self._keyboard_map[key]
            await self._key_event("keyDown", key_info["key"], key_code=key_info["keyCode"], code=key_info["code"])
            await self._key_event("keyUp", key_info["key"], key_code=key_info["keyCode"], code=key_info["code"])
        else:
            # Send keyDown event
            await self._key_event("keyDown", key)
            
            # Send keyUp event
            await self._key_event("keyUp", key)

    async def press_key_combination(self, keys: List[str]) -> None:
        """
        Press a combination of keys (e.g., Ctrl+C).

        Args:
            keys: List of keys to press simultaneously
        """
        if not self.page.attached:
            raise CDPError("Not attached to page")
        
        # Press all keys down
        for key in keys:
            if key in self._keyboard_map:
                key_info = self._keyboard_map[key]
                await self._key_event("keyDown", key_info["key"], key_code=key_info["keyCode"], code=key_info["code"])
            else:
                await self._key_event("keyDown", key)
        
        # Release all keys in reverse order
        for key in reversed(keys):
            if key in self._keyboard_map:
                key_info = self._keyboard_map[key]
                await self._key_event("keyUp", key_info["key"], key_code=key_info["keyCode"], code=key_info["code"])
            else:
                await self._key_event("keyUp", key)

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

    async def check(self, selector: str, check: bool = True) -> None:
        """
        Check or uncheck a checkbox.

        Args:
            selector: CSS selector for the checkbox
            check: Whether to check (True) or uncheck (False)
        """
        if not self.page.attached:
            raise CDPError("Not attached to page")
        
        # Use JavaScript to check/uncheck
        script = f"""
        (function() {{
            const checkbox = document.querySelector('{selector}');
            if (!checkbox || checkbox.type !== 'checkbox') return false;
            
            if (checkbox.checked !== {str(check).lower()}) {{
                checkbox.checked = {str(check).lower()};
                checkbox.dispatchEvent(new Event('input', {{ bubbles: true }}));
                checkbox.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
            
            return true;
        }})()
        """
        
        result = await self.page.evaluate(script)
        success = result.get("result", {}).get("value", False)
        
        if not success:
            raise CDPError(f"Failed to {'check' if check else 'uncheck'} checkbox: {selector}")

    async def fill_form(self, form_data: Dict[str, str], submit: bool = False, submit_selector: Optional[str] = None) -> None:
        """
        Fill a form with data.

        Args:
            form_data: Dictionary mapping selectors to values
            submit: Whether to submit the form after filling
            submit_selector: CSS selector for the submit button (if submit is True)
        """
        if not self.page.attached:
            raise CDPError("Not attached to page")
        
        # Fill each field
        for selector, value in form_data.items():
            # Determine field type
            field_type = await self.page.evaluate(f"""
            (function() {{
                const el = document.querySelector('{selector}');
                if (!el) return 'not-found';
                if (el.tagName === 'SELECT') return 'select';
                if (el.tagName === 'TEXTAREA') return 'textarea';
                if (el.tagName === 'INPUT') {{
                    return el.type || 'text';
                }}
                return 'other';
            }})()
            """)
            
            field_type = field_type.get("result", {}).get("value", "not-found")
            
            # Handle different field types
            if field_type == 'not-found':
                raise CDPError(f"Form field not found: {selector}")
            elif field_type == 'select':
                await self.select(selector, [value])
            elif field_type == 'checkbox':
                await self.check(selector, value.lower() in ('true', 'yes', '1', 'on'))
            elif field_type == 'radio':
                await self.click(selector)
            else:
                # Text input or textarea
                await self.type(selector, value, clear=True)
        
        # Submit the form if requested
        if submit:
            if submit_selector:
                await self.click(submit_selector)
            else:
                # Try to find a submit button or input
                script = """
                (function() {
                    // Try to find submit button
                    const submitBtn = document.querySelector('button[type="submit"], input[type="submit"]');
                    if (submitBtn) {
                        submitBtn.click();
                        return true;
                    }
                    
                    // Try to submit the form directly
                    const form = document.querySelector('form');
                    if (form) {
                        form.submit();
                        return true;
                    }
                    
                    return false;
                })()
                """
                
                result = await self.page.evaluate(script)
                success = result.get("result", {}).get("value", False)
                
                if not success:
                    raise CDPError("Failed to submit form: no submit button found")

    async def upload_file(self, selector: str, file_paths: List[str]) -> None:
        """
        Upload files to a file input.

        Args:
            selector: CSS selector for the file input
            file_paths: List of file paths to upload
        """
        if not self.page.attached:
            raise CDPError("Not attached to page")
        
        # Get node ID for the file input
        node_id = await self._get_node_id(selector)
        if not node_id:
            raise CDPError(f"File input not found: {selector}")
        
        # Set files to upload
        await self.page._send_command(
            "DOM.setFileInputFiles",
            {
                "nodeId": node_id,
                "files": file_paths
            }
        )

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
                "modifiers": self._modifiers
            },
        )

    async def _key_event(
        self, 
        type: str, 
        key: str, 
        text: Optional[str] = None, 
        key_code: int = 0, 
        code: Optional[str] = None
    ) -> None:
        """
        Send a keyboard event.

        Args:
            type: Event type (keyDown, keyUp)
            key: Key to press
            text: Text to input (defaults to key)
            key_code: Key code (ASCII code for single characters)
            code: Physical key code
        """
        # Get key code and modifiers
        if text is None:
            text = key if len(key) == 1 else ""
        
        if key_code == 0 and len(key) == 1:
            key_code = ord(key)
        
        if code is None:
            if len(key) == 1 and key.isalpha():
                code = f"Key{key.upper()}"
            elif len(key) == 1 and key.isdigit():
                code = f"Digit{key}"
            else:
                code = key
        
        # Update modifiers
        if type == "keyDown":
            if key == "Control" or key == "ControlLeft" or key == "ControlRight":
                self._modifiers |= 2  # Ctrl
            elif key == "Shift" or key == "ShiftLeft" or key == "ShiftRight":
                self._modifiers |= 8  # Shift
            elif key == "Alt" or key == "AltLeft" or key == "AltRight":
                self._modifiers |= 1  # Alt
            elif key == "Meta" or key == "MetaLeft" or key == "MetaRight":
                self._modifiers |= 4  # Meta/Command
        elif type == "keyUp":
            if key == "Control" or key == "ControlLeft" or key == "ControlRight":
                self._modifiers &= ~2  # Ctrl
            elif key == "Shift" or key == "ShiftLeft" or key == "ShiftRight":
                self._modifiers &= ~8  # Shift
            elif key == "Alt" or key == "AltLeft" or key == "AltRight":
                self._modifiers &= ~1  # Alt
            elif key == "Meta" or key == "MetaLeft" or key == "MetaRight":
                self._modifiers &= ~4  # Meta/Command
        
        await self.page._send_command(
            "Input.dispatchKeyEvent",
            {
                "type": type,
                "text": text,
                "key": key,
                "code": code,
                "keyCode": key_code,
                "location": 0,
                "modifiers": self._modifiers
            },
        ) 