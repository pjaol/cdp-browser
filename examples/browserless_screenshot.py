"""
Example script for taking screenshots using browserless/chrome API.
"""
import asyncio
import base64
import os
import sys
from urllib.parse import urljoin

import aiohttp

# Base URL for browserless API
BROWSERLESS_URL = "http://localhost:9222"


async def take_screenshot(url: str) -> bytes:
    """
    Take a screenshot of a URL using browserless API.
    
    Args:
        url: URL to screenshot
        
    Returns:
        Screenshot as bytes
    """
    screenshot_endpoint = "/screenshot"
    full_url = urljoin(BROWSERLESS_URL, screenshot_endpoint)
    
    payload = {
        "url": url,
        "options": {
            "fullPage": True,
            "type": "png"
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(full_url, json=payload) as response:
            if response.status != 200:
                raise Exception(f"Failed to take screenshot: {response.status}")
            
            return await response.read()


async def main():
    """
    Main function.
    """
    try:
        # URLs to screenshot
        urls = [
            "https://example.com",
            "https://google.com",
            "https://github.com"
        ]
        
        for url in urls:
            print(f"Taking screenshot of {url}...")
            
            # Take screenshot
            screenshot_data = await take_screenshot(url)
            
            # Save screenshot
            filename = url.replace("https://", "").replace("http://", "").replace("/", "_")
            screenshot_path = f"{filename}_screenshot.png"
            with open(screenshot_path, "wb") as f:
                f.write(screenshot_data)
            print(f"Screenshot saved to: {screenshot_path}")
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main()) 