"""
Stealth mode example for CDP Browser.

This example demonstrates how to use the stealth mode to avoid detection by
fingerprinting services. The stealth mode includes various techniques to make
the browser appear more like a regular user's browser.
"""
import asyncio
import os
import sys
from datetime import datetime
import base64

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cdp_browser.browser.stealth import StealthBrowser
from cdp_browser.browser.stealth.profile import StealthProfile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Stealth mode example to avoid fingerprinting."""
    # Create a stealth profile with customized settings
    profile = StealthProfile(
        level="maximum",  # Maximum stealth protection
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        window_size={"width": 1920, "height": 1080},
        languages=["en-US", "en"]
    )
    
    # Create a stealth browser with the profile
    async with StealthBrowser(profile=profile, port=9223) as browser:
        logger.info("Stealth browser connected")
        
        # Create a new page
        page = await browser.create_page()
        logger.info("Page created with stealth protections")
        
        try:
            # Navigate to a fingerprinting site
            url = "https://abrahamjuliot.github.io/creepjs/"
            logger.info(f"Navigating to fingerprinting test site: {url}")
            await page.navigate(url)
            
            # Wait for the page to load and run all fingerprinting tests
            logger.info("Waiting for fingerprinting tests to complete...")
            await asyncio.sleep(15)
            
            # Take a screenshot
            logger.info("Taking screenshot...")
            screenshot_base64 = await page.send_command("Page.captureScreenshot")
            screenshot_data = screenshot_base64.get("data", "")
            
            if screenshot_data:
                os.makedirs("stealth_results", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"stealth_results/creepjs_{timestamp}.png"
                
                with open(screenshot_path, "wb") as f:
                    f.write(base64.b64decode(screenshot_data))
                logger.info(f"Screenshot saved to {screenshot_path}")
            
            # Get the page content
            logger.info("Getting page content...")
            content_result = await page.send_command(
                "Runtime.evaluate",
                {
                    "expression": "document.documentElement.outerHTML",
                    "returnByValue": True,
                }
            )
            
            html_content = content_result.get("result", {}).get("value", "")
            
            # Save the HTML for analysis
            if html_content:
                os.makedirs("stealth_results", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                html_file = f"stealth_results/creepjs_html_{timestamp}.html"
                
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"HTML content saved to {html_file}")
                
                # Simple analysis to check if bot detection was triggered
                bot_detected = "ChromeDriver" in html_content or "automation detected" in html_content.lower()
                if bot_detected:
                    logger.warning("Bot detection was triggered!")
                else:
                    logger.info("No bot detection triggered - stealth mode working!")
        
        finally:
            # Close the page
            await page.close()
            logger.info("Page closed")

if __name__ == "__main__":
    # Run the example
    asyncio.run(main()) 