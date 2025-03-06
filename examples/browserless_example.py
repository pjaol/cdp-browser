"""
Example script for using browserless/chrome API.
"""
import asyncio
import base64
import json
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


async def get_content(url: str) -> str:
    """
    Get content of a URL using browserless API.
    
    Args:
        url: URL to get content from
        
    Returns:
        HTML content as string
    """
    content_endpoint = "/content"
    full_url = urljoin(BROWSERLESS_URL, content_endpoint)
    
    payload = {
        "url": url
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(full_url, json=payload) as response:
            if response.status != 200:
                raise Exception(f"Failed to get content: {response.status}")
            
            return await response.text()


async def main():
    """
    Main function.
    """
    try:
        # URL to navigate to
        url = "https://example.com"
        print(f"Taking screenshot of {url}...")
        
        # Take screenshot
        screenshot_data = await take_screenshot(url)
        
        # Save screenshot
        screenshot_path = "browserless_screenshot.png"
        with open(screenshot_path, "wb") as f:
            f.write(screenshot_data)
        print(f"Screenshot saved to: {screenshot_path}")
        
        # Get content
        print(f"Getting content of {url}...")
        content = await get_content(url)
        
        # Print first 100 characters of content
        print(f"Content (first 100 chars): {content[:100]}...")
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main()) 