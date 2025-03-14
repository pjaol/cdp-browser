import pytest
import pytest_asyncio
import asyncio
import logging
from cdp_browser.browser.stealth import StealthBrowser
from cdp_browser.stealth.profile import StealthProfile

logger = logging.getLogger(__name__)

@pytest_asyncio.fixture
async def stealth_browser():
    """Create a stealth browser instance for testing."""
    browser = StealthBrowser()
    try:
        await browser.connect()
        logger.info("Created stealth browser for testing")
        yield browser
    finally:
        await browser.close()
        logger.info("Closed stealth browser")

@pytest.mark.asyncio
async def test_webdriver_property_hidden(stealth_browser):
    """Test that the WebDriver property is properly hidden."""
    async with await stealth_browser.create_page() as page:
        # Wait for execution context to be ready
        await page.wait_for_execution_context(timeout=15.0)
        
        # Enable required domains with retries
        domains = ["Network", "Page", "Runtime"]
        for domain in domains:
            for attempt in range(3):
                try:
                    await page.enable_domain(domain)
                    logger.info(f"Successfully enabled {domain} domain")
                    break
                except Exception as e:
                    if attempt == 2:
                        raise RuntimeError(f"Failed to enable {domain} domain after 3 attempts: {e}")
                    await asyncio.sleep(1)

        # Navigate to a test page
        await page.navigate("about:blank")
        await asyncio.sleep(2)  # Wait for initialization

        # Check navigator.webdriver property
        webdriver_check = """
        () => {
            const results = {
                webdriver: navigator.webdriver,
                hasWebdriver: 'webdriver' in navigator,
                automationControlled: navigator.webdriver === undefined,
                chromeDriver: window.navigator.hasOwnProperty('webdriver'),
                driverUndefined: window.navigator.webdriver === undefined,
                cdp: window.navigator.hasOwnProperty('cdp'),
                selenium: window.navigator.hasOwnProperty('selenium')
            };
            return results;
        }
        """
        results = await page.evaluate(webdriver_check)
        
        # Log detailed results
        logger.info("WebDriver detection results:")
        for key, value in results.items():
            logger.info(f"{key}: {value}")

        # Assertions
        assert results['webdriver'] is None or results['webdriver'] is False, \
            "navigator.webdriver should be None or False"
        assert not results['hasWebdriver'], \
            "navigator should not have webdriver property"
        assert results['automationControlled'], \
            "automation controlled should be properly hidden"
        assert not results['chromeDriver'], \
            "window.navigator should not have webdriver property"
        assert results['driverUndefined'], \
            "window.navigator.webdriver should be undefined"
        assert not results['cdp'], \
            "CDP property should not be present"
        assert not results['selenium'], \
            "Selenium property should not be present"

@pytest.mark.asyncio
async def test_automation_flags(stealth_browser):
    """Test that automation flags and properties are properly hidden."""
    async with await stealth_browser.create_page() as page:
        await page.wait_for_execution_context(timeout=15.0)
        
        # Enable required domains
        for domain in ["Network", "Page", "Runtime"]:
            await page.enable_domain(domain)

        await page.navigate("about:blank")
        await asyncio.sleep(2)

        # Check various automation flags
        automation_check = """
        () => {
            const results = {
                // Chrome automation properties
                automationControlled: window.navigator.webdriver === undefined,
                permissionsPolicyViolation: !document.hasOwnProperty('webdriver'),
                
                // Additional automation checks
                languages: navigator.languages.length > 0,
                plugins: navigator.plugins.length > 0,
                webGL: !!window.WebGLRenderingContext,
                
                // Chrome-specific properties
                chrome: window.chrome && Object.keys(window.chrome).length > 0,
                permissions: window.Notification && window.Notification.permission !== 'denied',
                
                // Debugging properties
                debugger: !window.navigator.hasOwnProperty('webdriver') && 
                         !window.navigator.hasOwnProperty('__selenium_evaluate') &&
                         !window.navigator.hasOwnProperty('__selenium_unwrapped')
            };
            return results;
        }
        """
        results = await page.evaluate(automation_check)
        
        # Log detailed results
        logger.info("Automation detection results:")
        for key, value in results.items():
            logger.info(f"{key}: {value}")

        # Assertions
        assert results['automationControlled'], \
            "Automation controlled flag should be hidden"
        assert results['permissionsPolicyViolation'], \
            "Permissions policy should not expose webdriver"
        assert results['languages'], \
            "Browser should have language settings"
        assert results['plugins'], \
            "Browser should have plugins"
        assert results['webGL'], \
            "WebGL should be available"
        assert results['chrome'], \
            "Chrome object should be present"
        assert results['permissions'], \
            "Permissions should be properly configured"
        assert results['debugger'], \
            "Debugger properties should be hidden" 