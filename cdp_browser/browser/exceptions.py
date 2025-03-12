"""
Exceptions for CDP Browser.
"""

class BrowserError(Exception):
    """Base exception for browser-related errors."""
    pass

class ConnectionError(BrowserError):
    """Raised when connection to Chrome fails."""
    pass

class CommandError(BrowserError):
    """Raised when a CDP command fails."""
    pass

class PageError(BrowserError):
    """Base exception for page-related errors."""
    pass

class NavigationError(PageError):
    """Raised when navigation fails."""
    pass

class TimeoutError(PageError):
    """Raised when an operation times out."""
    pass 