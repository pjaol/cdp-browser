"""
Form interaction example for CDP Browser.
"""
import asyncio
import os
import sys

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
    configure_logging(level=20)  # INFO level
    
    # Create browser instance
    browser = Browser("localhost", 9222)
    
    try:
        # Connect to browser
        print("Connecting to browser...")
        await browser.connect()
        
        # Create a new page
        print("Creating new page...")
        page = await browser.new_page()
        
        # Create input handler
        input_handler = Input(page)
        
        # Navigate to a search engine
        url = "https://duckduckgo.com/"
        print(f"Navigating to {url}...")
        await page.navigate(url)
        
        # Wait for page to load
        await asyncio.sleep(2)
        
        # Type in search box
        print("Typing in search box...")
        search_query = "Python CDP Browser"
        await input_handler.type("input[name='q']", search_query)
        
        # Take screenshot before search
        print("Taking screenshot before search...")
        screenshot_data = await page.screenshot()
        with open("search_before.png", "wb") as f:
            f.write(screenshot_data)
        
        # Click search button
        print("Clicking search button...")
        await input_handler.click("button[type='submit']")
        
        # Wait for results to load
        print("Waiting for results to load...")
        await asyncio.sleep(3)
        
        # Take screenshot after search
        print("Taking screenshot after search...")
        screenshot_data = await page.screenshot()
        with open("search_after.png", "wb") as f:
            f.write(screenshot_data)
        
        # Get search results
        print("Getting search results...")
        result = await page.evaluate("""
            Array.from(document.querySelectorAll('.result__title')).map(el => el.textContent.trim())
        """)
        
        # Print search results
        search_results = result.get("result", {}).get("value", [])
        print(f"Found {len(search_results)} search results:")
        for i, title in enumerate(search_results[:5], 1):
            print(f"{i}. {title}")
        
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