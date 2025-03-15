"""
Stealth patches for CDP Browser.

This module contains various patches that can be applied to a browser page
to avoid detection by fingerprinting and bot detection systems.
"""

from typing import Dict, Any, List, Set
import logging

logger = logging.getLogger(__name__)

# Dictionary of available patches
PATCHES: Dict[str, Dict[str, Any]] = {}

def register_patch(name: str, script: str, description: str = "", priority: int = 100, dependencies: List[str] = None):
    """
    Register a stealth patch.
    
    Args:
        name: Unique name for the patch
        script: JavaScript code to execute
        description: Description of what the patch does
        priority: Execution priority (lower numbers execute first)
        dependencies: List of patch names that must be applied before this one
    """
    logger.debug(f"Registering patch: {name} (priority: {priority}, dependencies: {dependencies})")
    PATCHES[name] = {
        "script": script,
        "description": description,
        "priority": priority,
        "dependencies": dependencies or []
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
from .cloudflare_turnstile import *

logger.debug(f"Available patches: {list(PATCHES.keys())}")

def get_patches(level: str = "balanced") -> Dict[str, Dict[str, Any]]:
    """
    Get all patches for a specific stealth level.
    
    Args:
        level: Stealth level ("minimum", "balanced", or "maximum")
        
    Returns:
        Dictionary of patches to apply
    """
    logger.debug(f"Getting patches for level: {level}")
    # Filter patches based on level
    if level == "minimum":
        # Only include essential patches
        patches = {k: v for k, v in PATCHES.items() 
                if k in ["webdriver_basic", "chrome_runtime_basic", "user_agent_basic"]}
    elif level == "balanced":
        # Include all except experimental patches
        patches = {k: v for k, v in PATCHES.items() 
                if not k.startswith("experimental_")}
    elif level == "maximum":
        # Include all patches
        patches = PATCHES
    else:
        logger.warning(f"Unknown stealth level: {level}, using balanced")
        return get_patches("balanced")
    
    logger.debug(f"Selected patches for {level}: {list(patches.keys())}")
    return patches

def _resolve_dependencies(patches: Dict[str, Dict[str, Any]], name: str, resolved: Set[str], processing: Set[str]) -> List[str]:
    """
    Resolve patch dependencies using topological sort.
    
    Args:
        patches: Dictionary of patches
        name: Name of the patch to resolve
        resolved: Set of already resolved patches
        processing: Set of patches currently being processed (for cycle detection)
        
    Returns:
        List of patch names in dependency order
    """
    logger.debug(f"Resolving dependencies for {name} (resolved: {resolved}, processing: {processing})")
    if name in resolved:
        logger.debug(f"Patch {name} already resolved")
        return []
    if name in processing:
        raise ValueError(f"Circular dependency detected for patch {name}")
    
    processing.add(name)
    result = []
    
    # Process dependencies first
    for dep in patches[name].get("dependencies", []):
        if dep not in patches:
            logger.warning(f"Missing dependency {dep} for patch {name}")
            continue
        logger.debug(f"Processing dependency {dep} for {name}")
        result.extend(_resolve_dependencies(patches, dep, resolved, processing))
    
    result.append(name)
    processing.remove(name)
    resolved.add(name)
    logger.debug(f"Resolved dependencies for {name}: {result}")
    return result

def get_ordered_patches(level: str = "balanced") -> list:
    """
    Get patches ordered by priority and dependencies.
    
    Args:
        level: Stealth level ("minimum", "balanced", or "maximum")
        
    Returns:
        List of patches ordered by priority and dependencies
    """
    logger.debug(f"Getting ordered patches for level: {level}")
    patches = get_patches(level)
    
    # First, sort by priority
    priority_sorted = sorted(
        [(name, patch) for name, patch in patches.items()],
        key=lambda x: x[1]["priority"]
    )
    logger.debug(f"Priority sorted patches: {[name for name, _ in priority_sorted]}")
    
    # Then, resolve dependencies
    resolved = set()
    ordered = []
    
    for name, _ in priority_sorted:
        if name not in resolved:
            try:
                logger.debug(f"Resolving dependencies starting with {name}")
                ordered.extend(_resolve_dependencies(patches, name, resolved, set()))
            except ValueError as e:
                logger.error(f"Error resolving dependencies: {e}")
                continue
    
    # Return only patches that exist and maintain their original data
    result = [(name, patches[name]) for name in ordered if name in patches]
    logger.debug(f"Final ordered patches: {[name for name, _ in result]}")
    return result 