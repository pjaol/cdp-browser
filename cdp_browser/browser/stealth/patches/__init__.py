"""
Stealth patches for CDP Browser.

This module contains various patches that can be applied to a browser page
to avoid detection by fingerprinting and bot detection systems.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# Dictionary of available patches
PATCHES: Dict[str, Dict[str, Any]] = {}

def register_patch(name: str, script: str, description: str = "", priority: int = 100):
    """
    Register a stealth patch.
    
    Args:
        name: Unique name for the patch
        script: JavaScript code to execute
        description: Description of what the patch does
        priority: Execution priority (lower numbers execute first)
    """
    PATCHES[name] = {
        "script": script,
        "description": description,
        "priority": priority
    }

# Import all patches to register them
from .webdriver import *
from .user_agent import *
from .chrome_runtime import *
from .plugins import *
from .worker import *
from .iframe import *
from .canvas import *
from .webgl import *

def get_patches(level: str = "balanced") -> Dict[str, Dict[str, Any]]:
    """
    Get all patches for a specific stealth level.
    
    Args:
        level: Stealth level ("minimum", "balanced", or "maximum")
        
    Returns:
        Dictionary of patches to apply
    """
    # Filter patches based on level
    if level == "minimum":
        # Only include essential patches
        return {k: v for k, v in PATCHES.items() 
                if k in ["webdriver_basic", "chrome_runtime_basic", "user_agent_basic"]}
    elif level == "balanced":
        # Include all except experimental patches
        return {k: v for k, v in PATCHES.items() 
                if not k.startswith("experimental_")}
    elif level == "maximum":
        # Include all patches
        return PATCHES
    else:
        logger.warning(f"Unknown stealth level: {level}, using balanced")
        return get_patches("balanced")

def get_ordered_patches(level: str = "balanced") -> list:
    """
    Get patches ordered by priority.
    
    Args:
        level: Stealth level ("minimum", "balanced", or "maximum")
        
    Returns:
        List of patches ordered by priority
    """
    patches = get_patches(level)
    return sorted(
        [(name, patch) for name, patch in patches.items()],
        key=lambda x: x[1]["priority"]
    ) 