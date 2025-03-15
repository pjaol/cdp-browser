"""
Base class for stealth patches.

This module provides a base class for creating stealth patches that can be applied to pages.
"""

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BasePatch(ABC):
    """Base class for stealth patches."""

    NAME = "base_patch"
    DESCRIPTION = "Base class for stealth patches"
    PRIORITY = 100  # Default priority

    def __init__(self):
        """Initialize the patch."""
        pass

    @abstractmethod
    async def apply(self, browser, page):
        """
        Apply the patch to the page.
        
        Args:
            browser: The browser instance
            page: The page to apply the patch to
            
        Returns:
            bool: True if the patch was applied successfully, False otherwise
        """
        pass
    
    def get_script(self):
        """
        Get the JavaScript to be executed for this patch.
        
        This method is used to make class-based patches compatible with
        the existing script-based patch system.
        
        Returns:
            str: The JavaScript code to execute
        """
        # This is a stub that should be overridden if needed
        return "// No script for this patch" 