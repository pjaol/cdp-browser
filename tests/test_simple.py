"""Test simple browser operations."""
import logging
import pytest
from cdp_browser.browser import Browser
import asyncio

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
            try:
                # Navigate to test site
                logger.debug("Navigating to saucedemo.com")
                await asyncio.wait_for(
                    page.navigate("https://www.saucedemo.com/", wait_until="networkidle"), 
                    timeout=5.0
                )
                
                # Type username and password
                logger.debug("Typing credentials")
                await asyncio.wait_for(page.type("#user-name", "standard_user"), timeout=2.0)
                await asyncio.wait_for(page.type("#password", "secret_sauce"), timeout=2.0)
                
                # Click login button with networkidle waiting strategy
                logger.debug("Clicking login button")
                await asyncio.wait_for(
                    page.click("#login-button", wait_until="networkidle"), 
                    timeout=5.0
                )
                
                # No need to wait for navigation separately as click is already doing it
                
                # Verify we reached the inventory page
                current_url = await page.get_current_url()
                logger.debug(f"Final URL after login: {current_url}")
                assert current_url == "https://www.saucedemo.com/inventory.html"
                
            except asyncio.TimeoutError as e:
                logger.error(f"Timeout during page interaction: {e}")
                # Get navigation state for debugging
                nav_state = page._navigation_state if hasattr(page, '_navigation_state') else 'Unknown'
                logger.error(f"Navigation state: {nav_state}")
                raise

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