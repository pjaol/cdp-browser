"""
Connection module for CDP Browser.
Handles WebSocket connections to Chrome DevTools Protocol.
"""
import asyncio
import contextlib
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Union, Set, Awaitable

import websockets
from websockets.exceptions import ConnectionClosed

from cdp_browser.core.exceptions import CDPConnectionError

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def preserve_loop_state():
    """
    Context manager to preserve event loop state during cleanup.
    """
    loop = asyncio.get_running_loop()
    is_closed = loop.is_closed()
    try:
        yield
    finally:
        if not is_closed and loop.is_closed():
            logger.debug("Event loop was closed during operation")


class CDPConnection:
    """
    Manages a WebSocket connection to Chrome DevTools Protocol.
    """

    def __init__(self, ws_url: str):
        """
        Initialize a CDP connection.

        Args:
            ws_url: WebSocket URL for CDP
        """
        self.ws_url = ws_url
        self.ws = None
        self.connected = False
        self._closing = False
        self.message_id = 0
        self.callbacks = {}
        self._event_listeners = {}
        self._message_queue = asyncio.Queue()

    async def connect(self) -> None:
        """
        Connect to Chrome DevTools Protocol.
        """
        if self.connected:
            return

        try:
            self.ws = await websockets.connect(self.ws_url)
            self.connected = True
            self._closing = False

            # Start listening for messages
            asyncio.create_task(self._listen_for_messages())

        except Exception as e:
            self.ws = None
            self.connected = False
            raise CDPConnectionError(f"Failed to connect to CDP: {str(e)}")

    async def disconnect(self) -> None:
        """
        Disconnect from Chrome DevTools Protocol.
        """
        if not self.connected:
            return

        self._closing = True

        try:
            if self.ws:
                await self.ws.close()
        except Exception as e:
            logger.warning(f"Error closing WebSocket: {str(e)}")
        finally:
            self.ws = None
            self.connected = False
            self.callbacks.clear()

    async def _listen_for_messages(self) -> None:
        """
        Listen for messages from CDP and handle them.
        """
        if not self.ws:
            return

        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    
                    # Put the message in the queue for receive_message
                    await self._message_queue.put(data)
                    
                    # Handle message
                    message_id = data.get("id")
                    if message_id in self.callbacks:
                        method, future = self.callbacks[message_id]
                        
                        if "error" in data:
                            future.set_exception(
                                CDPConnectionError(f"CDP Error: {data['error']}")
                            )
                        else:
                            future.set_result(data.get("result"))
                            
                        del self.callbacks[message_id]
                    
                    # Handle events
                    elif "method" in data:
                        method = data["method"]
                        if method in self._event_listeners:
                            for listener in self._event_listeners[method]:
                                try:
                                    await listener(data.get("params", {}))
                                except Exception as e:
                                    logger.error(
                                        f"Error in event listener for {method}: {str(e)}"
                                    )

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message: {str(e)}")
                except Exception as e:
                    logger.error(f"Error handling message: {str(e)}")

        except websockets.exceptions.ConnectionClosed:
            if not self._closing:
                logger.warning("WebSocket connection closed unexpectedly")
        except Exception as e:
            if not self._closing:
                logger.error(f"Error in message listener: {str(e)}")

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

        if self._closing:
            raise CDPConnectionError("Connection is closing")

        self.message_id += 1
        message_id = self.message_id

        message = {
            "id": message_id,
            "method": method,
        }

        if params:
            message["params"] = params

        try:
            loop = asyncio.get_running_loop()
            if loop.is_closed():
                raise CDPConnectionError("Event loop is closed")

            future = loop.create_future()
            self.callbacks[message_id] = (method, future)

            await self.ws.send(json.dumps(message))

            return await future
        except asyncio.CancelledError:
            if message_id in self.callbacks:
                del self.callbacks[message_id]
            raise
        except Exception as e:
            if message_id in self.callbacks:
                del self.callbacks[message_id]
            raise CDPConnectionError(f"Error in CDP command {method}: {str(e)}")

    def add_event_listener(
        self, event: str, callback: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """
        Add an event listener for CDP events.

        Args:
            event: CDP event name
            callback: Async callback function
        """
        if event not in self._event_listeners:
            self._event_listeners[event] = set()
        self._event_listeners[event].add(callback)

    def remove_event_listener(
        self, event: str, callback: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """
        Remove an event listener.

        Args:
            event: CDP event name
            callback: Callback function to remove
        """
        if event in self._event_listeners:
            self._event_listeners[event].discard(callback)
            if not self._event_listeners[event]:
                del self._event_listeners[event]

    async def receive_message(self) -> Optional[Dict[str, Any]]:
        """
        Receive the next message from CDP.

        Returns:
            Message data as a dictionary, or None if the connection is closed
        """
        if not self.ws or not self.connected:
            return None

        try:
            return await self._message_queue.get()
        except Exception as e:
            logger.error(f"Error receiving message: {str(e)}")
            return None

    def _create_task(self, coro) -> asyncio.Task:
        """
        Create a task and add it to pending tasks set.
        
        Args:
            coro: Coroutine to create task from
            
        Returns:
            Created task
        """
        task = asyncio.create_task(coro)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)
        return task

    async def _cancel_pending_tasks(self) -> None:
        """
        Cancel all pending tasks and wait for them to complete.
        """
        if not self._pending_tasks:
            return

        # Cancel all pending tasks
        for task in self._pending_tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete with timeout
        pending = list(self._pending_tasks)
        try:
            async with preserve_loop_state():
                done, pending = await asyncio.wait(
                    pending,
                    timeout=0.5,  # Short timeout to minimize wait time
                    return_when=asyncio.ALL_COMPLETED
                )
                # Log any tasks that didn't complete
                if pending:
                    logger.warning(
                        f"{len(pending)} tasks did not complete within timeout"
                    )
        except asyncio.CancelledError:
            logger.debug("Task cancellation interrupted")
        finally:
            self._pending_tasks.clear()

    async def _close_websocket(self) -> None:
        """
        Close the WebSocket connection gracefully.
        """
        if not self.ws:
            return

        try:
            # Cancel message listener first
            if self._message_listener_task and not self._message_listener_task.done():
                self._message_listener_task.cancel()
                try:
                    async with preserve_loop_state():
                        await asyncio.wait_for(self._message_listener_task, timeout=0.2)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass

            # Try graceful closure with short timeout
            try:
                async with preserve_loop_state():
                    await asyncio.wait_for(self.ws.close(), timeout=0.2)
            except (asyncio.TimeoutError, ConnectionClosed):
                pass
            except Exception as e:
                logger.warning(f"Error during WebSocket close: {str(e)}")
        finally:
            self.ws = None
            self._message_listener_task = None

    async def _process_message(self, message: str) -> None:
        """
        Process a message from Chrome DevTools Protocol.

        Args:
            message: Message from CDP
        """
        if self._closing:
            return

        try:
            data = json.loads(message)
            
            # Handle method response
            if "id" in data:
                message_id = data["id"]
                if message_id in self.callbacks:
                    callback, future = self.callbacks[message_id]
                    if "result" in data:
                        if not future.done():
                            future.set_result(data["result"])
                    elif "error" in data:
                        if not future.done():
                            future.set_exception(
                                CDPConnectionError(f"CDP Error: {data['error']}")
                            )
                    del self.callbacks[message_id]
            
            # Handle event
            elif "method" in data:
                method = data["method"]
                params = data.get("params", {})
                if method in self._event_listeners:
                    for listener in self._event_listeners[method]:
                        try:
                            await listener(params)
                        except Exception as e:
                            logger.error(f"Error in event listener for {method}: {str(e)}")
        except json.JSONDecodeError:
            logger.error(f"Failed to parse CDP message: {message}")
        except Exception as e:
            logger.error(f"Error processing CDP message: {str(e)}") 