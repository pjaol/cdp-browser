"""
Example script for using Chrome DevTools Protocol (CDP) via the proxy
"""

import asyncio
import base64
import json
import os
import sys
import aiohttp

# Use the proxy port
CDP_URL = "http://localhost:9223"

async def take_screenshot(url: str):
    """
    Take a screenshot of a URL using CDP
    """
    try:
        # First, get the list of available targets
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{CDP_URL}/json/list") as response:
                if response.status != 200:
                    print(f"Error getting targets: {response.status}")
                    return None
                
                targets = await response.json()
                
                # If no targets are available, create a new one
                if not targets:
                    print("No targets available, creating a new one")
                    # This would require creating a new page, which is more complex
                    # For simplicity, we'll just return an error
                    return None
                
                # Use the first available target
                target = targets[0]
                target_id = target["id"]
                
                # Connect to the target via WebSocket
                ws_url = target["webSocketDebuggerUrl"]
                async with session.ws_connect(ws_url) as ws:
                    # Navigate to the URL
                    await ws.send_json({
                        "id": 1,
                        "method": "Page.navigate",
                        "params": {"url": url}
                    })
                    
                    # Wait for navigation to complete
                    while True:
                        msg = await ws.receive_json()
                        if msg.get("id") == 1:
                            break
                    
                    # Wait a bit for the page to render
                    await asyncio.sleep(1)
                    
                    # Capture screenshot
                    await ws.send_json({
                        "id": 2,
                        "method": "Page.captureScreenshot",
                        "params": {"format": "png", "quality": 100}
                    })
                    
                    # Wait for screenshot response
                    while True:
                        msg = await ws.receive_json()
                        if msg.get("id") == 2:
                            if "result" in msg and "data" in msg["result"]:
                                return base64.b64decode(msg["result"]["data"])
                            else:
                                print(f"Error taking screenshot: {msg}")
                                return None
    except Exception as e:
        print(f"Error taking screenshot: {e}")
        return None

async def get_content(url: str):
    """
    Get the HTML content of a URL using CDP
    """
    try:
        # First, get the list of available targets
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{CDP_URL}/json/list") as response:
                if response.status != 200:
                    print(f"Error getting targets: {response.status}")
                    return None
                
                targets = await response.json()
                
                # If no targets are available, create a new one
                if not targets:
                    print("No targets available, creating a new one")
                    # This would require creating a new page, which is more complex
                    # For simplicity, we'll just return an error
                    return None
                
                # Use the first available target
                target = targets[0]
                target_id = target["id"]
                
                # Connect to the target via WebSocket
                ws_url = target["webSocketDebuggerUrl"]
                async with session.ws_connect(ws_url) as ws:
                    # Navigate to the URL
                    await ws.send_json({
                        "id": 1,
                        "method": "Page.navigate",
                        "params": {"url": url}
                    })
                    
                    # Wait for navigation to complete
                    while True:
                        msg = await ws.receive_json()
                        if msg.get("id") == 1:
                            break
                    
                    # Wait a bit for the page to render
                    await asyncio.sleep(1)
                    
                    # Get the document content
                    await ws.send_json({
                        "id": 2,
                        "method": "Runtime.evaluate",
                        "params": {
                            "expression": "document.documentElement.outerHTML"
                        }
                    })
                    
                    # Wait for content response
                    while True:
                        msg = await ws.receive_json()
                        if msg.get("id") == 2:
                            if "result" in msg and "result" in msg["result"] and "value" in msg["result"]["result"]:
                                return msg["result"]["result"]["value"]
                            else:
                                print(f"Error getting content: {msg}")
                                return None
    except Exception as e:
        print(f"Error getting content: {e}")
        return None

async def main():
    """
    Main function
    """
    try:
        # Take a screenshot of example.com
        print("Taking screenshot of https://example.com...")
        screenshot_data = await take_screenshot("https://example.com")
        if screenshot_data:
            # Save the screenshot to a file
            with open("browserless_screenshot.png", "wb") as f:
                f.write(screenshot_data)
            print(f"Screenshot saved to browserless_screenshot.png")
        else:
            print("Failed to take screenshot")
        
        # Get the content of example.com
        print("Getting content of https://example.com...")
        content = await get_content("https://example.com")
        if content:
            print(f"Content length: {len(content)} characters")
            print(f"Content preview: {content[:200]}...")
        else:
            print("Failed to get content")
    except Exception as e:
        print(f"Error in main: {e}")

if __name__ == "__main__":
    asyncio.run(main())