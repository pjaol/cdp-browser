#!/usr/bin/env python3
"""
Simple test script to use the browserless API directly.
"""
import asyncio
import base64
import json
import os
import sys

import aiohttp

# Browserless API URL
BROWSERLESS_URL = "http://localhost:9223"

async def take_screenshot(url: str) -> bytes:
    """
    Take a screenshot of a URL using browserless API.
    """
    print(f"Taking screenshot of {url}...")
    
    async with aiohttp.ClientSession() as session:
        # Use the /screenshot endpoint
        screenshot_url = f"{BROWSERLESS_URL}/screenshot"
        
        # Prepare the payload
        payload = {
            "url": url,
            "options": {
                "fullPage": True,
                "type": "png"
            }
        }
        
        # Send the request
        async with session.post(screenshot_url, json=payload) as response:
            if response.status != 200:
                print(f"Error: {response.status}")
                print(await response.text())
                return None
            
            # Get the screenshot data
            return await response.read()

async def get_content(url: str) -> str:
    """
    Get the content of a URL using browserless API.
    """
    print(f"Getting content of {url}...")
    
    async with aiohttp.ClientSession() as session:
        # Use the /content endpoint
        content_url = f"{BROWSERLESS_URL}/content"
        
        # Prepare the payload
        payload = {
            "url": url
        }
        
        # Send the request
        async with session.post(content_url, json=payload) as response:
            if response.status != 200:
                print(f"Error: {response.status}")
                print(await response.text())
                return None
            
            # Get the content
            return await response.text()

async def main():
    """
    Main function.
    """
    try:
        # Take a screenshot of example.com
        screenshot_data = await take_screenshot("https://example.com")
        if screenshot_data:
            # Save the screenshot to a file
            with open("browserless_test_screenshot.png", "wb") as f:
                f.write(screenshot_data)
            print(f"Screenshot saved to browserless_test_screenshot.png")
        
        # Get the content of example.com
        content = await get_content("https://example.com")
        if content:
            print(f"Content length: {len(content)} characters")
            print(f"Content preview: {content[:200]}...")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 