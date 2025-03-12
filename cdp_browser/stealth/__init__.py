"""
Stealth module for CDP browser to avoid bot detection.
"""

from .profiles import create_profile
from .patches import StealthPatches, StealthConfig

__all__ = ['create_profile', 'StealthPatches', 'StealthConfig'] 