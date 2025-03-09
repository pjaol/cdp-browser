"""Test simple browser operations."""
import logging
import pytest
from cdp_browser.browser import Browser

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_browser_lifecycle():
    """Test basic browser lifecycle operations."""
    logger.info("Starting browser lifecycle test")
    async with Browser(port=9223) as browser:
        # Create a new page
        page = await browser.create_page()
        assert page is not None
        
        # Navigate to a simple page first
        await page.navigate("http://example.com")
        current_url = await page.get_current_url()
        assert current_url == "https://example.com/"
        
        # Close the page
        await page.close()

@pytest.mark.asyncio
async def test_page_navigation():
    """Test page navigation and URL tracking."""
    logger.info("Starting page navigation test")
    async with Browser(port=9223) as browser:
        async with await browser.create_page() as page:
            # Navigate to first URL
            await page.navigate("http://example.com")
            current_url = await page.get_current_url()
            assert current_url == "https://example.com/"
            
            # Navigate to second URL
            await page.navigate("https://www.example.org")
            current_url = await page.get_current_url()
            assert current_url == "https://www.example.org/"

@pytest.mark.asyncio
async def test_page_interaction():
    """Test page interactions like typing and clicking."""
    logger.info("Starting page interaction test")
    async with Browser(port=9223) as browser:
        async with await browser.create_page() as page:
            # Navigate to test site
            await page.navigate("https://www.saucedemo.com/")
            
            # Type username and password
            await page.type("#user-name", "standard_user")
            await page.type("#password", "secret_sauce")
            
            # Click login button
            await page.click("#login-button")
            
            # Wait for navigation and verify URL
            await page.wait_for_navigation()
            current_url = await page.get_current_url()
            assert current_url == "https://www.saucedemo.com/inventory.html"

@pytest.mark.asyncio
async def test_multiple_pages():
    """Test handling multiple pages."""
    logger.info("Starting multiple pages test")
    async with Browser(port=9223) as browser:
        # Create first page
        page1 = await browser.create_page()
        await page1.navigate("http://example.com")
        
        # Create second page
        page2 = await browser.create_page()
        await page2.navigate("https://www.example.org")
        
        # Verify URLs
        assert await page1.get_current_url() == "https://example.com/"
        assert await page2.get_current_url() == "https://www.example.org/"
        
        # Close pages
        await page1.close()
        await page2.close()

@pytest.mark.asyncio
async def test_page_events():
    """Test page event handling."""
    logger.info("Starting page events test")
    async with Browser(port=9223) as browser:
        async with await browser.create_page() as page:
            # Enable Page domain
            await page.enable_domain("Page")
            
            # Navigate and verify load events are triggered
            await page.navigate("http://example.com")
            assert page._load_complete is True
            assert page._navigation_complete is True 