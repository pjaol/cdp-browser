"""
Connection module for CDP Browser.
Handles WebSocket connections to Chrome DevTools Protocol.
"""
import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Union

import websockets
from websockets.exceptions import ConnectionClosed

from cdp_browser.core.exceptions import CDPConnectionError

logger = logging.getLogger(__name__)


class CDPConnection:
    """
    Handles WebSocket connection to Chrome DevTools Protocol.
    """

    def __init__(self, ws_url: str):
        """
        Initialize a CDP connection.

        Args:
            ws_url: WebSocket URL for Chrome DevTools Protocol
        """
        self.ws_url = ws_url
        self.ws = None
        self.message_id = 0
        self.callbacks = {}
        self.event_listeners = {}
        self.connected = False
        self.connection_task = None

    async def connect(self) -> None:
        """
        Connect to Chrome DevTools Protocol.
        """
        try:
            self.ws = await websockets.connect(self.ws_url)
            self.connected = True
            self.connection_task = asyncio.create_task(self._listen_for_messages())
            logger.info(f"Connected to CDP at {self.ws_url}")
        except Exception as e:
            self.connected = False
            raise CDPConnectionError(f"Failed to connect to CDP: {str(e)}")

    async def disconnect(self) -> None:
        """
        Disconnect from Chrome DevTools Protocol.
        """
        if self.connection_task:
            self.connection_task.cancel()
            try:
                await self.connection_task
            except asyncio.CancelledError:
                pass
            self.connection_task = None

        if self.ws:
            await self.ws.close()
            self.ws = None
            self.connected = False
            logger.info("Disconnected from CDP")

    async def _listen_for_messages(self) -> None:
        """
        Listen for messages from Chrome DevTools Protocol.
        """
        if not self.ws:
            return

        try:
            async for message in self.ws:
                await self._process_message(message)
        except ConnectionClosed:
            logger.warning("CDP connection closed")
            self.connected = False
        except Exception as e:
            logger.error(f"Error in CDP message listener: {str(e)}")
            self.connected = False

    async def _process_message(self, message: str) -> None:
        """
        Process a message from Chrome DevTools Protocol.

        Args:
            message: Message from CDP
        """
        try:
            data = json.loads(message)
            
            # Handle method response
            if "id" in data:
                message_id = data["id"]
                if message_id in self.callbacks:
                    callback, future = self.callbacks[message_id]
                    if "result" in data:
                        future.set_result(data["result"])
                    elif "error" in data:
                        future.set_exception(
                            CDPConnectionError(f"CDP Error: {data['error']}")
                        )
                    del self.callbacks[message_id]
            
            # Handle event
            elif "method" in data:
                method = data["method"]
                params = data.get("params", {})
                if method in self.event_listeners:
                    for listener in self.event_listeners[method]:
                        try:
                            await listener(params)
                        except Exception as e:
                            logger.error(f"Error in event listener for {method}: {str(e)}")
        except json.JSONDecodeError:
            logger.error(f"Failed to parse CDP message: {message}")
        except Exception as e:
            logger.error(f"Error processing CDP message: {str(e)}")

    async def send_command(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Send a command to Chrome DevTools Protocol.

        Args:
            method: CDP method name
            params: CDP method parameters

        Returns:
            Response from CDP
        """
        if not self.ws or not self.connected:
            raise CDPConnectionError("Not connected to CDP")

        self.message_id += 1
        message_id = self.message_id
        
        message = {
            "id": message_id,
            "method": method,
        }
        
        if params:
            message["params"] = params

        future = asyncio.get_running_loop().create_future()
        self.callbacks[message_id] = (method, future)
        
        try:
            await self.ws.send(json.dumps(message))
        except Exception as e:
            del self.callbacks[message_id]
            raise CDPConnectionError(f"Failed to send CDP command: {str(e)}")
        
        try:
            return await future
        except asyncio.CancelledError:
            del self.callbacks[message_id]
            raise

    def add_event_listener(self, event: str, callback: Callable) -> None:
        """
        Add an event listener for CDP events.

        Args:
            event: CDP event name
            callback: Callback function for the event
        """
        if event not in self.event_listeners:
            self.event_listeners[event] = []
        self.event_listeners[event].append(callback)

    def remove_event_listener(self, event: str, callback: Callable) -> None:
        """
        Remove an event listener for CDP events.

        Args:
            event: CDP event name
            callback: Callback function to remove
        """
        if event in self.event_listeners and callback in self.event_listeners[event]:
            self.event_listeners[event].remove(callback)
            if not self.event_listeners[event]:
                del self.event_listeners[event] 