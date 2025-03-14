from typing import Callable, Dict

class StealthBrowser:
    def on(self, event: str, callback: Callable) -> None:
        """Register an event handler.
        
        Args:
            event: The event to listen for.
            callback: The callback to call when the event occurs.
        """
        if not hasattr(self, '_event_handlers'):
            self._event_handlers = {}
        
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        
        self._event_handlers[event].append(callback)

    def remove_listener(self, event: str, callback: Callable) -> None:
        """Remove an event handler.
        
        Args:
            event: The event to remove the handler from.
            callback: The callback to remove.
        """
        if not hasattr(self, '_event_handlers'):
            return
        
        if event in self._event_handlers:
            try:
                self._event_handlers[event].remove(callback)
            except ValueError:
                pass

    async def _handle_message(self, message: Dict) -> None:
        """Handle a message from the browser.
        
        Args:
            message: The message to handle.
        """
        if not hasattr(self, '_event_handlers'):
            self._event_handlers = {}
        
        # Handle command responses
        if 'id' in message:
            command_id = message['id']
            if command_id in self._command_futures:
                future = self._command_futures.pop(command_id)
                if not future.done():
                    future.set_result(message)
        
        # Handle events
        if 'method' in message:
            method = message['method']
            params = message.get('params', {})
            
            if method in self._event_handlers:
                for handler in self._event_handlers[method]:
                    try:
                        await handler(params)
                    except Exception as e:
                        logger.error(f"Error in event handler for {method}: {str(e)}") 