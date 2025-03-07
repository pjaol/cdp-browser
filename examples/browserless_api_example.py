#!/usr/bin/env python3
"""
Example script for using the browserless API with CDP Browser.
"""
import asyncio
import os
import sys
import logging

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cdp_browser.browser.browser import Browser
from cdp_browser.utils.logging import configure_logging


async def main():
    """
    Main function.
    """
    # Configure logging
    configure_logging(level=logging.INFO)
    
    # Create browser instance
    browser = Browser("localhost", 9223)
    
    try:
        # Connect to browser
        print("Connecting to browser...")
        await browser.connect()
        
        # Take a screenshot directly using the browserless API
        print("Taking screenshot using browserless API...")
        screenshot_data = await browser.take_screenshot("https://example.com")
        with open("browserless_api_screenshot.png", "wb") as f:
            f.write(screenshot_data)
        print(f"Screenshot saved to: browserless_api_screenshot.png")
        
        # Create a new page
        print("Creating new page...")
        page = await browser.new_page()
        
        # Navigate to a URL
        print("Navigating to example.com...")
        await page.navigate("https://example.com")
        
        # Print page title
        print(f"Page title: {page.title}")
        
        # Take screenshot
        print("Taking screenshot...")
        screenshot_data = await page.screenshot()
        with open("browserless_page_screenshot.png", "wb") as f:
            f.write(screenshot_data)
        print(f"Screenshot saved to: browserless_page_screenshot.png")
        
        # Get HTML content
        print("Getting HTML content...")
        html = await page.get_html()
        print(f"HTML length: {len(html)} characters")
        print(f"HTML preview: {html[:200]}...")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Disconnect from browser
        print("Disconnecting from browser...")
        await browser.disconnect()


if __name__ == "__main__":
    # Run the example
    asyncio.run(main()) 