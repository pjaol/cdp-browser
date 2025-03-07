"""
Form interaction example for CDP Browser.
"""
import asyncio
import os
import sys
import logging

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cdp_browser.browser.browser import Browser
from cdp_browser.browser.input import Input
from cdp_browser.utils.logging import configure_logging


async def main():
    """
    Form interaction example.
    """
    # Configure logging
    configure_logging(level=logging.INFO)
    
    # Create browser instance
    browser = Browser("localhost", 9223)
    
    try:
        # Connect to browser
        print("Connecting to browser...")
        await browser.connect()
        
        # Create a new page
        print("Creating new page...")
        page = await browser.new_page()
        
        # Navigate to GitHub login page
        await page.navigate("https://github.com")
        
        # Print page title
        print(f"Page title: {page.title}")
        
        # Take screenshot
        screenshot_data = await page.screenshot()
        with open("github.com_screenshot.png", "wb") as f:
            f.write(screenshot_data)
        print(f"Screenshot saved to: github.com_screenshot.png")
        
        # Fill a search form
        # First, click on the search button to open the search box
        search_button = "button[aria-label='Toggle navigation']"
        await browser.input.click(search_button)
        
        # Wait a bit for the search box to appear
        await asyncio.sleep(1)
        
        # Now type in the search box
        search_input = "input[name='q']"
        await browser.input.type(search_input, "python")
        
        # Press Enter to submit the search
        await browser.input.press("Enter")
        
        # Wait for the search results to load
        await asyncio.sleep(2)
        
        # Print the new page title
        print(f"Search results page title: {page.title}")
        
        # Take screenshot of search results
        screenshot_data = await page.screenshot()
        with open("github_search_results.png", "wb") as f:
            f.write(screenshot_data)
        print(f"Screenshot saved to: github_search_results.png")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Disconnect from browser
        print("Disconnecting from browser...")
        await browser.disconnect()


if __name__ == "__main__":
    # Run the example
    asyncio.run(main()) 