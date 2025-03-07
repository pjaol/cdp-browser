"""
Main module for CDP Browser.
Demonstrates how to use the CDP client.
"""
import argparse
import asyncio
import logging
import os
import sys
from typing import Optional

from cdp_browser.browser.browser import Browser
from cdp_browser.utils.logging import configure_logging
from cdp_browser.utils.proxy import ProxyConfig


async def main(
    url: str,
    host: str = "localhost",
    port: int = 9222,
    proxy: Optional[str] = None,
    screenshot: Optional[str] = None,
) -> None:
    """
    Main function for CDP Browser.

    Args:
        url: URL to navigate to
        host: Chrome DevTools host
        port: Chrome DevTools port
        proxy: Proxy URL
        screenshot: Screenshot file path
    """
    # Create browser instance
    browser = Browser(host, port)
    
    try:
        # Connect to browser
        await browser.connect()
        
        # Create a new page
        page = await browser.new_page()
        
        # Navigate to URL
        await page.navigate(url)
        
        # Wait for page to load
        await asyncio.sleep(2)
        
        # Print page title
        print(f"Page title: {page.title}")
        
        # Take screenshot if requested
        if screenshot:
            screenshot_data = await page.screenshot()
            with open(screenshot, "wb") as f:
                f.write(screenshot_data)
            print(f"Screenshot saved to: {screenshot}")
    finally:
        # Disconnect from browser
        await browser.disconnect()


if __name__ == "__main__":
    # Configure argument parser
    parser = argparse.ArgumentParser(description="CDP Browser")
    parser.add_argument("url", help="URL to navigate to")
    parser.add_argument("--host", default="localhost", help="Chrome DevTools host")
    parser.add_argument("--port", type=int, default=9223, help="Chrome DevTools port")
    parser.add_argument("--proxy", help="Proxy URL")
    parser.add_argument("--screenshot", help="Screenshot file path")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    configure_logging(level=log_level)
    
    # Set proxy environment variable if specified
    if args.proxy:
        os.environ["PROXY_SERVER"] = args.proxy
    
    # Run main function
    asyncio.run(
        main(
            args.url,
            args.host,
            args.port,
            args.proxy,
            args.screenshot,
        )
    ) 