"""
Form interaction example for CDP Browser.
"""
import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cdp_browser.browser import Browser
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Form interaction example using saucedemo.com."""
    async with Browser(port=9223) as browser:
        logger.info("Browser connected")
        
        # Create a new page
        async with await browser.create_page() as page:
            logger.info("Page created")
            
            # Navigate to login page
            url = "https://www.saucedemo.com/"
            logger.info(f"Navigating to {url}")
            await page.navigate(url)
            
            # Type username
            logger.info("Typing username")
            await page.type("#user-name", "standard_user")
            
            # Type password
            logger.info("Typing password")
            await page.type("#password", "secret_sauce")
            
            # Click login button
            logger.info("Clicking login button")
            await page.click("#login-button")
            
            # Wait for navigation
            logger.info("Waiting for navigation")
            await page.wait_for_navigation()
            
            # Get current URL
            current_url = await page.get_current_url()
            logger.info(f"Current URL after login: {current_url}")
            
            # Verify we're on the inventory page
            assert "inventory.html" in current_url, "Login failed"
            logger.info("Login successful")

if __name__ == "__main__":
    # Run the example
    asyncio.run(main()) 