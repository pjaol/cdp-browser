"""
Tests for Browser class.
"""
import asyncio
import os
import pytest

from cdp_browser.browser.browser import Browser
from cdp_browser.core.exceptions import CDPConnectionError


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_browser_connect():
    """Test browser connection."""
    browser = Browser("localhost", 9222)
    
    try:
        await browser.connect()
        assert browser.connection is not None
        assert browser.connection.connected
    except CDPConnectionError:
        pytest.skip("Chrome not available")
    finally:
        await browser.disconnect()


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_browser_get_version():
    """Test getting browser version."""
    browser = Browser("localhost", 9222)
    
    try:
        await browser.connect()
        version = await browser.get_version()
        assert "Browser" in version
        assert "Protocol-Version" in version
    except CDPConnectionError:
        pytest.skip("Chrome not available")
    finally:
        await browser.disconnect()


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_browser_new_page():
    """Test creating a new page."""
    browser = Browser("localhost", 9222)
    
    try:
        await browser.connect()
        page = await browser.new_page()
        assert page is not None
        assert page.attached
        
        # Close the page
        await browser.close_page(page.target_id)
        assert page.target_id not in browser.pages
    except CDPConnectionError:
        pytest.skip("Chrome not available")
    finally:
        await browser.disconnect()


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_browser_navigate():
    """Test navigating to a URL."""
    browser = Browser("localhost", 9222)
    
    try:
        await browser.connect()
        page = await browser.new_page()
        
        # Navigate to a URL
        await page.navigate("https://example.com")
        assert "example.com" in page.url.lower()
        
        # Close the page
        await browser.close_page(page.target_id)
    except CDPConnectionError:
        pytest.skip("Chrome not available")
    finally:
        await browser.disconnect() 