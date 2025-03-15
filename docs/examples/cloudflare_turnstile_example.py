#!/usr/bin/env python3
"""
Example script demonstrating how to handle Cloudflare Turnstile challenges.

This example shows:
1. How to detect when Cloudflare Turnstile is present
2. How to intercept the parameters needed for solving
3. Two ways to handle the challenge: 
   - Using enhanced browser fingerprinting (default)
   - Using an external CAPTCHA solving service (optional)
"""

import asyncio
import logging
import sys
import os
from typing import Optional

# Add CDP Browser to path if running the example directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from cdp_browser import StealthBrowser


# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("cf_turnstile_example")


# Optional: Integration with a CAPTCHA solving service
class CaptchaSolver:
    """Simple integration with a CAPTCHA solving service for Cloudflare Turnstile."""
    
    def __init__(self, api_key: str):
        """Initialize with an API key."""
        self.api_key = api_key
        
    async def solve_turnstile(self, params):
        """
        Solve Cloudflare Turnstile using an external service.
        
        Args:
            params: Turnstile parameters (sitekey, pageurl, data, etc.)
            
        Returns:
            str: Solution token or None if failed
        """
        logger.info(f"Solving Turnstile challenge with params: {params}")
        
        # In a real implementation, you would call the API of a service like 2captcha here
        # For example using aiohttp to make the request
        
        # This is just a placeholder - in a real implementation you would:
        # 1. Send the parameters to the service
        # 2. Poll for the solution
        # 3. Return the token
        
        logger.warning("CaptchaSolver.solve_turnstile is just a demonstration - no actual solving happening")
        await asyncio.sleep(2)  # Simulate API call
        
        # Return dummy token for demonstration purposes
        return None


async def handle_turnstile_challenge(browser, page, captcha_solver: Optional[CaptchaSolver] = None) -> bool:
    """
    Handle a Cloudflare Turnstile challenge when encountered.
    
    Args:
        browser: StealthBrowser instance
        page: Page with potential Turnstile challenge
        captcha_solver: Optional CaptchaSolver for external solving
        
    Returns:
        bool: True if challenge was handled successfully, False otherwise
    """
    # Get the Cloudflare Turnstile patch
    cf_patch = None
    for patch in browser.stealth.patches:
        if patch.NAME == "cloudflare_turnstile":
            cf_patch = patch
            break
    
    if not cf_patch:
        logger.error("Cloudflare Turnstile patch not found in browser")
        return False
    
    # Check if Turnstile is detected
    detection_result = await cf_patch.is_detected(page)
    if not detection_result.get("detected", False):
        logger.info("No Cloudflare Turnstile detected on page")
        return True
    
    logger.info(f"Detected Cloudflare Turnstile: {detection_result}")
    
    # If we have an external solver and appropriate parameters, use it
    if captcha_solver and detection_result.get("params"):
        params = detection_result.get("params")
        token = await captcha_solver.solve_turnstile(params)
        
        if token:
            logger.info("Successfully obtained Turnstile token from external solver")
            success = await cf_patch.apply_solution(page, token)
            return success
        else:
            logger.warning("External solver failed to solve Turnstile challenge")
    
    # Otherwise, rely on the enhanced fingerprinting provided by stealth patches
    logger.info("Relying on enhanced browser fingerprinting to bypass Turnstile")
    
    # Wait for navigation to complete (after potential auto-bypass)
    try:
        await page.waitForNavigation({"timeout": 10000})
        logger.info("Successful navigation after Turnstile challenge")
        return True
    except Exception as e:
        logger.error(f"Failed to navigate past Turnstile challenge: {e}")
        return False


async def main():
    """Main example function."""
    # Create a browser with stealth mode enabled (including Turnstile patch)
    browser = StealthBrowser(headless=False, stealth_level="maximum")
    
    # Optional: Initialize a CAPTCHA solving service
    # Uncomment and set your API key to use an external solver
    # api_key = "your_api_key_here"
    # captcha_solver = CaptchaSolver(api_key)
    captcha_solver = None
    
    try:
        # Connect to the browser
        await browser.connect()
        
        # Create a new page
        page = await browser.new_page()
        
        # Navigate to a page that might have Cloudflare Turnstile
        # For demonstration, we'll use a known page with Turnstile
        target_url = "https://nowsecure.nl/"  # This is a test site with Cloudflare protection
        
        logger.info(f"Navigating to {target_url}")
        await page.goto(target_url)
        
        # Handle any Turnstile challenge
        success = await handle_turnstile_challenge(browser, page, captcha_solver)
        
        if success:
            logger.info("Successfully handled Cloudflare Turnstile challenge")
            
            # Now you can interact with the actual page content
            title = await page.title()
            logger.info(f"Page title: {title}")
            
            # Take a screenshot to verify success
            await page.screenshot({"path": "turnstile_success.png"})
            logger.info("Screenshot saved to turnstile_success.png")
        else:
            logger.error("Failed to handle Cloudflare Turnstile challenge")
    
    finally:
        # Close the browser
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main()) 