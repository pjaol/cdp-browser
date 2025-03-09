"""
Simple navigation example for CDP Browser.
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
    """Simple navigation example."""
    async with Browser(port=9223) as browser:
        logger.info("Browser connected")
        
        # Create a new page
        async with await browser.create_page() as page:
            logger.info("Page created")
            
            # Navigate to URL
            url = "https://example.com"
            logger.info(f"Navigating to {url}")
            await page.navigate(url)
            
            # Get current URL
            current_url = await page.get_current_url()
            logger.info(f"Current URL: {current_url}")
            
            # Navigate to another URL
            url = "https://www.example.org"
            logger.info(f"Navigating to {url}")
            await page.navigate(url)
            
            # Get current URL
            current_url = await page.get_current_url()
            logger.info(f"Current URL: {current_url}")

if __name__ == "__main__":
    # Run the example
    asyncio.run(main()) 