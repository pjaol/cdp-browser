"""
Form interaction example for CDP Browser.
"""
import asyncio
import logging

from cdp_browser.browser import Browser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Form interaction example using saucedemo.com."""
    logger.info("Starting form interaction example")
    
    async with Browser(port=9223) as browser:
        logger.info("Browser connected")
        
        async with await browser.create_page() as page:
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
            logger.info(f"Current URL: {current_url}")
            assert current_url == "https://www.saucedemo.com/inventory.html"
            logger.info("Successfully logged in!")

if __name__ == "__main__":
    # Run the example
    asyncio.run(main()) 