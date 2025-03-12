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
    async with StealthBrowser(profile=profile, port=9223) as browser:
        yield browser

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
        await asyncio.sleep(10)  # Initial wait
        
        # Check if the test is still running
        is_running = await page.evaluate("""
            () => {
                const statusElement = document.getElementById('loader');
                return statusElement && statusElement.style.display !== 'none';
            }
        """)
        
        # Wait longer if tests are still running
        if is_running:
            logger.info("CreepJS tests still running, waiting longer...")
            await asyncio.sleep(10)
        
        # Extract the fingerprinting results
        logger.info("Extracting CreepJS fingerprinting results")
        fingerprint_results = await page.evaluate("""
            () => {
                // Function to extract text from an element
                const getText = (selector) => {
                    const el = document.querySelector(selector);
                    return el ? el.textContent.trim() : null;
                };
                
                // Function to get scoring information
                const getScore = (selector) => {
                    const el = document.querySelector(selector);
                    if (!el) return null;
                    
                    // Get text content and class name for scoring
                    const score = el.textContent.trim();
                    const cssClass = el.className;
                    const isBlocked = cssClass.includes('blocked');
                    const isWarning = cssClass.includes('warning');
                    const isSuccess = cssClass.includes('success');
                    
                    return { score, isBlocked, isWarning, isSuccess };
                };
                
                // Extract all results
                return {
                    // Overall trust score
                    trustScore: getScore('.trust-score'),
                    
                    // Browser fingerprinting
                    userAgent: {
                        reported: navigator.userAgent,
                        detected: getText('.user-agent-data')
                    },
                    
                    // Each fingerprinting category
                    fingerprinting: {
                        resistance: getScore('.resistance-fingerprinting .grade-score'),
                        bot: getScore('.bot-detection .grade-score'),
                        lies: getScore('.lies-detected .grade-score'),
                        trash: getScore('.trash-detected .grade-score')
                    },
                    
                    // Detailed fingerprinting results
                    details: {
                        canvas: getText('#fingerprint-data .canvas-fingerprint'),
                        webgl: getText('#fingerprint-data .webgl-fingerprint'),
                        audio: getText('#fingerprint-data .audio-fingerprint'),
                        fonts: getText('#fingerprint-data .fonts-fingerprint'),
                        screen: getText('#fingerprint-data .screen-fingerprint'),
                        timezone: getText('#fingerprint-data .timezone-fingerprint')
                    },
                    
                    // Bot detection results
                    botDetection: {
                        automation: getText('#bot-detection-data .automation'),
                        webdriver: getText('#bot-detection-data .webdriver'),
                        chrome: getText('#bot-detection-data .chrome-detection'),
                        selenium: getText('#bot-detection-data .selenium-detection')
                    },
                    
                    // Lie detection
                    lieDetection: {
                        navigatorLies: getText('#lies-detected-data .navigator-lies'),
                        featureLies: getText('#lies-detected-data .feature-lies')
                    }
                };
            }
        """)
        
        # Log and save the results
        logger.info("CreepJS fingerprinting results:")
        logger.info(json.dumps(fingerprint_results, indent=2))
        
        # Save results to file for later analysis
        results_file = save_results("creepjs", fingerprint_results)
        logger.info(f"Saved CreepJS results to {results_file}")
        
        # Basic assertions - these will evolve as we improve stealth capabilities
        assert fingerprint_results is not None, "Failed to retrieve fingerprinting results"
        
        # Check for trust score - we're mostly interested in logging results at this stage
        if fingerprint_results.get('trustScore'):
            logger.info(f"Trust score: {fingerprint_results['trustScore'].get('score')}")
        
        # Check for webdriver detection
        webdriver_detection = fingerprint_results.get('botDetection', {}).get('webdriver')
        if webdriver_detection:
            logger.info(f"Webdriver detection result: {webdriver_detection}")
            
        # We don't want hard assertions at this point since we're just gathering data
        # We'll refine our stealth approach based on the results
        
    except Exception as e:
        logger.error(f"Error during CreepJS fingerprinting test: {e}")
        raise
    finally:
        # Take a screenshot for visual verification
        try:
            screenshot_base64 = await page.send_command("Page.captureScreenshot")
            screenshot_data = screenshot_base64.get("data", "")
            if screenshot_data:
                os.makedirs("fingerprint_results", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                with open(f"fingerprint_results/creepjs_{timestamp}.png", "wb") as f:
                    import base64
                    f.write(base64.b64decode(screenshot_data))
                logger.info(f"Screenshot saved to fingerprint_results/creepjs_{timestamp}.png")
        except Exception as screenshot_error:
            logger.error(f"Failed to capture screenshot: {screenshot_error}")
        
        # Close the page
        await page.close()

@pytest.mark.asyncio
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
        await asyncio.sleep(15)  # Give it time to run all tests
        
        # Extract the results
        logger.info("Extracting Fingerprint.js results")
        fingerprint_results = await page.evaluate("""
            () => {
                // Try to find the visitor ID
                const visitorIdElement = document.querySelector('[data-testid="visitor-id-badge"]');
                const visitorId = visitorIdElement ? visitorIdElement.textContent.trim() : null;
                
                // Try to get bot detection result
                const botDetectionElement = document.querySelector('[data-testid="bot-detection-badge"]');
                const botDetection = botDetectionElement ? botDetectionElement.textContent.trim() : null;
                
                // Try to get incognito detection result
                const incognitoElement = document.querySelector('[data-testid="incognito-badge"]');
                const incognitoDetection = incognitoElement ? incognitoElement.textContent.trim() : null;
                
                // Try to get VPN detection result
                const vpnElement = document.querySelector('[data-testid="vpn-badge"]');
                const vpnDetection = vpnElement ? vpnElement.textContent.trim() : null;
                
                return {
                    visitorId,
                    botDetection,
                    incognitoDetection,
                    vpnDetection,
                    // Add browser identification info
                    browserInfo: {
                        userAgent: navigator.userAgent,
                        platform: navigator.platform,
                        language: navigator.language,
                        languages: navigator.languages,
                        cookieEnabled: navigator.cookieEnabled,
                        doNotTrack: navigator.doNotTrack,
                        hardwareConcurrency: navigator.hardwareConcurrency,
                        deviceMemory: navigator.deviceMemory,
                        screenWidth: screen.width,
                        screenHeight: screen.height,
                        colorDepth: screen.colorDepth,
                        pixelRatio: window.devicePixelRatio
                    }
                };
            }
        """)
        
        # Log and save the results
        logger.info("Fingerprint.js Pro results:")
        logger.info(json.dumps(fingerprint_results, indent=2))
        
        # Save results to file for later analysis
        results_file = save_results("fingerprintjs", fingerprint_results)
        logger.info(f"Saved Fingerprint.js results to {results_file}")
        
        # Basic assertions - these will evolve as we improve stealth capabilities
        assert fingerprint_results is not None, "Failed to retrieve Fingerprint.js results"
        
        # Check bot detection result
        if fingerprint_results.get('botDetection'):
            logger.info(f"Bot detection result: {fingerprint_results['botDetection']}")
            
    except Exception as e:
        logger.error(f"Error during Fingerprint.js Pro test: {e}")
        raise
    finally:
        # Take a screenshot for visual verification
        try:
            screenshot_base64 = await page.send_command("Page.captureScreenshot")
            screenshot_data = screenshot_base64.get("data", "")
            if screenshot_data:
                os.makedirs("fingerprint_results", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                with open(f"fingerprint_results/fingerprintjs_{timestamp}.png", "wb") as f:
                    import base64
                    f.write(base64.b64decode(screenshot_data))
                logger.info(f"Screenshot saved to fingerprint_results/fingerprintjs_{timestamp}.png")
        except Exception as screenshot_error:
            logger.error(f"Failed to capture screenshot: {screenshot_error}")
        
        # Close the page
        await page.close() 