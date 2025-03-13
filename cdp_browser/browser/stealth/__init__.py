"""
StealthBrowser implementation for anti-detection.
"""
from typing import Optional, Dict, Any, List
import logging
import asyncio

from ..browser import Browser
from ..page import Page
from .profile import StealthProfile
from .patches import get_ordered_patches

logger = logging.getLogger(__name__)

class StealthBrowser(Browser):
    """A browser with anti-detection capabilities."""
    
    def __init__(self, profile: Optional[StealthProfile] = None, host: str = "localhost", port: int = 9223):
        """
        Initialize the stealth browser with optional profile.
        
        Args:
            profile: Optional StealthProfile for stealth settings
            host: Chrome DevTools host (default: localhost)
            port: Chrome DevTools port (default: 9223)
        """
        super().__init__(host=host, port=port)
        self.profile = profile or StealthProfile()
    
    async def create_page(self) -> Page:
        """Create a new page with stealth patches applied."""
        logger.debug("Creating new page using parent class...")
        page = await super().create_page()
        
        try:
            # Enable required domains one at a time
            logger.debug("Enabling required domains...")
            await page.send_command("Network.enable")
            await page.send_command("Page.enable")
            await page.send_command("Runtime.enable")
            
            # Navigate to blank page to establish a clean execution context
            logger.debug("Navigating to blank page to establish execution context...")
            await page.navigate("about:blank")
            await asyncio.sleep(1)  # Give time for context to be created
            
            # Apply stealth patches
            logger.debug("Applying stealth patches...")
            await self._apply_stealth_patches(page)
            
            # Apply user agent if specified
            if self.profile.user_agent:
                await page.send_command("Network.setUserAgentOverride", {
                    "userAgent": self.profile.user_agent,
                    "platform": "MacIntel",
                    "acceptLanguage": "en-US,en;q=0.9",
                    "userAgentMetadata": {
                        "brands": [
                            {"brand": "Chrome", "version": "121"},
                            {"brand": "Chromium", "version": "121"},
                            {"brand": "Not=A?Brand", "version": "24"}
                        ],
                        "fullVersion": "121.0.6167.85",
                        "platform": "macOS",
                        "platformVersion": "13.0.0",
                        "architecture": "x86",
                        "model": "",
                        "mobile": False,
                        "bitness": "64",
                        "wow64": False
                    }
                })
            
            # Apply viewport settings
            await page.send_command("Emulation.setDeviceMetricsOverride", {
                "width": self.profile.window_size["width"],
                "height": self.profile.window_size["height"],
                "deviceScaleFactor": 1,
                "mobile": False
            })
            
            logger.debug("Successfully created stealth page")
            return page
            
        except Exception as e:
            logger.error(f"Error setting up stealth page: {e}")
            try:
                await page.close()
            except Exception as close_error:
                logger.error(f"Error closing page after setup failure: {close_error}")
            raise RuntimeError(f"Failed to setup stealth page: {e}")
    
    async def _apply_stealth_patches(self, page: Page) -> None:
        """Apply all stealth patches to a page."""
        try:
            logger.debug("Applying stealth patches...")
            
            # Get ordered patches based on profile level
            ordered_patches = get_ordered_patches(self.profile.level)
            
            # Apply each patch in order
            for name, patch in ordered_patches:
                try:
                    logger.debug(f"Applying patch: {name}")
                    await page.send_command("Page.addScriptToEvaluateOnNewDocument", {
                        "source": patch["script"]
                    })
                except Exception as patch_error:
                    logger.error(f"Error applying patch {name}: {patch_error}")
            
            # Wait for patches to settle
            await asyncio.sleep(0.1)
            
            logger.debug("Successfully applied all stealth patches")
            
        except Exception as e:
            logger.error(f"Failed to apply stealth patches: {e}")
            raise RuntimeError(f"Failed to apply stealth patches: {e}")
    
    def get_profile(self) -> StealthProfile:
        """Get the current stealth profile."""
        return self.profile
    
    def update_profile(self, profile: StealthProfile) -> None:
        """
        Update the stealth profile.
        Note: Changes will only take effect after a browser restart.
        
        Args:
            profile: New StealthProfile instance
        """
        self.profile = profile
    
    async def apply_advanced_stealth_patches(self, page: Page) -> None:
        """
        Apply additional advanced stealth patches to a page.
        This can be used to enhance stealth capabilities for specific sites.
        
        Args:
            page: The page to apply patches to
        """
        try:
            logger.debug("Applying advanced stealth patches...")
            
            # Get all patches including experimental ones
            ordered_patches = get_ordered_patches("maximum")
            
            # Apply experimental patches
            for name, patch in ordered_patches:
                if name.startswith("experimental_"):
                    try:
                        logger.debug(f"Applying experimental patch: {name}")
                        await page.send_command("Page.addScriptToEvaluateOnNewDocument", {
                            "source": patch["script"]
                        })
                    except Exception as patch_error:
                        logger.error(f"Error applying experimental patch {name}: {patch_error}")
            
            logger.debug("Successfully applied advanced stealth patches")
            
        except Exception as e:
            logger.error(f"Failed to apply advanced stealth patches: {e}")
            raise RuntimeError(f"Failed to apply advanced stealth patches: {e}")
    
    async def _apply_page_patch(self, page: Page, patch: Dict[str, Any]) -> None:
        """Apply a patch to a specific page."""
        patch_type = patch["type"]
        
        if patch_type == "webdriver":
            await page.evaluate("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
        elif patch_type == "user_agent":
            if patch.get("value"):
                await page.send_command("Network.setUserAgentOverride", {
                    "userAgent": patch["value"]
                })
        elif patch_type == "viewport":
            size = patch.get("size", {})
            await page.send_command("Emulation.setDeviceMetricsOverride", {
                "width": size.get("width", 1920),
                "height": size.get("height", 1080),
                "deviceScaleFactor": 1,
                "mobile": False
            })
        # Add more page-specific patches as needed 