"""
Debug test for Cloudflare Turnstile to understand XFAIL behavior.
"""

import asyncio
import logging
import inspect
import pytest

logger = logging.getLogger(__name__)

# Import the fixture from test_stealth_fingerprint
from tests.test_stealth_fingerprint import advanced_stealth_browser

@pytest.mark.asyncio
async def test_cloudflare_turnstile_debug(advanced_stealth_browser):
    """Simple debug test for Cloudflare Turnstile."""
    print("\n===== DEBUG TEST FOR CLOUDFLARE TURNSTILE =====")
    
    # Print details about the browser
    print(f"Browser type: {type(advanced_stealth_browser)}")
    
    # Examine the browser structure
    print("\nBrowser attributes:")
    for attr in dir(advanced_stealth_browser):
        if not attr.startswith('_'):  # Skip private attributes
            try:
                value = getattr(advanced_stealth_browser, attr)
                if not callable(value):  # Skip methods
                    print(f"  {attr}: {type(value)}")
            except Exception as e:
                print(f"  {attr}: [Error: {e}]")
    
    # Look for patches in a different way
    print("\nLooking for stealth patches:")
    if hasattr(advanced_stealth_browser, 'patches'):
        print(f"Found patches attribute with {len(advanced_stealth_browser.patches)} items")
        for i, patch in enumerate(advanced_stealth_browser.patches):
            print(f"  {i+1}. {getattr(patch, 'NAME', 'unknown')} ({type(patch).__name__})")
    else:
        print("No 'patches' attribute found")
    
    # Try to find the Cloudflare Turnstile patch using dir()
    print("\nSearching for Cloudflare Turnstile:")
    for attr in dir(advanced_stealth_browser):
        if 'cloudflare' in attr.lower() or 'turnstile' in attr.lower():
            print(f"Found potential match: {attr}")
    
    # Create a page
    print("\nCreating page...")
    page = await advanced_stealth_browser.create_page()
    print(f"Page created: {page}")
    
    # Navigate to a test site
    print("\nNavigating to test site...")
    await page.navigate("https://example.com")
    print("Navigation complete")
    
    # Get page title
    result = await page.send_command(
        "Runtime.evaluate",
        {
            "expression": "document.title",
            "returnByValue": True,
        }
    )
    title = result.get("result", {}).get("value", "Unknown")
    print(f"Page title: {title}")
    
    # Clean up
    print("\nClosing page...")
    await page.close()
    print("Page closed")
    
    # Test succeeded
    print("\n===== DEBUG TEST COMPLETE =====")
    assert True 