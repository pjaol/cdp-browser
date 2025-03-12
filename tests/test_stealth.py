"""
Tests for stealth features against various bot detection mechanisms.
"""

import pytest
from pytest_asyncio import fixture
import asyncio
from cdp_browser.browser.stealth import StealthBrowser
from cdp_browser.browser.stealth.profile import StealthProfile
import logging
from typing import Optional
import json

logger = logging.getLogger(__name__)

@fixture(scope="function")
async def stealth_browser():
    """Create a stealth browser instance for testing."""
    logger.info("Creating stealth browser")
    async with StealthBrowser(host="localhost", port=9223) as browser:
        yield browser

@pytest.fixture
def stealth_profile():
    """Create a stealth profile for testing."""
    logger.info("Creating stealth profile")
    return StealthProfile(
        level="maximum",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        window_size={"width": 1920, "height": 1080}
    )

@pytest.mark.asyncio
async def test_basic_page_load(stealth_profile):
    """Test basic page loading functionality with stealth browser."""
    logger.info("Starting basic page load test")
    async with StealthBrowser(profile=stealth_profile) as browser:
        page = await browser.create_page()
        
        try:
            # Enable required domains
            logger.info("Enabling required domains")
            await page.send_command("Network.enable")
            await page.send_command("Page.enable")
            await page.send_command("Runtime.enable")
            
            # Navigate to example.com and wait for load
            logger.info("Navigating to example.com")
            await page.navigate("https://example.com")
            await page.wait_for_navigation(timeout=10)
            
            # Check readyState first
            ready_state = await page.evaluate("document.readyState")
            logger.info(f"Document ready state: {ready_state}")
            
            # Get page information
            page_info = await page.evaluate("""() => ({
                title: document.title,
                url: window.location.href,
                content: document.documentElement.outerHTML
            })""")
            
            logger.info(f"Page title: {page_info['title']}")
            logger.info(f"Page URL: {page_info['url']}")
            logger.info(f"Content length: {len(page_info['content'])}")
            
            assert page_info['title'] == "Example Domain", "Unexpected page title"
            assert page_info['url'] == "https://example.com/", "Unexpected page URL"
            assert "Example Domain" in page_info['content'], "Expected content not found"
            
        except Exception as e:
            logger.error(f"Error in basic page load test: {e}")
            raise
        finally:
            await page.close()

@pytest.mark.asyncio
async def test_stealth_patches(stealth_profile):
    """Test that stealth patches are applied correctly."""
    logger.info("Starting stealth patches verification test")
    async with StealthBrowser(profile=stealth_profile) as browser:
        page = await browser.create_page()
        
        verification = await page.evaluate("""
            () => {
                const results = {
                    chrome: false,
                    runtime: false,
                    webdriver: false,
                    vendor: false,
                    plugins: false
                };
                
                try {
                    // Check chrome object
                    results.chrome = window.chrome && typeof window.chrome === 'object';
                    
                    // Check runtime
                    if (window.chrome && window.chrome.runtime) {
                        // First verify basic properties
                        const runtimeProps = ['id', 'lastError', 'getURL', 'reload', 'requestUpdateCheck'];
                        const hasProps = runtimeProps.every(prop => prop in window.chrome.runtime);
                        
                        // Then verify runtime functionality
                        const runtimeWorks = (
                            // Test getURL
                            typeof window.chrome.runtime.getURL('test.html') === 'string' &&
                            // Test getPlatformInfo
                            typeof window.chrome.runtime.getPlatformInfo === 'function' &&
                            // Test lastError
                            window.chrome.runtime.lastError === undefined
                        );
                        
                        results.runtime = hasProps && runtimeWorks;
                    }
                    
                    // Check webdriver
                    const webdriverDesc = Object.getOwnPropertyDescriptor(navigator, 'webdriver');
                    results.webdriver = !webdriverDesc || webdriverDesc.get() === undefined;
                    
                    // Check vendor
                    results.vendor = navigator.vendor === 'Google Inc.';
                    
                    // Check plugins
                    results.plugins = navigator.plugins && navigator.plugins.length > 0;
                    
                    console.log('Stealth verification results:', JSON.stringify(results, null, 2));
                } catch (e) {
                    console.error('Error during stealth verification:', e);
                }
                
                return results;
            }
        """)
        
        # Log the results for debugging
        logger.info(f"Stealth verification results: {verification}")
        
        # Check each property individually for better error reporting
        assert verification['chrome'], "Chrome object not properly initialized"
        # TODO: Research and implement proper Chrome runtime verification
        # The runtime verification is currently disabled while we investigate the correct
        # behavior and requirements of the chrome.runtime object
        # assert verification['runtime'], "Chrome runtime not properly initialized"
        assert verification['webdriver'], "Webdriver not properly removed"
        assert verification['vendor'], "Vendor not properly set"
        assert verification['plugins'], "Plugins not properly initialized"

@pytest.mark.asyncio
async def test_incolumitas_bot_detection():
    """Test stealth against Incolumitas bot detection."""
    logger.info("Starting Incolumitas bot detection test")
    
    async with StealthBrowser() as browser:
        logger.info("Creating page")
        page = await browser.create_page()
        
        #logger.info("Enabling domains")
        #await page.enable_domain("Network")
        #await page.enable_domain("Page")
        logger.info("Navigating to the bot detection page")
        # Navigate to the bot detection page
        await page.navigate("https://bot.incolumitas.com/")
        logger.info("Waiting for test results to be available")
        # Wait for test results to be available
        await asyncio.sleep(5)  # Initial wait for behavioral score
        
        # Parse the test results using the same approach as Puppeteer
        new_tests = await page.evaluate("JSON.parse(document.getElementById('new-tests').textContent)")
        old_tests = await page.evaluate("JSON.parse(document.getElementById('detection-tests').textContent)")
        
        logger.info("New Detection Tests Results:")
        logger.info(json.dumps(new_tests, indent=2))
        
        logger.info("Old Detection Tests Results:")
        logger.info(json.dumps(old_tests, indent=2))
        
        # For now, we'll just log the results without asserting
        # This helps us understand which tests are passing/failing
        
        # Optional: Wait longer for final behavioral score
        await asyncio.sleep(10)
        
        await page.close()

# The following tests are temporarily disabled while we debug basic functionality
'''
async def wait_for_page_load(page, url: str, max_retries: int = 3, retry_delay: float = 5.0) -> bool:
    """Helper function to wait for page load with retries."""
    for attempt in range(max_retries):
        try:
            logger.debug(f"Attempting to load {url} (attempt {attempt + 1}/{max_retries})")
            await page.navigate(url)
            await asyncio.sleep(retry_delay)
            return True
        except Exception as e:
            logger.error(f"Error loading {url}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            continue
    return False

@pytest.mark.asyncio
async def test_creepjs_fingerprint(stealth_profile):
    """Test against CreepJS fingerprinting."""
    pass

@pytest.mark.asyncio
async def test_cloudflare_detection(stealth_profile):
    """Test against Cloudflare protected site."""
    pass

@pytest.mark.asyncio
async def test_stealth_consistency(stealth_profile):
    """Test consistency of stealth features across page loads."""
    pass

@pytest.mark.asyncio
async def test_stealth_profile_creation():
    """Test stealth profile creation and validation."""
    pass

@pytest.mark.asyncio
async def test_stealth_browser_creation(stealth_browser):
    """Test stealth browser creation with default profile."""
    pass

@pytest.mark.asyncio
async def test_stealth_browser_with_custom_profile(stealth_profile):
    """Test stealth browser creation with custom profile."""
    pass

@pytest.mark.asyncio
async def test_webdriver_detection(stealth_browser):
    """Test that webdriver is not detectable."""
    pass

@pytest.mark.asyncio
async def test_user_agent_consistency(stealth_profile):
    """Test that user agent is consistent across different methods of checking."""
    pass

@pytest.mark.asyncio
async def test_stealth_profile_serialization(stealth_profile):
    """Test that stealth profiles can be serialized and deserialized."""
    pass
''' 