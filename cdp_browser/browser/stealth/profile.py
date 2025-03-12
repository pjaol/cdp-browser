"""
Configuration profile for stealth browser features.
"""

from typing import Dict, Any, List, Optional

class StealthProfile:
    """Configuration profile for stealth browser features."""
    
    def __init__(self,
                 level: str = "balanced",
                 user_agent: Optional[str] = None,
                 window_size: Optional[Dict[str, int]] = None,
                 languages: Optional[List[str]] = None):
        """
        Initialize a stealth profile.
        
        Args:
            level: Stealth level ("minimum", "balanced", or "maximum")
            user_agent: Custom user agent string
            window_size: Dictionary with width and height
            languages: List of language codes (e.g. ["en-US", "en"])
        """
        self.level = self._validate_level(level)
        self.user_agent = user_agent or "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        self.window_size = window_size or {"width": 1920, "height": 1080}
        self.languages = languages or ["en-US", "en"]
        
        # Validate window size
        if not isinstance(self.window_size, dict) or \
           not all(k in self.window_size for k in ["width", "height"]) or \
           not all(isinstance(v, int) for v in self.window_size.values()):
            raise ValueError("window_size must be a dictionary with 'width' and 'height' as integers")
        
        # Validate languages
        if not isinstance(self.languages, list) or \
           not all(isinstance(lang, str) for lang in self.languages):
            raise ValueError("languages must be a list of strings")
    
    def _validate_level(self, level: str) -> str:
        """Validate stealth level."""
        valid_levels = ["minimum", "balanced", "maximum"]
        if level not in valid_levels:
            raise ValueError(f"Invalid stealth level. Must be one of: {', '.join(valid_levels)}")
        return level
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        return {
            "level": self.level,
            "user_agent": self.user_agent,
            "window_size": self.window_size,
            "languages": self.languages
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StealthProfile':
        """Create profile from dictionary."""
        return cls(
            level=data.get("level", "balanced"),
            user_agent=data.get("user_agent"),
            window_size=data.get("window_size"),
            languages=data.get("languages")
        ) 