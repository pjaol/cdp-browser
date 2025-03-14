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
            # Wait for CDP connection to be fully established
            logger.debug("Waiting for CDP connection...")
            await asyncio.sleep(1)
            
            # Enable required domains with retries
            domains = ["Network", "Page", "Runtime"]
            for domain in domains:
                retries = 0
                while retries < 3:
                    try:
                        logger.debug(f"Enabling {domain} domain (attempt {retries + 1})...")
                        await page.send_command(f"{domain}.enable")
                        logger.debug(f"Successfully enabled {domain} domain")
                        break
                    except Exception as e:
                        retries += 1
                        if retries == 3:
                            raise RuntimeError(f"Failed to enable {domain} domain after 3 attempts: {e}")
                        logger.warning(f"Failed to enable {domain} domain (attempt {retries}): {e}")
                        await asyncio.sleep(1)
            
            # Initialize page after domains are enabled
            logger.debug("Initializing page...")
            await page.initialize()
            
            # Wait for execution context to be ready with a longer timeout
            logger.debug("Waiting for execution context...")
            await page.wait_for_execution_context(timeout=10.0)
            
            # Apply stealth patches
            logger.debug("Applying stealth patches...")
            await self._apply_stealth_patches(page)
            
            # Apply user agent if specified
            if self.profile.user_agent:
                logger.debug("Setting user agent...")
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
                        "fullVersion": "121.0.0.0",
                        "platform": "macOS",
                        "platformVersion": "10.15.7",
                        "architecture": "x86",
                        "model": "",
                        "mobile": False,
                        "bitness": "64",
                        "wow64": False
                    }
                })
            
            # Apply viewport settings
            logger.debug("Setting viewport...")
            await page.send_command("Emulation.setDeviceMetricsOverride", {
                "width": self.profile.window_size["width"],
                "height": self.profile.window_size["height"],
                "deviceScaleFactor": 1,
                "mobile": False
            })
            
            # Verify execution context is still valid
            logger.debug("Verifying execution context...")
            await page.evaluate("1 + 1")
            
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
            logger.debug(f"Ordered patches: {[name for name, _ in ordered_patches]}")
            
            # Apply each patch in order and verify
            for name, patch in ordered_patches:
                try:
                    logger.debug(f"Applying patch: {name}")
                    logger.debug(f"Patch script: {patch['script'][:100]}...")  # Log the first 100 chars of the script

                    # Add the script to evaluate on new document
                    await page.send_command("Page.addScriptToEvaluateOnNewDocument", {
                        "source": patch["script"],
                        "worldName": "main"  # Ensure script runs in main world
                    })

                    # Also evaluate immediately in current context
                    try:
                        await page.evaluate(patch["script"])
                        logger.debug(f"Successfully applied patch: {name}")
                    except Exception as eval_error:
                        logger.error(f"Error evaluating patch {name}: {eval_error}")
                        raise
                    
                    # Verify the patch worked by checking a key property
                    if name == "chrome_runtime_basic":
                        result = await page.evaluate("typeof window.chrome === 'object'")
                        logger.debug(f"Chrome object verification: {result}")
                        if not result:
                            raise RuntimeError(f"Failed to initialize Chrome object in {name}")
                    elif name == "chrome_runtime_advanced":
                        result = await page.evaluate("typeof window.chrome.runtime === 'object'")
                        logger.debug(f"Chrome runtime verification: {result}")
                        if not result:
                            raise RuntimeError(f"Failed to initialize Chrome runtime in {name}")
                    elif name == "webdriver" or name == "webdriver_basic" or name == "webdriver_advanced":
                        result = await page.evaluate("navigator.webdriver === false")
                        logger.debug(f"Navigator verification for {name}: {result}")
                        if not result:
                            raise RuntimeError(f"Failed to patch webdriver in {name}")
                    elif name == "plugins":
                        result = await page.evaluate("navigator.plugins.length > 0")
                        logger.debug(f"Plugins verification: {result}")
                        if not result:
                            raise RuntimeError(f"Failed to initialize plugins in {name}")
                    
                except Exception as patch_error:
                    logger.error(f"Error applying patch {name}: {patch_error}")
                    raise
            
            # Final verification of all patches
            verification = await page.evaluate("""
                (() => {
                    const results = {};
                    try {
                        results.chrome = typeof window.chrome === 'object';
                        results.runtime = window.chrome && typeof window.chrome.runtime === 'object';
                        results.webdriver = navigator.webdriver === false;
                        results.webdriverExists = 'webdriver' in navigator;
                        results.vendor = navigator.vendor === 'Google Inc.';
                        results.plugins = navigator.plugins.length > 0;
                        results.error = null;
                    } catch (e) {
                        results.error = e.message;
                    }
                    return results;
                })()
            """)
            
            logger.debug(f"Final stealth verification: {verification}")
            
            if verification.get('error'):
                raise RuntimeError(f"Error during final verification: {verification['error']}")
            
            if not verification.get('chrome'):
                raise RuntimeError("Chrome object not properly initialized")
            if not verification.get('runtime'):
                raise RuntimeError("Chrome runtime not properly initialized")
            if not verification.get('webdriver'):
                raise RuntimeError("Webdriver property not properly set to false")
            if not verification.get('webdriverExists'):
                raise RuntimeError("Webdriver property should exist but is missing")
            
            logger.debug("Successfully applied and verified all stealth patches")
            
        except Exception as e:
            logger.error(f"Failed to apply stealth patches: {e}")
            # Get current state for debugging
            try:
                state = await page.evaluate("""
                    (() => ({
                        chrome: typeof window.chrome,
                        runtime: window.chrome ? typeof window.chrome.runtime : undefined,
                        webdriver: navigator.webdriver,
                        vendor: navigator.vendor,
                        plugins: navigator.plugins ? navigator.plugins.length : 0
                    }))()
                """)
                logger.error(f"Current state: {state}")
            except Exception as state_error:
                logger.error(f"Failed to get current state: {state_error}")
            raise RuntimeError(f"Failed to apply stealth patches: {e}")
            
        # Wait for everything to settle
        await asyncio.sleep(0.5)
    
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
                    "userAgent": patch["value"],
                    "platform": "MacIntel",
                    "acceptLanguage": "en-US,en;q=0.9",
                    "userAgentMetadata": {
                        "brands": [
                            {"brand": "Chrome", "version": "121"},
                            {"brand": "Chromium", "version": "121"},
                            {"brand": "Not=A?Brand", "version": "24"}
                        ],
                        "fullVersion": "121.0.0.0",
                        "platform": "macOS",
                        "platformVersion": "10.15.7",
                        "architecture": "x86",
                        "model": "",
                        "mobile": False,
                        "bitness": "64",
                        "wow64": False
                    }
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