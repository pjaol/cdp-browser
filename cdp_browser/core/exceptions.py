"""
Exceptions module for CDP Browser.
Contains custom exceptions for CDP-related errors.
"""


class CDPError(Exception):
    """Base exception for all CDP-related errors."""
    pass


class CDPConnectionError(CDPError):
    """Exception raised for CDP connection errors."""
    pass


class CDPTimeoutError(CDPError):
    """Exception raised for CDP timeout errors."""
    pass


class CDPProtocolError(CDPError):
    """Exception raised for CDP protocol errors."""
    pass


class CDPRuntimeError(CDPError):
    """Exception raised for CDP runtime errors."""
    pass 