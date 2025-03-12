"""
Advanced stealth tests against fingerprinting services.
"""

import pytest
from pytest_asyncio import fixture
import asyncio
from cdp_browser.browser.stealth import StealthBrowser
from cdp_browser.browser.stealth.profile import StealthProfile
import logging
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)

@fixture(scope="function")
async def advanced_stealth_browser():
    """Create an advanced stealth browser instance with maximum protection."""
    logger.info("Creating advanced stealth browser")
    profile = StealthProfile(
        level="maximum",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        window_size={"width": 1920, "height": 1080},
        languages=["en-US", "en"]
    )
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            browser = StealthBrowser(profile=profile, port=9223)
            await browser.__aenter__()
            break
        except Exception as e:
            retry_count += 1
            logger.error(f"Failed to create browser (attempt {retry_count}/{max_retries}): {e}")
            
            if retry_count >= max_retries:
                raise
            
            # Wait before retrying
            await asyncio.sleep(1)
    
    try:
        yield browser
    finally:
        await browser.__aexit__(None, None, None)

def save_results(name, results):
    """Save fingerprinting results to file for later analysis."""
    # Create results directory if it doesn't exist
    os.makedirs("fingerprint_results", exist_ok=True)
    
    # Create a timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"fingerprint_results/{name}_{timestamp}.json"
    
    # Save the results
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Results saved to {filename}")
    return filename

@pytest.mark.asyncio
async def test_creepjs_fingerprint(advanced_stealth_browser):
    """Test stealth capabilities against CreepJS fingerprinting."""
    logger.info("Starting CreepJS fingerprint test")
    
    # Create a page with our advanced stealth browser
    page = await advanced_stealth_browser.create_page()
    
    try:
        # Navigate to the CreepJS fingerprinting page
        logger.info("Navigating to CreepJS fingerprinting page")
        await page.navigate("https://abrahamjuliot.github.io/creepjs/")
        
        # Wait for the page to fully load and run all fingerprinting tests
        # CreepJS takes some time to complete all tests
        logger.info("Waiting for CreepJS to complete fingerprinting...")
        await asyncio.sleep(20)  # Give plenty of time for all tests to complete
        
        # Take a screenshot for visual verification
        try:
            screenshot_base64 = await page.send_command("Page.captureScreenshot")
            screenshot_data = screenshot_base64.get("data", "")
            if screenshot_data:
                os.makedirs("fingerprint_results", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"fingerprint_results/creepjs_{timestamp}.png"
                with open(screenshot_path, "wb") as f:
                    import base64
                    f.write(base64.b64decode(screenshot_data))
                logger.info(f"Screenshot saved to {screenshot_path}")
        except Exception as screenshot_error:
            logger.error(f"Failed to capture screenshot: {screenshot_error}")
        
        # Get the page content using a simpler approach
        try:
            # Get document.documentElement.outerHTML
            content_result = await page.send_command(
                "Runtime.evaluate",
                {
                    "expression": "document.documentElement.outerHTML",
                    "returnByValue": True,
                }
            )
            
            html_content = content_result.get("result", {}).get("value", "")
            
            # Save the HTML for analysis
            if html_content:
                html_file = f"fingerprint_results/creepjs_html_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"HTML content saved to {html_file}")
                
                # Extract some basic information from the HTML
                # This is very basic and not as detailed as using proper evaluate,
                # but it will at least give us something to work with
                fingerprint_results = {
                    "htmlCaptured": True,
                    "userAgent": {
                        "reported": html_content.split('User Agent: ')[1].split('</div>')[0] if 'User Agent: ' in html_content else "Not found"
                    },
                    "botDetection": {
                        "detected": "ChromeDriver" in html_content or "automation detected" in html_content.lower()
                    }
                }
                
                # Save results to file for later analysis
                results_file = save_results("creepjs_basic", fingerprint_results)
                logger.info(f"Saved basic CreepJS results to {results_file}")
            else:
                logger.error("Failed to extract HTML content")
        except Exception as content_error:
            logger.error(f"Error extracting page content: {content_error}")
        
    except Exception as e:
        logger.error(f"Error during CreepJS fingerprinting test: {e}")
        raise
    finally:
        # Close the page
        await page.close()

@pytest.mark.asyncio
@pytest.mark.xfail(reason="Fingerprint.js demo site may cause WebSocket connection issues")
async def test_fingerprint_js_detection(advanced_stealth_browser):
    """Test against Fingerprint.js Pro detection."""
    logger.info("Starting Fingerprint.js Pro detection test")
    
    page = await advanced_stealth_browser.create_page()
    
    try:
        # Navigate to the Fingerprint.js demo page
        logger.info("Navigating to Fingerprint.js Pro demo page")
        await page.navigate("https://fingerprint.com/demo/")
        
        # Wait for the page to load and run all detection tests
        logger.info("Waiting for Fingerprint.js to complete...")
        await asyncio.sleep(15)  # Shorter wait time to avoid connection issues
        
        # Take a screenshot for visual verification
        try:
            screenshot_base64 = await page.send_command("Page.captureScreenshot")
            screenshot_data = screenshot_base64.get("data", "")
            if screenshot_data:
                os.makedirs("fingerprint_results", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"fingerprint_results/fingerprintjs_{timestamp}.png"
                with open(screenshot_path, "wb") as f:
                    import base64
                    f.write(base64.b64decode(screenshot_data))
                logger.info(f"Screenshot saved to {screenshot_path}")
        except Exception as screenshot_error:
            logger.error(f"Failed to capture screenshot: {screenshot_error}")
        
        # Get the page content using a simpler approach with a shorter timeout
        try:
            # Get document.documentElement.outerHTML with a shorter timeout
            content_result = await asyncio.wait_for(
                page.send_command(
                    "Runtime.evaluate",
                    {
                        "expression": "document.documentElement.outerHTML",
                        "returnByValue": True,
                    }
                ),
                timeout=10.0  # Shorter timeout to avoid connection issues
            )
            
            html_content = content_result.get("result", {}).get("value", "")
            
            # Save the HTML for analysis
            if html_content:
                # Save a shorter version of the HTML to avoid large files
                html_content_truncated = html_content[:100000] if len(html_content) > 100000 else html_content
                html_file = f"fingerprint_results/fingerprintjs_html_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content_truncated)
                logger.info(f"HTML content saved to {html_file}")
                
                # Extract some basic information from the HTML
                fingerprint_results = {
                    "htmlCaptured": True,
                    "botDetection": {
                        "detected": "bot" in html_content.lower() and "detected" in html_content.lower()
                    }
                }
                
                # Try to extract user agent if the pattern exists
                try:
                    if 'User-Agent:</dt><dd>' in html_content:
                        user_agent = html_content.split('User-Agent:</dt><dd>')[1].split('</dd>')[0]
                        fingerprint_results["browserInfo"] = {"userAgent": user_agent}
                except Exception as parse_error:
                    logger.error(f"Error parsing user agent: {parse_error}")
                    fingerprint_results["browserInfo"] = {"userAgent": "Extraction failed"}
                
                # Save results to file for later analysis
                results_file = save_results("fingerprintjs_basic", fingerprint_results)
                logger.info(f"Saved basic Fingerprint.js results to {results_file}")
            else:
                logger.error("Failed to extract HTML content")
        except asyncio.TimeoutError:
            logger.error("Timeout while getting page content")
        except Exception as content_error:
            logger.error(f"Error extracting page content: {content_error}")
        
    except Exception as e:
        logger.error(f"Error during Fingerprint.js Pro test: {e}")
    finally:
        # Close the page
        try:
            await page.close()
        except Exception as close_error:
            logger.error(f"Error closing page: {close_error}") 