"""
Stealth profiles for CDP browser to manage different stealth configurations.
"""

from typing import Dict, Any
from .patches import StealthPatches, StealthConfig

class StealthProfile:
    """Base class for stealth profiles."""
    
    def __init__(self):
        self.patches = StealthPatches()
        self.config = StealthConfig()
    
    def get_launch_flags(self) -> list[str]:
        """Get Chrome launch flags for this profile."""
        return self.config.get_stealth_flags()
    
    def get_patches(self) -> Dict[str, Any]:
        """Get JavaScript patches for this profile."""
        return self.patches.get_all_patches()
    
    def get_user_agent(self) -> str:
        """Get the user agent string for this profile."""
        return (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        )

class MacOSProfile(StealthProfile):
    """Stealth profile mimicking macOS Chrome."""
    
    def get_user_agent(self) -> str:
        return (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        )

class WindowsProfile(StealthProfile):
    """Stealth profile mimicking Windows Chrome."""
    
    def get_user_agent(self) -> str:
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        )

class LinuxProfile(StealthProfile):
    """Stealth profile mimicking Linux Chrome."""
    
    def get_user_agent(self) -> str:
        return (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        )

def create_profile(profile_type: str = "macos") -> StealthProfile:
    """
    Create a stealth profile based on the specified type.
    
    Args:
        profile_type: Type of profile to create ("macos", "windows", or "linux")
        
    Returns:
        StealthProfile: The created stealth profile
    """
    profiles = {
        "macos": MacOSProfile,
        "windows": WindowsProfile,
        "linux": LinuxProfile
    }
    
    profile_class = profiles.get(profile_type.lower(), MacOSProfile)
    return profile_class() 