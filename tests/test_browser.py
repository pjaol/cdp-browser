"""
Tests for Browser class.
"""
import asyncio
import os
import pytest
from typing import AsyncGenerator

from cdp_browser.browser.browser import Browser
from cdp_browser.core.exceptions import CDPConnectionError, CDPError, CDPTimeoutError

@pytest.fixture(autouse=True)
async def cleanup_browser():
    """Cleanup any leftover browser pages after each test."""
    # Store initial state
    initial_targets = []
    try:
        async with Browser(host="0.0.0.0", port=9223) as browser:
            initial_targets = await browser.get_targets()
            initial_target_ids = {t.get("id") or t.get("targetId") for t in initial_targets if t.get("type") == "page"}
    except Exception as e:
        print(f"Error getting initial browser state: {str(e)}")
    
    yield
    
    # Clean up after test, but preserve initial pages
    try:
        async with Browser(host="0.0.0.0", port=9223) as browser:
            current_targets = await browser.get_targets()
            for target in current_targets:
                target_id = target.get("id") or target.get("targetId")
                if target_id and target.get("type") == "page":
                    if target_id not in initial_target_ids:
                        try:
                            await browser.close_page(target_id)
                        except Exception as e:
                            print(f"Error cleaning up page {target_id}: {str(e)}")
    except Exception as e:
        print(f"Error during browser cleanup: {str(e)}")


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_browser_connect():
    """Test browser connection."""
    async with Browser(host="0.0.0.0", port=9223) as browser:
        assert browser.connection is not None
        assert browser.connection.connected
        
        # Test version info
        version = await browser.get_version()
        assert "product" in version
        assert "Chrome" in version["product"]
        assert "protocolVersion" in version


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_browser_get_targets():
    """Test getting browser targets."""
    async with Browser(host="0.0.0.0", port=9223) as browser:
        # First get initial targets
        targets = await browser.get_targets()
        assert isinstance(targets, list)
        
        # If no targets exist, create a new page
        if not targets:
            async with await browser.new_page() as page:
                targets = await browser.get_targets()
                assert isinstance(targets, list)
                assert len(targets) > 0
                
                # Verify target structure
                target = next(t for t in targets if t.get("type") == "page")
                assert "id" in target or "targetId" in target
                assert target["type"] == "page"
                assert "url" in target
        else:
            # Verify target structure of existing target
            target = targets[0]
            assert "id" in target or "targetId" in target
            assert "type" in target
            assert "url" in target


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_browser_new_page():
    """Test creating a new page."""
    async with Browser(host="0.0.0.0", port=9223) as browser:
        async with await browser.new_page() as page:
            assert page is not None
            assert page.attached
            assert page.target_id in browser.pages
            assert page.frame_id is not None
            
            # Test page info
            assert page.url == "about:blank"
            assert isinstance(page.title, str)


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_browser_navigate():
    """Test navigating to a URL."""
    async with Browser(host="0.0.0.0", port=9223) as browser:
        async with await browser.new_page() as page:
            # Navigate to a URL
            await page.navigate("https://example.com")
            assert "example.com" in page.url.lower()
            assert page.title
            
            # Test page content
            content = await page.evaluate("document.documentElement.outerHTML")
            assert isinstance(content, str)
            assert "Example Domain" in content


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_browser_screenshot():
    """Test taking a screenshot."""
    async with Browser(host="0.0.0.0", port=9223) as browser:
        async with await browser.new_page() as page:
            await page.navigate("https://example.com")
            
            # Take PNG screenshot
            png_data = await page.screenshot(format="png")
            assert isinstance(png_data, bytes)
            assert len(png_data) > 0
            assert png_data.startswith(b"\x89PNG")
            
            # Take JPEG screenshot
            jpeg_data = await page.screenshot(format="jpeg", quality=80)
            assert isinstance(jpeg_data, bytes)
            assert len(jpeg_data) > 0
            assert jpeg_data.startswith(b"\xff\xd8")


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_browser_cookies():
    """Test cookie operations."""
    async with Browser(host="0.0.0.0", port=9223) as browser:
        async with await browser.new_page() as page:
            await page.navigate("https://example.com")
            
            # Set cookies
            test_cookies = [
                {
                    "name": "test1",
                    "value": "value1",
                    "domain": "example.com",
                    "path": "/",
                },
                {
                    "name": "test2",
                    "value": "value2",
                    "domain": "example.com",
                    "path": "/",
                },
            ]
            await page.set_cookies(test_cookies)
            
            # Get cookies
            cookies = await page.get_cookies()
            assert isinstance(cookies, list)
            assert len(cookies) >= 2
            
            cookie_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
            assert cookie_dict["test1"] == "value1"
            assert cookie_dict["test2"] == "value2"


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_browser_evaluate():
    """Test JavaScript evaluation."""
    async with Browser(host="0.0.0.0", port=9223) as browser:
        async with await browser.new_page() as page:
            await page.navigate("https://example.com")
            
            # Test simple evaluation
            result = await page.evaluate("2 + 2")
            assert result == 4
            
            # Test DOM manipulation
            await page.evaluate("document.title = 'Test Title'")
            title = await page.evaluate("document.title")
            assert title == "Test Title"
            
            # Test error handling
            with pytest.raises(CDPError) as exc_info:
                await page.evaluate("nonexistentFunction()")
            assert "ReferenceError" in str(exc_info.value)


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_browser_wait_for_load():
    """Test waiting for page load."""
    async with Browser(host="0.0.0.0", port=9223) as browser:
        async with await browser.new_page() as page:
            # Start navigation
            navigation_task = asyncio.create_task(
                page.navigate("https://example.com")
            )
            
            # Wait for load
            await page.wait_for_load()
            
            # Ensure navigation completed
            await navigation_task
            
            assert "example.com" in page.url.lower()
            assert page.title


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_browser_error_handling():
    """Test error handling."""
    async with Browser(host="0.0.0.0", port=9223) as browser:
        async with await browser.new_page() as page:
            # Test invalid URL
            with pytest.raises(CDPError):
                await page.navigate("invalid-url")
            
            # Test invalid selector
            with pytest.raises(CDPError):
                await page.evaluate("document.querySelector('nonexistent').textContent")
            
            # Test navigation timeout
            with pytest.raises(CDPTimeoutError):
                await page.navigate("https://example.com", timeout=0.001) 