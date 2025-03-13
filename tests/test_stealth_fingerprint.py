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
import sys
from datetime import datetime

# Configure logging to show more details
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
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

@pytest.mark.asyncio
@pytest.mark.xfail(reason="Cloudflare sites may cause WebSocket connection issues")
async def test_cloudflare_detection(advanced_stealth_browser):
    """Test against Cloudflare's bot detection."""
    print("\n===== Starting Cloudflare bot detection test =====")
    logger.info("Starting Cloudflare bot detection test")
    
    # Apply additional patches based on Intoli's research
    print("Applying advanced stealth patches...")
    await apply_advanced_stealth_patches(advanced_stealth_browser)
    
    print("Creating page...")
    page = await advanced_stealth_browser.create_page()
    
    # Create results to gather data even if we encounter errors
    cloudflare_results = {
        "htmlCaptured": False,
        "challengeDetected": False,
        "title": "Unknown",
        "currentUrl": "Unknown",
        "cfCookies": [],
        "cloudflareInfo": {},
        "botDetection": {
            "detected": False,
            "indicators": []
        }
    }
    
    try:
        # Navigate to a site with Cloudflare protection
        # Using a known site that implements Cloudflare but isn't too aggressive
        print("Navigating to Cloudflare site...")
        logger.info("Navigating to a site with Cloudflare protection")
        await page.navigate("https://www.cloudflare.com/")
        print("Navigation initiated.")
        
        # Wait a shorter time before taking initial data
        print("Waiting 2 seconds...")
        await asyncio.sleep(2)
        print("Wait completed.")
        
        # Capture a screenshot early to avoid losing it due to WebSocket issues
        try:
            print("Taking early screenshot...")
            logger.info("Taking an early screenshot")
            screenshot_base64 = await asyncio.wait_for(
                page.send_command("Page.captureScreenshot"),
                timeout=5.0
            )
            screenshot_data = screenshot_base64.get("data", "")
            if screenshot_data:
                os.makedirs("fingerprint_results", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"fingerprint_results/cloudflare_early_{timestamp}.png"
                with open(screenshot_path, "wb") as f:
                    import base64
                    f.write(base64.b64decode(screenshot_data))
                print(f"Early screenshot saved to {screenshot_path}")
                logger.info(f"Early screenshot saved to {screenshot_path}")
        except Exception as screenshot_error:
            print(f"❌ Failed to capture early screenshot: {screenshot_error}")
            logger.error(f"Failed to capture early screenshot: {screenshot_error}")
            
        # Get initial page content with timeout
        try:
            print("Getting initial page content...")
            logger.info("Getting initial page content")
            content_result = await asyncio.wait_for(
                page.send_command(
                    "Runtime.evaluate",
                    {
                        "expression": "document.documentElement.outerHTML",
                        "returnByValue": True,
                    }
                ),
                timeout=5.0
            )
            
            html_content = content_result.get("result", {}).get("value", "")
            print(f"HTML content length: {len(html_content)}")
            
            # Save the initial HTML content
            if html_content:
                html_file = f"fingerprint_results/cloudflare_html_early_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"Initial HTML content saved to {html_file}")
                logger.info(f"Initial HTML content saved to {html_file}")
                cloudflare_results["htmlCaptured"] = True
                
                # Try to extract title from HTML
                if "<title>" in html_content and "</title>" in html_content:
                    cloudflare_results["title"] = html_content.split("<title>")[1].split("</title>")[0]
                    print(f"Page title: {cloudflare_results['title']}")
                    
                # Check for Cloudflare challenge indicators
                cloudflare_indicators = [
                    "cf-browser-verification",
                    "cf_captcha_container",
                    "cf-challenge",
                    "cloudflare-challenge",
                    "security challenge",
                    "ray id",
                    "checking your browser",
                    "just a moment",
                    "clearance"
                ]
                
                detected_indicators = [indicator for indicator in cloudflare_indicators 
                                      if indicator in html_content.lower()]
                
                challenge_detected = len(detected_indicators) > 0
                cloudflare_results["challengeDetected"] = challenge_detected
                cloudflare_results["botDetection"]["detected"] = challenge_detected
                cloudflare_results["botDetection"]["indicators"] = detected_indicators
                
                if detected_indicators:
                    print(f"⚠️ Detected Cloudflare indicators: {detected_indicators}")
                else:
                    print("✅ No Cloudflare challenge indicators detected")
                
                # Save early results in case we encounter errors later
                early_results_file = save_results("cloudflare_early_data", cloudflare_results)
                print(f"Early results saved to {early_results_file}")
                logger.info(f"Saved early Cloudflare results to {early_results_file}")
        except Exception as content_error:
            print(f"❌ Error extracting initial page content: {content_error}")
            logger.error(f"Error extracting initial page content: {content_error}")
        
        # Try to get current URL
        try:
            cloudflare_results["currentUrl"] = await asyncio.wait_for(
                page.get_current_url(),
                timeout=3.0
            )
        except Exception as url_error:
            logger.error(f"Error getting current URL: {url_error}")
        
        # Give Cloudflare some time to run its checks, but not too long to avoid WebSocket issues
        logger.info("Waiting for Cloudflare checks to complete...")
        await asyncio.sleep(5)  # Shortened from 8 seconds
        
        # Take a screenshot for visual verification
        try:
            logger.info("Taking final screenshot")
            screenshot_base64 = await asyncio.wait_for(
                page.send_command("Page.captureScreenshot"),
                timeout=5.0
            )
            screenshot_data = screenshot_base64.get("data", "")
            if screenshot_data:
                os.makedirs("fingerprint_results", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"fingerprint_results/cloudflare_{timestamp}.png"
                with open(screenshot_path, "wb") as f:
                    import base64
                    f.write(base64.b64decode(screenshot_data))
                logger.info(f"Final screenshot saved to {screenshot_path}")
        except Exception as screenshot_error:
            logger.error(f"Failed to capture final screenshot: {screenshot_error}")
        
        # Get the page content to check for Cloudflare challenge page
        try:
            logger.info("Getting final page content")
            content_result = await asyncio.wait_for(
                page.send_command(
                    "Runtime.evaluate",
                    {
                        "expression": "document.documentElement.outerHTML",
                        "returnByValue": True,
                    }
                ),
                timeout=5.0
            )
            
            html_content = content_result.get("result", {}).get("value", "")
            
            # Save the HTML for analysis
            if html_content:
                html_file = f"fingerprint_results/cloudflare_html_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"HTML content saved to {html_file}")
                cloudflare_results["htmlCaptured"] = True
                
                # Check for Cloudflare challenge indicators
                cloudflare_indicators = [
                    "cf-browser-verification",
                    "cf_captcha_container",
                    "cf-challenge",
                    "cloudflare-challenge",
                    "security challenge",
                    "ray id",
                    "checking your browser",
                    "just a moment",
                    "clearance"
                ]
                
                # Check for indicators in the HTML content
                detected_indicators = [indicator for indicator in cloudflare_indicators 
                                      if indicator in html_content.lower()]
                                      
                challenge_detected = len(detected_indicators) > 0
                cloudflare_results["challengeDetected"] = challenge_detected
                cloudflare_results["botDetection"]["detected"] = challenge_detected
                cloudflare_results["botDetection"]["indicators"] = detected_indicators
                
                # Get the page title
                title = ""
                try:
                    title_result = await asyncio.wait_for(
                        page.evaluate("document.title"),
                        timeout=3.0
                    )
                    title = title_result if isinstance(title_result, str) else str(title_result)
                    cloudflare_results["title"] = title
                except Exception as title_error:
                    logger.error(f"Error getting page title: {title_error}")
                    # Try to extract title from HTML
                    if "<title>" in html_content and "</title>" in html_content:
                        title = html_content.split("<title>")[1].split("</title>")[0]
                        cloudflare_results["title"] = title
                
                # Cloudflare challenge pages often have specific titles
                challenge_title = any(phrase in title.lower() for phrase in ["cloudflare", "attention", "security check", "ddos", "just a moment"])
                if challenge_title:
                    cloudflare_results["challengeDetected"] = True
                    cloudflare_results["botDetection"]["detected"] = True
                
                # Get the current URL
                try:
                    current_url = await asyncio.wait_for(
                        page.get_current_url(),
                        timeout=3.0
                    )
                    cloudflare_results["currentUrl"] = current_url
                except Exception as url_error:
                    logger.error(f"Error getting current URL: {url_error}")
                
                # Analyze cookies for Cloudflare specific ones with timeout
                try:
                    cookies_result = await asyncio.wait_for(
                        page.send_command("Network.getAllCookies"),
                        timeout=3.0
                    )
                    cookies = cookies_result.get("cookies", [])
                    cf_cookies = [cookie for cookie in cookies if cookie.get("name", "").startswith("cf_")]
                    cloudflare_results["cfCookies"] = [cookie.get("name") for cookie in cf_cookies]
                except Exception as cookies_error:
                    logger.error(f"Error getting cookies: {cookies_error}")
                
                # Extract CloudFlare specific info using safer methods
                cf_info = {}
                try:
                    # Extract CF Ray from the HTML
                    if "cf-ray" in html_content.lower():
                        import re
                        ray_match = re.search(r'cf-ray="([^"]+)"', html_content)
                        if ray_match:
                            cf_info["cfRay"] = ray_match.group(1)
                    
                    # Check for challenge elements in the HTML
                    cf_info["challenge"] = "challenge-form" in html_content
                    cf_info["captcha"] = "cf-captcha-container" in html_content
                    cloudflare_results["cloudflareInfo"] = cf_info
                except Exception as cf_info_error:
                    logger.error(f"Error extracting CF info: {cf_info_error}")
                
                # Log the result for immediate feedback
                if cloudflare_results["botDetection"]["detected"]:
                    logger.warning("Cloudflare bot detection triggered")
                else:
                    logger.info("Cloudflare bot detection passed")
                
            else:
                logger.error("Failed to extract HTML content")
        except Exception as content_error:
            logger.error(f"Error extracting page content: {content_error}")
        
    except Exception as e:
        logger.error(f"Error during Cloudflare detection test: {e}")
    finally:
        # Save whatever results we've gathered so far
        results_file = save_results("cloudflare_basic", cloudflare_results)
        logger.info(f"Saved Cloudflare test results to {results_file}")
        
        # Close the page
        try:
            await page.close()
        except Exception as close_error:
            logger.error(f"Error closing page: {close_error}")

async def apply_advanced_stealth_patches(browser):
    """Apply advanced stealth patches based on Intoli research."""
    page = await browser.create_page()
    try:
        # Apply additional patches to bypass Cloudflare detection
        await page.send_command("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                (() => {
                    // Override the webdriver property more aggressively
                    const objectToInspect = window;
                    const navigatorKeys = Object.keys(Object.getPrototypeOf(navigator));
                    if (navigatorKeys.includes('webdriver')) {
                        // Delete the property from the prototype
                        delete Object.getPrototypeOf(navigator).webdriver;
                    }
                    
                    // Apply the Intoli technique: redefine the property
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => false,
                        configurable: true,
                        enumerable: true
                    });
                    
                    // Add more sophisticated techniques from Intoli's research
                    // Override the permissions API which is sometimes used for detection
                    const originalQuery = navigator.permissions.query;
                    navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                    
                    // Ensure plugins and language settings match real browsers
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => {
                            const plugins = [
                                {
                                    name: "Chrome PDF Plugin",
                                    description: "Portable Document Format",
                                    filename: "internal-pdf-viewer",
                                    length: 1,
                                    item: function() {},
                                    namedItem: function() {}
                                },
                                {
                                    name: "Chrome PDF Viewer",
                                    description: "",
                                    filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                                    length: 1,
                                    item: function() {},
                                    namedItem: function() {}
                                },
                                {
                                    name: "Native Client",
                                    description: "",
                                    filename: "internal-nacl-plugin",
                                    length: 2,
                                    item: function() {},
                                    namedItem: function() {}
                                }
                            ];
                            plugins.refresh = () => {};
                            plugins.item = idx => plugins[idx];
                            plugins.namedItem = name => plugins.find(p => p.name === name);
                            Object.defineProperty(plugins, 'length', { value: plugins.length });
                            return plugins;
                        },
                        enumerable: true,
                        configurable: true
                    });
                    
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en'],
                        enumerable: true,
                        configurable: true
                    });
                    
                    // Add functions to detect fingerprinting attempts
                    const monitorFingerprinting = () => {
                        // List of properties commonly used for fingerprinting
                        const fingerprintingProps = [
                            'userAgent', 'appVersion', 'platform', 'plugins', 'mimeTypes',
                            'doNotTrack', 'languages', 'deviceMemory', 'hardwareConcurrency',
                            'cpuClass', 'maxTouchPoints', 'webdriver'
                        ];
                        
                        // Monitor access to navigator properties
                        fingerprintingProps.forEach(prop => {
                            if (prop in navigator) {
                                const descriptor = Object.getOwnPropertyDescriptor(
                                    Object.getPrototypeOf(navigator), prop
                                ) || Object.getOwnPropertyDescriptor(navigator, prop);
                                
                                if (descriptor && descriptor.get) {
                                    const originalGetter = descriptor.get;
                                    descriptor.get = function() {
                                        // Could log fingerprinting attempts here
                                        return originalGetter.apply(this);
                                    };
                                    
                                    Object.defineProperty(
                                        navigator,
                                        prop,
                                        descriptor
                                    );
                                }
                            }
                        });
                    };
                    
                    // Run the monitor
                    monitorFingerprinting();
                })();
            """
        })
        
        # Additional patches to handle Cloudflare's specific checks
        await page.send_command("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                (() => {
                    // Overwriting other detection methods
                    
                    // Make sure Function.prototype.toString behaves normally
                    const originalFunctionToString = Function.prototype.toString;
                    const originalObjectGetOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
                    const originalObjectGetOwnPropertyDescriptors = Object.getOwnPropertyDescriptors;
                    
                    // Cloudflare often checks for native function modifications
                    // Ensure they look native by preserving the original toString
                    Object.getOwnPropertyDescriptor = function(obj, prop) {
                        const descriptor = originalObjectGetOwnPropertyDescriptor.apply(this, arguments);
                        if (descriptor && prop === 'toString' && obj === Function.prototype) {
                            return {
                                ...descriptor,
                                value: originalFunctionToString
                            };
                        }
                        return descriptor;
                    };
                    
                    Object.getOwnPropertyDescriptors = function(obj) {
                        const descriptors = originalObjectGetOwnPropertyDescriptors.apply(this, arguments);
                        if (obj === Function.prototype && descriptors.toString) {
                            descriptors.toString.value = originalFunctionToString;
                        }
                        return descriptors;
                    };
                    
                    // Cloudflare often checks browser features availability
                    // Ensure common browser APIs exist
                    if (!window.chrome) {
                        window.chrome = {
                            runtime: {},
                            loadTimes: function() {},
                            csi: function() {},
                            app: {}
                        };
                    }
                    
                    // Handle iframe access for Cloudflare checks
                    // Some CF challenges create hidden iframes to test browser behavior
                    const originalCreate = document.createElement;
                    document.createElement = function() {
                        const element = originalCreate.apply(this, arguments);
                        // If this is an iframe, ensure it behaves normally for Cloudflare checks
                        if (arguments[0].toLowerCase() === 'iframe') {
                            // Patch it after it's added to the document
                            setTimeout(() => {
                                try {
                                    if (element.contentWindow && element.contentWindow.navigator) {
                                        // Copy our patched navigator properties to the iframe
                                        const iframe = element.contentWindow;
                                        if (iframe.navigator) {
                                            Object.defineProperty(iframe.navigator, 'webdriver', {
                                                get: () => false,
                                                configurable: true,
                                                enumerable: true
                                            });
                                        }
                                    }
                                } catch (e) {
                                    // Ignore cross-origin errors
                                }
                            }, 0);
                        }
                        return element;
                    };
                    
                    // Intercept potential bot detection scripts
                    const originalFetch = window.fetch;
                    window.fetch = function() {
                        // We can't modify CF requests, but we're showing a pattern
                        // for monitoring network calls used for fingerprinting
                        return originalFetch.apply(this, arguments);
                    };
                    
                    // Add additional CF-specific evasion techniques
                    // Simulate user interaction timing
                    const getRandomDelay = () => Math.floor(Math.random() * 100) + 50;
                    
                    // Patch mousemove and other events to appear more human-like
                    const originalAddEventListener = EventTarget.prototype.addEventListener;
                    EventTarget.prototype.addEventListener = function(type) {
                        if (['mousemove', 'mousedown', 'mouseup', 'click'].includes(type)) {
                            // We could add random delays here if needed for specific CF sites
                        }
                        return originalAddEventListener.apply(this, arguments);
                    };
                })();
            """
        })
        
        logger.info("Applied advanced stealth patches based on Intoli research")
    except Exception as e:
        logger.error(f"Error applying advanced stealth patches: {e}")
    finally:
        await page.close() 

@pytest.mark.asyncio
@pytest.mark.xfail(reason="Specific Cloudflare challenge sites are expected to detect bots")
async def test_cloudflare_specific_challenge(advanced_stealth_browser):
    """Test against a specific Cloudflare challenge page designed to detect bots."""
    print("\n===== Starting Specific Cloudflare Challenge Test =====")
    logger.info("Starting specific Cloudflare challenge test")
    
    # Apply additional patches based on Intoli research
    print("Applying advanced stealth patches...")
    await apply_advanced_stealth_patches(advanced_stealth_browser)
    
    print("Creating page...")
    page = await advanced_stealth_browser.create_page()
    
    # Create results to gather data even if we encounter errors
    cloudflare_results = {
        "htmlCaptured": False,
        "challengeDetected": False,
        "title": "Unknown",
        "currentUrl": "Unknown",
        "cfCookies": [],
        "cloudflareInfo": {},
        "botDetection": {
            "detected": False,
            "indicators": []
        }
    }
    
    try:
        # Navigate to the specific Cloudflare challenge site
        print("Navigating to specific Cloudflare challenge site...")
        logger.info("Navigating to specific Cloudflare challenge site")
        await page.navigate("https://www.scrapingcourse.com/cloudflare-challenge")
        print("Navigation initiated.")
        
        # Wait a shorter time before taking initial data to avoid WebSocket issues
        print("Waiting 2 seconds...")
        await asyncio.sleep(2)
        print("Wait completed.")
        
        # Capture a screenshot early to avoid losing it due to WebSocket issues
        try:
            print("Taking early screenshot...")
            logger.info("Taking an early screenshot")
            screenshot_base64 = await asyncio.wait_for(
                page.send_command("Page.captureScreenshot"),
                timeout=5.0
            )
            screenshot_data = screenshot_base64.get("data", "")
            if screenshot_data:
                os.makedirs("fingerprint_results", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"fingerprint_results/cf_challenge_early_{timestamp}.png"
                with open(screenshot_path, "wb") as f:
                    import base64
                    f.write(base64.b64decode(screenshot_data))
                print(f"Early screenshot saved to {screenshot_path}")
                logger.info(f"Early screenshot saved to {screenshot_path}")
        except Exception as screenshot_error:
            print(f"❌ Failed to capture early screenshot: {screenshot_error}")
            logger.error(f"Failed to capture early screenshot: {screenshot_error}")
            
        # Get initial page content with timeout
        try:
            print("Getting initial page content...")
            logger.info("Getting initial page content")
            content_result = await asyncio.wait_for(
                page.send_command(
                    "Runtime.evaluate",
                    {
                        "expression": "document.documentElement.outerHTML",
                        "returnByValue": True,
                    }
                ),
                timeout=5.0
            )
            
            html_content = content_result.get("result", {}).get("value", "")
            print(f"HTML content length: {len(html_content)}")
            
            # Save the initial HTML content
            if html_content:
                html_file = f"fingerprint_results/cf_challenge_html_early_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"Initial HTML content saved to {html_file}")
                logger.info(f"Initial HTML content saved to {html_file}")
                cloudflare_results["htmlCaptured"] = True
                
                # Try to extract title from HTML
                if "<title>" in html_content and "</title>" in html_content:
                    cloudflare_results["title"] = html_content.split("<title>")[1].split("</title>")[0]
                    print(f"Page title: {cloudflare_results['title']}")
                    
                # Check for Cloudflare challenge indicators
                cloudflare_indicators = [
                    "cf-browser-verification",
                    "cf_captcha_container",
                    "cf-challenge",
                    "cloudflare-challenge",
                    "security challenge",
                    "ray id",
                    "checking your browser",
                    "just a moment",
                    "challenge-running",
                    "challenge-form",
                    "clearance"
                ]
                
                detected_indicators = [indicator for indicator in cloudflare_indicators 
                                      if indicator in html_content.lower()]
                
                challenge_detected = len(detected_indicators) > 0
                cloudflare_results["challengeDetected"] = challenge_detected
                cloudflare_results["botDetection"]["detected"] = challenge_detected
                cloudflare_results["botDetection"]["indicators"] = detected_indicators
                
                if detected_indicators:
                    print(f"⚠️ Detected Cloudflare indicators: {detected_indicators}")
                else:
                    print("✅ No Cloudflare challenge indicators detected")
                
                # Save early results in case we encounter errors later
                early_results_file = save_results("cf_challenge_early_data", cloudflare_results)
                print(f"Early results saved to {early_results_file}")
                logger.info(f"Saved early Cloudflare challenge results to {early_results_file}")
        except Exception as content_error:
            print(f"❌ Error extracting initial page content: {content_error}")
            logger.error(f"Error extracting initial page content: {content_error}")
        
        # Try to get current URL
        try:
            cloudflare_results["currentUrl"] = await asyncio.wait_for(
                page.get_current_url(),
                timeout=3.0
            )
            print(f"Current URL: {cloudflare_results['currentUrl']}")
        except Exception as url_error:
            print(f"❌ Error getting current URL: {url_error}")
            logger.error(f"Error getting current URL: {url_error}")
        
        # Wait longer for Cloudflare challenge to complete
        print("Waiting for Cloudflare challenge to complete...")
        logger.info("Waiting for Cloudflare challenge to complete...")
        await asyncio.sleep(10)  # Give more time for the challenge
        
        # Take a final screenshot
        try:
            print("Taking final screenshot...")
            logger.info("Taking final screenshot")
            screenshot_base64 = await asyncio.wait_for(
                page.send_command("Page.captureScreenshot"),
                timeout=5.0
            )
            screenshot_data = screenshot_base64.get("data", "")
            if screenshot_data:
                os.makedirs("fingerprint_results", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"fingerprint_results/cf_challenge_final_{timestamp}.png"
                with open(screenshot_path, "wb") as f:
                    import base64
                    f.write(base64.b64decode(screenshot_data))
                print(f"Final screenshot saved to {screenshot_path}")
                logger.info(f"Final screenshot saved to {screenshot_path}")
        except Exception as screenshot_error:
            print(f"❌ Failed to capture final screenshot: {screenshot_error}")
            logger.error(f"Failed to capture final screenshot: {screenshot_error}")
        
        # Get final page content to see if we passed the challenge
        try:
            print("Getting final page content...")
            logger.info("Getting final page content")
            content_result = await asyncio.wait_for(
                page.send_command(
                    "Runtime.evaluate",
                    {
                        "expression": "document.documentElement.outerHTML",
                        "returnByValue": True,
                    }
                ),
                timeout=5.0
            )
            
            html_content = content_result.get("result", {}).get("value", "")
            print(f"Final HTML content length: {len(html_content)}")
            
            # Save the final HTML content
            if html_content:
                html_file = f"fingerprint_results/cf_challenge_html_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"Final HTML content saved to {html_file}")
                logger.info(f"Final HTML content saved to {html_file}")
                
                # Check if we passed the challenge
                challenge_passed = "You've passed the Cloudflare challenge" in html_content
                if challenge_passed:
                    print("✅ PASSED: Successfully bypassed Cloudflare challenge!")
                    logger.info("Successfully bypassed Cloudflare challenge!")
                else:
                    print("❌ FAILED: Could not bypass Cloudflare challenge")
                    logger.warning("Could not bypass Cloudflare challenge")
                
                cloudflare_results["challengePassed"] = challenge_passed
                
                # Update challenge detection in the results
                cloudflare_indicators = [
                    "cf-browser-verification",
                    "cf_captcha_container",
                    "cf-challenge",
                    "cloudflare-challenge",
                    "security challenge",
                    "ray id",
                    "checking your browser",
                    "just a moment",
                    "challenge-running",
                    "challenge-form",
                    "clearance"
                ]
                
                detected_indicators = [indicator for indicator in cloudflare_indicators 
                                      if indicator in html_content.lower()]
                
                challenge_detected = len(detected_indicators) > 0
                cloudflare_results["challengeDetected"] = challenge_detected
                cloudflare_results["botDetection"]["detected"] = challenge_detected
                cloudflare_results["botDetection"]["indicators"] = detected_indicators
                
                # Extract more details from the page
                try:
                    # Check if we can identify what specific checks failed
                    detection_reasons = []
                    
                    # Common bot detection patterns
                    if "headless" in html_content.lower():
                        detection_reasons.append("headless browser detected")
                    
                    if "webdriver" in html_content.lower():
                        detection_reasons.append("webdriver detected")
                    
                    if "automation" in html_content.lower():
                        detection_reasons.append("automation detected")
                    
                    if "bot" in html_content.lower() and "detected" in html_content.lower():
                        detection_reasons.append("bot keyword detected")
                    
                    cloudflare_results["detectionReasons"] = detection_reasons
                    
                    if detection_reasons:
                        print(f"⚠️ Detected reasons for failure: {detection_reasons}")
                    
                except Exception as parse_error:
                    print(f"❌ Error parsing detection details: {parse_error}")
                    logger.error(f"Error parsing detection details: {parse_error}")
                
            else:
                print("❌ No HTML content in final page")
                logger.error("No HTML content in final page")
        
        except Exception as content_error:
            print(f"❌ Error extracting final page content: {content_error}")
            logger.error(f"Error extracting final page content: {content_error}")
        
    except Exception as e:
        print(f"❌ Error during Cloudflare challenge test: {e}")
        logger.error(f"Error during Cloudflare challenge test: {e}")
    finally:
        # Save whatever results we've gathered
        results_file = save_results("cf_challenge_results", cloudflare_results)
        print(f"Results saved to {results_file}")
        logger.info(f"Saved Cloudflare challenge results to {results_file}")
        
        # Close the page
        try:
            await page.close()
        except Exception as close_error:
            print(f"❌ Error closing page: {close_error}")
            logger.error(f"Error closing page: {close_error}") 