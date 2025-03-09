"""
Simple navigation example for CDP Browser.
"""
import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cdp_browser.browser.browser import Browser
from cdp_browser.utils.logging import configure_logging


async def main():
    """
    Simple navigation example.
    """
    # Configure logging
    configure_logging(level=20)  # INFO level
    
    # Create browser instance
    browser = Browser("localhost", 9223)
    
    try:
        # Connect to browser
        print("Connecting to browser...")
        await browser.connect()
        
        # Create a new page
        print("Creating new page...")
        page = await browser.new_page()
        
        # Navigate to URL
        url = "https://example.com"
        print(f"Navigating to {url}...")
        await page.navigate(url)
        
        # Print page title
        print(f"Page title: {page.title}")
        
        # Take screenshot
        print("Taking screenshot...")
        screenshot_data = await page.screenshot()
        
        # Save screenshot
        screenshot_path = "example_screenshot.png"
        with open(screenshot_path, "wb") as f:
            f.write(screenshot_data)
        print(f"Screenshot saved to: {screenshot_path}")
        
        # Get page content
        print("Getting page content...")
        result = await page.evaluate("document.documentElement.outerHTML")
        html = result.get("result", {}).get("value", "")
        
        # Print first 100 characters of HTML
        print(f"Page HTML (first 100 chars): {html[:100]}...")
        
        # Close page
        print("Closing page...")
        await browser.close_page(page.target_id)
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Disconnect from browser
        print("Disconnecting from browser...")
        await browser.disconnect()


if __name__ == "__main__":
    # Run the example
    asyncio.run(main()) 