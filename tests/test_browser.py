"""
Tests for Browser class.
"""
import asyncio
import os
import pytest
import subprocess
import time
from typing import AsyncGenerator

from cdp_browser.browser.browser import Browser
from cdp_browser.core.exceptions import CDPConnectionError, CDPError


def is_docker_running() -> bool:
    """Check if the CDP Docker container is running."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "ancestor=cdp-browser", "--format", "{{.ID}}"],
            capture_output=True,
            text=True,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def ensure_docker_running() -> None:
    """Ensure the CDP Docker container is running."""
    if not is_docker_running():
        # Build and start Docker container
        try:
            subprocess.run(
                ["docker", "build", "-t", "cdp-browser", "docker"],
                check=True,
            )
            subprocess.run(
                ["docker", "run", "-d", "-p", "9223:9223", "cdp-browser"],
                check=True,
            )
            # Wait for container to start
            time.sleep(2)
        except subprocess.CalledProcessError as e:
            pytest.skip(f"Failed to start Docker container: {e}")


@pytest.fixture(scope="session", autouse=True)
def docker_setup():
    """Setup Docker container for tests."""
    ensure_docker_running()


@pytest.fixture
async def browser() -> AsyncGenerator[Browser, None]:
    """Browser fixture."""
    browser = Browser("localhost", 9223)
    try:
        await browser.connect()
        yield browser
    finally:
        await browser.disconnect()


@pytest.mark.asyncio
async def test_browser_connect(browser: Browser):
    """Test browser connection."""
    assert browser.connection is not None
    assert browser.connection.connected
    
    # Test version info
    version = await browser.get_version()
    assert "Browser" in version
    assert "Protocol-Version" in version


@pytest.mark.asyncio
async def test_browser_get_targets(browser: Browser):
    """Test getting browser targets."""
    targets = await browser.get_targets()
    assert isinstance(targets, list)
    assert len(targets) > 0
    
    # Verify target structure
    target = targets[0]
    assert "id" in target or "targetId" in target
    assert "type" in target
    assert "url" in target


@pytest.mark.asyncio
async def test_browser_new_page(browser: Browser):
    """Test creating a new page."""
    page = await browser.new_page()
    assert page is not None
    assert page.attached
    assert page.target_id in browser.pages
    assert page.frame_id is not None
    
    # Test page info
    assert page.url == "about:blank"
    assert isinstance(page.title, str)
    
    # Close the page
    await browser.close_page(page.target_id)
    assert page.target_id not in browser.pages
    assert not page.attached


@pytest.mark.asyncio
async def test_browser_navigate(browser: Browser):
    """Test navigating to a URL."""
    page = await browser.new_page()
    try:
        # Navigate to a URL
        await page.navigate("https://example.com")
        assert "example.com" in page.url.lower()
        assert page.title
        
        # Test page content
        content = await page.evaluate("document.documentElement.outerHTML")
        assert isinstance(content, str)
        assert "Example Domain" in content
    finally:
        await browser.close_page(page.target_id)


@pytest.mark.asyncio
async def test_browser_screenshot(browser: Browser):
    """Test taking a screenshot."""
    page = await browser.new_page()
    try:
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
    finally:
        await browser.close_page(page.target_id)


@pytest.mark.asyncio
async def test_browser_cookies(browser: Browser):
    """Test cookie operations."""
    page = await browser.new_page()
    try:
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
    finally:
        await browser.close_page(page.target_id)


@pytest.mark.asyncio
async def test_browser_evaluate(browser: Browser):
    """Test JavaScript evaluation."""
    page = await browser.new_page()
    try:
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
    finally:
        await browser.close_page(page.target_id)


@pytest.mark.asyncio
async def test_browser_wait_for_load(browser: Browser):
    """Test waiting for page load."""
    page = await browser.new_page()
    try:
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
    finally:
        await browser.close_page(page.target_id)


@pytest.mark.asyncio
async def test_browser_error_handling(browser: Browser):
    """Test error handling."""
    page = await browser.new_page()
    try:
        # Test invalid URL
        with pytest.raises(CDPError):
            await page.navigate("invalid-url")
        
        # Test invalid selector
        with pytest.raises(CDPError):
            await page.evaluate("document.querySelector('nonexistent').textContent")
        
        # Test navigation timeout
        with pytest.raises(CDPTimeoutError):
            await page.navigate("https://example.com", timeout=0.001)
    finally:
        await browser.close_page(page.target_id) 