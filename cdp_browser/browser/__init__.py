"""
Browser module for CDP Browser.
Contains classes for managing browser instances and pages.
"""
from .browser import Browser
from .page import Page
from .exceptions import NavigationError, TimeoutError

__all__ = ['Browser', 'Page', 'NavigationError', 'TimeoutError'] 