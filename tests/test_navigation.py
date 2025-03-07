"""
Tests for navigation functionality.
"""
import asyncio
import os
import pytest

from cdp_browser.browser.browser import Browser
from cdp_browser.core.exceptions import CDPError, CDPTimeoutError, CDPNavigationError


@pytest.mark.asyncio
async def test_navigation():
    """Test basic navigation."""
    # Skip if Chrome is not available
    if not os.environ.get("CHROME_AVAILABLE"):
        pytest.skip("Chrome not available")
    
    browser = Browser()
    try:
        # Connect to browser
        await browser.connect()
        
        # Create a new page
        page = await browser.new_page()
        
        # Navigate to a URL
        await page.navigate("https://example.com")
        
        # Check that the URL and title are correct
        assert "example.com" in page.url
        assert "Example Domain" in page.title
        
        # Navigate to another URL
        await page.navigate("https://google.com")
        
        # Check that the URL and title are correct
        assert "google.com" in page.url
        assert "Google" in page.title
        
        # Go back
        result = await page.go_back()
        assert result is True
        
        # Check that we're back at example.com
        assert "example.com" in page.url
        assert "Example Domain" in page.title
        
        # Go forward
        result = await page.go_forward()
        assert result is True
        
        # Check that we're back at google.com
        assert "google.com" in page.url
        assert "Google" in page.title
        
        # Reload the page
        await page.reload()
        
        # Check that we're still at google.com
        assert "google.com" in page.url
        assert "Google" in page.title
    finally:
        # Disconnect from browser
        await browser.disconnect()


@pytest.mark.asyncio
async def test_wait_for_selector():
    """Test waiting for a selector."""
    # Skip if Chrome is not available
    if not os.environ.get("CHROME_AVAILABLE"):
        pytest.skip("Chrome not available")
    
    browser = Browser()
    try:
        # Connect to browser
        await browser.connect()
        
        # Create a new page
        page = await browser.new_page()
        
        # Navigate to a URL
        await page.navigate("https://example.com")
        
        # Wait for a selector that exists
        result = await page.wait_for_selector("h1")
        assert result is True
        
        # Wait for a selector that doesn't exist (with short timeout)
        result = await page.wait_for_selector("non-existent-element", timeout=1)
        assert result is False
    finally:
        # Disconnect from browser
        await browser.disconnect()


@pytest.mark.asyncio
async def test_wait_for_navigation():
    """Test waiting for navigation."""
    # Skip if Chrome is not available
    if not os.environ.get("CHROME_AVAILABLE"):
        pytest.skip("Chrome not available")
    
    browser = Browser()
    try:
        # Connect to browser
        await browser.connect()
        
        # Create a new page
        page = await browser.new_page()
        
        # Start navigation and wait for it to complete
        navigation_task = asyncio.create_task(page.wait_for_navigation())
        await page.evaluate('window.location.href = "https://example.com"')
        await navigation_task
        
        # Check that we navigated to example.com
        assert "example.com" in page.url
        assert "Example Domain" in page.title
        
        # Test with URL pattern
        navigation_task = asyncio.create_task(page.wait_for_navigation(url_pattern="google"))
        await page.evaluate('window.location.href = "https://google.com"')
        await navigation_task
        
        # Check that we navigated to google.com
        assert "google.com" in page.url
        assert "Google" in page.title
    finally:
        # Disconnect from browser
        await browser.disconnect()


@pytest.mark.asyncio
async def test_get_html_and_text():
    """Test getting HTML and text content."""
    # Skip if Chrome is not available
    if not os.environ.get("CHROME_AVAILABLE"):
        pytest.skip("Chrome not available")
    
    browser = Browser()
    try:
        # Connect to browser
        await browser.connect()
        
        # Create a new page
        page = await browser.new_page()
        
        # Navigate to a URL
        await page.navigate("https://example.com")
        
        # Get HTML content
        html = await page.get_html()
        assert "<html" in html
        assert "<h1>Example Domain</h1>" in html
        
        # Get text content
        text = await page.get_text()
        assert "Example Domain" in text
    finally:
        # Disconnect from browser
        await browser.disconnect()


@pytest.mark.asyncio
async def test_wait_for_function():
    """Test waiting for a function to return a truthy value."""
    # Skip if Chrome is not available
    if not os.environ.get("CHROME_AVAILABLE"):
        pytest.skip("Chrome not available")
    
    browser = Browser()
    try:
        # Connect to browser
        await browser.connect()
        
        # Create a new page
        page = await browser.new_page()
        
        # Navigate to a URL
        await page.navigate("https://example.com")
        
        # Wait for a function that returns immediately
        result = await page.wait_for_function("return document.querySelector('h1') !== null")
        assert result is True
        
        # Wait for a function with a delay
        result = await page.wait_for_function("""
        return new Promise(resolve => {
            setTimeout(() => {
                resolve(document.title === 'Example Domain');
            }, 500);
        });
        """)
        assert result is True
        
        # Test timeout (with short timeout)
        with pytest.raises(CDPTimeoutError):
            await page.wait_for_function("return false", timeout=1)
    finally:
        # Disconnect from browser
        await browser.disconnect()


@pytest.mark.asyncio
async def test_viewport():
    """Test viewport manipulation."""
    # Skip if Chrome is not available
    if not os.environ.get("CHROME_AVAILABLE"):
        pytest.skip("Chrome not available")
    
    browser = Browser()
    try:
        # Connect to browser
        await browser.connect()
        
        # Create a new page
        page = await browser.new_page()
        
        # Set viewport size
        await page.set_viewport(800, 600)
        
        # Navigate to a URL
        await page.navigate("https://example.com")
        
        # Check viewport size
        dimensions = await page.evaluate("""
        ({
            width: window.innerWidth,
            height: window.innerHeight
        })
        """)
        width = dimensions.get("result", {}).get("value", {}).get("width", 0)
        height = dimensions.get("result", {}).get("value", {}).get("height", 0)
        
        # Allow for some small differences due to scrollbars, etc.
        assert abs(width - 800) < 20
        assert abs(height - 600) < 20
        
        # Reset viewport
        await page.reset_viewport()
    finally:
        # Disconnect from browser
        await browser.disconnect() 