"""
Enhanced tests for Cloudflare Turnstile detection and handling with detailed status reporting.
"""

import asyncio
import logging
import os
import json
from datetime import datetime
import pytest
import base64
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import shared test utilities
from tests.test_stealth_fingerprint import (
    advanced_stealth_browser,  # Import the browser fixture
    apply_advanced_stealth_patches,  # Import the patch function
    save_results  # Import the results saving function
)

# Import the Cloudflare Turnstile patch class directly
from cdp_browser.browser.stealth.patches.cloudflare_turnstile import CloudflareTurnstilePatch

logger.info("Cloudflare enhanced test module loaded")

@pytest.mark.xfail(reason="Specific Cloudflare challenge sites are expected to detect bots")
@pytest.mark.asyncio
async def test_cloudflare_specific_challenge(advanced_stealth_browser):
    """Test against a specific Cloudflare challenge page designed to detect bots.
    
    Success criteria:
    1. Successfully detect Cloudflare Turnstile challenge
    2. Successfully solve the challenge using human-like interaction
    3. Navigate past the challenge page to the target content
    """
    print("\n========================================================================")
    print("📊 CLOUDFLARE TURNSTILE CHALLENGE TEST")
    print("========================================================================")
    logger.info("Starting specific Cloudflare challenge test")
    
    # Create results directory if it doesn't exist
    os.makedirs("test_results", exist_ok=True)
    
    # Initialize test metrics to track progress
    test_metrics = {
        "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stages": {
            "setup": {"status": "pending", "details": []},
            "navigation": {"status": "pending", "details": []},
            "detection": {"status": "pending", "details": []},
            "solving": {"status": "pending", "details": []},
            "verification": {"status": "pending", "details": []}
        },
        "detailed_results": {},
        "success": False,
        "failure_reason": None
    }
    
    # Add a helper function to update metrics
    def update_metrics(stage, status, message):
        test_metrics["stages"][stage]["status"] = status
        test_metrics["stages"][stage]["details"].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": message
        })
        prefix = {
            "success": "✅",
            "failed": "❌",
            "warning": "⚠️",
            "pending": "🔄",
            "info": "ℹ️",
        }.get(status, "ℹ️")
        print(f"{prefix} [{stage.upper()}] {message}")
        logger.info(f"[{stage}] {message}")
    
    # Setup stage
    update_metrics("setup", "info", "Setting up test environment")
    
    # Apply additional patches based on Intoli research
    update_metrics("setup", "info", "Applying advanced stealth patches...")
    await apply_advanced_stealth_patches(advanced_stealth_browser)
    update_metrics("setup", "success", "Advanced stealth patches applied")
    
    # Create a Cloudflare Turnstile patch instance for detection and solving
    update_metrics("setup", "info", "Creating Cloudflare Turnstile patch instance...")
    cf_patch = CloudflareTurnstilePatch()
    update_metrics("setup", "success", "Cloudflare Turnstile patch created")
    
    update_metrics("setup", "info", "Creating browser page...")
    page = await advanced_stealth_browser.create_page()
    update_metrics("setup", "success", "Browser page created")
    
    # Apply the Cloudflare Turnstile detection script manually
    update_metrics("setup", "info", "Applying Cloudflare Turnstile detection script...")
    detection_script = cf_patch.get_script()
    
    # Add the script to evaluate on new document
    await page.send_command("Page.addScriptToEvaluateOnNewDocument", {
        "source": detection_script
    })
    
    # Also evaluate immediately in current context
    await page.evaluate(detection_script)
    
    # Set up console message handler to detect Turnstile
    update_metrics("setup", "info", "Setting up console message handler...")
    
    # We'll use a simple approach to check for Turnstile detection
    await page.evaluate("""
    window.addEventListener('message', function(event) {
        if (event.data && event.data.type === 'cf-turnstile-callback') {
            console.log('CDP-TURNSTILE-DETECTED:' + JSON.stringify(event.data));
        }
    });
    """)
    
    update_metrics("setup", "success", "Cloudflare Turnstile detection setup complete")
    
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
        },
        "automaticSolvingAttempted": False,
        "automaticSolvingSuccess": False
    }
    
    try:
        # Navigation stage
        update_metrics("navigation", "info", "Navigating to Cloudflare challenge site...")
        test_url = "https://www.scrapingcourse.com/cloudflare-challenge"
        await page.navigate(test_url)
        update_metrics("navigation", "success", f"Navigation initiated to {test_url}")
        
        # Wait time for initial page load
        update_metrics("navigation", "info", "Waiting for initial page load (2s)...")
        await asyncio.sleep(2)
        update_metrics("navigation", "success", "Initial wait completed")
        
        # Take an early screenshot to document the challenge page
        try:
            update_metrics("navigation", "info", "Taking initial screenshot of challenge page...")
            screenshot_base64 = await asyncio.wait_for(
                page.send_command("Page.captureScreenshot"),
                timeout=5.0
            )
            screenshot_data = screenshot_base64.get("data", "")
            if screenshot_data:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"test_results/cf_challenge_initial_{timestamp}.png"
                with open(screenshot_path, "wb") as f:
                    f.write(base64.b64decode(screenshot_data))
                update_metrics("navigation", "success", f"Initial screenshot saved to {screenshot_path}")
                test_metrics["detailed_results"]["initial_screenshot"] = screenshot_path
            else:
                update_metrics("navigation", "warning", "No screenshot data received")
        except Exception as screenshot_error:
            update_metrics("navigation", "failed", f"Failed to capture initial screenshot: {screenshot_error}")
            
        # Get the page content to analyze
        try:
            update_metrics("detection", "info", "Getting page content for analysis...")
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
            content_length = len(html_content)
            update_metrics("detection", "success", f"Retrieved page content ({content_length} bytes)")
            
            # Save the initial HTML content for analysis
            if html_content:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                html_file = f"test_results/cf_challenge_initial_{timestamp}.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                update_metrics("detection", "success", f"Initial HTML saved to {html_file}")
                test_metrics["detailed_results"]["initial_html"] = html_file
                cloudflare_results["htmlCaptured"] = True
                
                # Extract page title
                if "<title>" in html_content and "</title>" in html_content:
                    cloudflare_results["title"] = html_content.split("<title>")[1].split("</title>")[0]
                    update_metrics("detection", "info", f"Page title: {cloudflare_results['title']}")
                    test_metrics["detailed_results"]["page_title"] = cloudflare_results["title"]
                
                # Check for Cloudflare challenge indicators
                cloudflare_indicators = [
                    "cf-browser-verification",
                    "cf_captcha_container",
                    "cf-challenge",
                    "cloudflare-challenge",
                    "cf-turnstile",
                    "security challenge",
                    "ray id",
                    "checking your browser",
                    "just a moment",
                    "challenge-running",
                    "challenge-form",
                    "clearance",
                    "turnstile_"
                ]
                
                detected_indicators = [indicator for indicator in cloudflare_indicators 
                                      if indicator in html_content.lower()]
                
                challenge_detected = len(detected_indicators) > 0
                cloudflare_results["challengeDetected"] = challenge_detected
                cloudflare_results["botDetection"]["detected"] = challenge_detected
                cloudflare_results["botDetection"]["indicators"] = detected_indicators
                
                if detected_indicators:
                    update_metrics("detection", "success", f"Cloudflare challenge detected! Indicators: {detected_indicators}")
                    test_metrics["detailed_results"]["challenge_indicators"] = detected_indicators
                else:
                    update_metrics("detection", "warning", "No Cloudflare challenge indicators detected in the HTML")
            else:
                update_metrics("detection", "failed", "No HTML content received")
                test_metrics["failure_reason"] = "Failed to retrieve page HTML"
        except Exception as content_error:
            update_metrics("detection", "failed", f"Error retrieving page content: {content_error}")
            test_metrics["failure_reason"] = f"Content retrieval error: {str(content_error)}"
        
        # Get the current URL to check for redirects
        try:
            current_url = await asyncio.wait_for(
                page.get_current_url(),
                timeout=3.0
            )
            cloudflare_results["currentUrl"] = current_url
            update_metrics("detection", "info", f"Current URL: {current_url}")
            test_metrics["detailed_results"]["current_url"] = current_url
        except Exception as url_error:
            update_metrics("detection", "warning", f"Error getting current URL: {url_error}")
        
        # Automatic solution process
        turnstile_detected = False
        solution_attempted = False
        solution_succeeded = False
        
        if cloudflare_results["challengeDetected"]:
            update_metrics("solving", "info", "Starting automatic Turnstile detection and solving...")
            cloudflare_results["automaticSolvingAttempted"] = True
            
            try:
                # Check if Turnstile is detected by our patch
                update_metrics("solving", "info", "Checking for Turnstile widget on page...")
                
                # Use our own detection logic since we can't use the patch's is_detected method directly
                detection_result = await page.evaluate("""
                () => {
                    // Look for Turnstile elements
                    const turnstileFrames = document.querySelectorAll('iframe[src*="challenges.cloudflare.com"]');
                    const turnstileWidgets = document.querySelectorAll('[class*="turnstile"], [id*="turnstile"], [data-sitekey]');
                    
                    if (turnstileFrames.length > 0 || turnstileWidgets.length > 0) {
                        // Get position of the first turnstile element for interaction
                        let position = null;
                        const element = turnstileFrames[0] || turnstileWidgets[0];
                        
                        if (element) {
                            const rect = element.getBoundingClientRect();
                            position = {
                                centerX: rect.left + rect.width / 2,
                                centerY: rect.top + rect.height / 2,
                                width: rect.width,
                                height: rect.height,
                                left: rect.left,
                                top: rect.top
                            };
                        }
                        
                        return {
                            detected: true,
                            type: 'turnstile_widget',
                            frames: turnstileFrames.length,
                            widgets: turnstileWidgets.length,
                            position: position
                        };
                    }
                    
                    // Check for challenge page indicators
                    if (window._cf_chl_opt || document.querySelector('[class*="ray-id"]')) {
                        return {
                            detected: true,
                            type: 'challenge_page'
                        };
                    }
                    
                    return { detected: false };
                }
                """)
                
                if detection_result.get("detected", False):
                    turnstile_detected = True
                    update_metrics("solving", "success", f"Turnstile detected on page! Type: {detection_result.get('type', 'unknown')}")
                    test_metrics["detailed_results"]["turnstile_detection"] = detection_result
                    
                    # Check if we have position data for interaction
                    if "position" in detection_result:
                        position_info = detection_result.get("position", {})
                        update_metrics("solving", "success", f"Position data found: centerX={position_info.get('centerX')}, centerY={position_info.get('centerY')}")
                        
                        # Attempt to solve using human-like interaction
                        update_metrics("solving", "info", "Attempting to solve using human-like interaction...")
                        solution_attempted = True
                        
                        # Record detailed timing for debugging
                        solve_start = datetime.now()
                        
                        # Simulate human-like interaction with the challenge
                        # 1. Move mouse to the center of the widget
                        await page.send_command("Input.dispatchMouseEvent", {
                            "type": "mouseMoved",
                            "x": position_info.get("centerX"),
                            "y": position_info.get("centerY")
                        })
                        
                        # 2. Wait a bit like a human would
                        await asyncio.sleep(0.5)
                        
                        # 3. Click on the widget
                        await page.send_command("Input.dispatchMouseEvent", {
                            "type": "mousePressed",
                            "button": "left",
                            "x": position_info.get("centerX"),
                            "y": position_info.get("centerY"),
                            "clickCount": 1
                        })
                        
                        await page.send_command("Input.dispatchMouseEvent", {
                            "type": "mouseReleased",
                            "button": "left",
                            "x": position_info.get("centerX"),
                            "y": position_info.get("centerY"),
                            "clickCount": 1
                        })
                        
                        # 4. Wait for the challenge to process
                        await asyncio.sleep(2)
                        
                        # Check if the challenge was solved
                        success_check = await page.evaluate("""
                        () => {
                            // Check if the challenge is still visible
                            const turnstileElements = document.querySelectorAll('iframe[src*="challenges.cloudflare.com"], [class*="turnstile"], [id*="turnstile"]');
                            return {
                                success: turnstileElements.length === 0 || 
                                        document.body.innerText.includes("You've passed") ||
                                        !document.body.innerText.includes("Checking your browser") ||
                                        document.querySelector('[data-success="true"]') !== null
                            };
                        }
                        """)
                        
                        solve_duration = (datetime.now() - solve_start).total_seconds()
                        success = success_check.get("success", False)
                        
                        if success:
                            solution_succeeded = True
                            update_metrics("solving", "success", f"Automatic Cloudflare challenge solving succeeded in {solve_duration:.2f}s!")
                            cloudflare_results["automaticSolvingSuccess"] = True
                        else:
                            update_metrics("solving", "failed", f"Automatic Cloudflare challenge solving failed after {solve_duration:.2f}s")
                    else:
                        update_metrics("solving", "warning", "No position data available for solving - can't interact with challenge")
                else:
                    update_metrics("solving", "warning", "Turnstile not detected by our detection script - check if challenge page format has changed")
            except Exception as solve_error:
                update_metrics("solving", "failed", f"Error during automatic solving: {solve_error}")
                test_metrics["failure_reason"] = f"Solving error: {str(solve_error)}"
        
        # Track key metrics for the solution phase
        test_metrics["detailed_results"]["turnstile_detected"] = turnstile_detected
        test_metrics["detailed_results"]["solution_attempted"] = solution_attempted
        test_metrics["detailed_results"]["solution_succeeded"] = solution_succeeded
        
        # Wait for challenge to complete (if auto-solving or timeout)
        wait_time = 10  # seconds
        update_metrics("verification", "info", f"Waiting {wait_time}s for Cloudflare challenge to complete...")
        await asyncio.sleep(wait_time)
        
        # Take a final screenshot to document results
        try:
            update_metrics("verification", "info", "Taking final screenshot...")
            screenshot_base64 = await asyncio.wait_for(
                page.send_command("Page.captureScreenshot"),
                timeout=5.0
            )
            screenshot_data = screenshot_base64.get("data", "")
            if screenshot_data:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"test_results/cf_challenge_final_{timestamp}.png"
                with open(screenshot_path, "wb") as f:
                    f.write(base64.b64decode(screenshot_data))
                update_metrics("verification", "success", f"Final screenshot saved to {screenshot_path}")
                test_metrics["detailed_results"]["final_screenshot"] = screenshot_path
            else:
                update_metrics("verification", "warning", "No final screenshot data received")
        except Exception as screenshot_error:
            update_metrics("verification", "failed", f"Failed to capture final screenshot: {screenshot_error}")
        
        # Get final page content to check if challenge was passed
        try:
            update_metrics("verification", "info", "Getting final page content...")
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
            content_length = len(html_content)
            update_metrics("verification", "success", f"Retrieved final page content ({content_length} bytes)")
            
            # Save the final HTML content for analysis
            if html_content:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                html_file = f"test_results/cf_challenge_final_{timestamp}.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                update_metrics("verification", "success", f"Final HTML saved to {html_file}")
                test_metrics["detailed_results"]["final_html"] = html_file
                
                # Explicit success check: does the page contain the target content?
                challenge_passed = "You've passed the Cloudflare challenge" in html_content
                cloudflare_results["challengePassed"] = challenge_passed
                
                # Second check: are there still challenge indicators?
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
                
                still_has_indicators = any(indicator in html_content.lower() for indicator in cloudflare_indicators)
                
                # Get current URL to check if we moved past the challenge
                try:
                    final_url = await asyncio.wait_for(page.get_current_url(), timeout=3.0)
                    url_changed = final_url != test_url and final_url != cloudflare_results["currentUrl"]
                    update_metrics("verification", "info", f"Final URL: {final_url} (changed: {url_changed})")
                    test_metrics["detailed_results"]["final_url"] = final_url
                    test_metrics["detailed_results"]["url_changed"] = url_changed
                except Exception as url_error:
                    update_metrics("verification", "warning", f"Error getting final URL: {url_error}")
                    url_changed = False
                
                # Determine overall success
                success = challenge_passed or (solution_succeeded and not still_has_indicators) or url_changed
                test_metrics["success"] = success
                
                # Log detailed verification results
                if challenge_passed:
                    update_metrics("verification", "success", "SUCCESS: Found 'You've passed the Cloudflare challenge' in content!")
                elif solution_succeeded and not still_has_indicators:
                    update_metrics("verification", "success", "SUCCESS: Solution succeeded and challenge indicators disappeared!")
                elif url_changed:
                    update_metrics("verification", "success", "SUCCESS: URL changed after challenge, likely passed!")
                else:
                    update_metrics("verification", "failed", "FAILED: Could not verify successful challenge passage")
                    
                    # Detailed failure analysis
                    if still_has_indicators:
                        update_metrics("verification", "info", "Still showing challenge indicators")
                    
                    # Check for specific failure indicators
                    detection_reasons = []
                    if "headless" in html_content.lower():
                        detection_reasons.append("headless browser detected")
                    if "webdriver" in html_content.lower():
                        detection_reasons.append("webdriver detected")
                    if "automation" in html_content.lower():
                        detection_reasons.append("automation detected")
                    if "bot" in html_content.lower() and "detected" in html_content.lower():
                        detection_reasons.append("bot keyword detected")
                    
                    if detection_reasons:
                        update_metrics("verification", "info", f"Possible failure reasons: {detection_reasons}")
                        test_metrics["detailed_results"]["detection_reasons"] = detection_reasons
                
            else:
                update_metrics("verification", "failed", "No HTML content in final page")
                test_metrics["failure_reason"] = "No final HTML content"
        
        except Exception as content_error:
            update_metrics("verification", "failed", f"Error extracting final page content: {content_error}")
            test_metrics["failure_reason"] = f"Final content error: {str(content_error)}"
        
    except Exception as e:
        update_metrics("verification", "failed", f"Error during test: {e}")
        test_metrics["failure_reason"] = f"Test error: {str(e)}"
    finally:
        # Save test metrics for analysis
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_file = f"test_results/cf_challenge_metrics_{timestamp}.json"
        with open(metrics_file, 'w', encoding='utf-8') as f:
            # Add end time
            test_metrics["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Add duration
            start_time = datetime.strptime(test_metrics["start_time"], "%Y-%m-%d %H:%M:%S")
            end_time = datetime.strptime(test_metrics["end_time"], "%Y-%m-%d %H:%M:%S")
            duration_seconds = (end_time - start_time).total_seconds()
            test_metrics["duration_seconds"] = duration_seconds
            
            json.dump(test_metrics, f, indent=2)
        
        update_metrics("verification", "info", f"Test metrics saved to {metrics_file}")
        
        # Print summary
        print("\n========================================================================")
        print(f"📋 TEST SUMMARY - Duration: {duration_seconds:.2f}s")
        print("========================================================================")
        
        for stage, data in test_metrics["stages"].items():
            status_icon = {
                "success": "✅",
                "failed": "❌",
                "warning": "⚠️",
                "pending": "⏸️",
                "info": "ℹ️",
            }.get(data["status"], "ℹ️")
            print(f"{status_icon} {stage.upper()}: {data['status'].upper()}")
        
        print("------------------------------------------------------------------------")
        if test_metrics["success"]:
            print("✅ OVERALL RESULT: PASSED - Successfully handled Cloudflare challenge!")
        else:
            print(f"❌ OVERALL RESULT: FAILED - {test_metrics.get('failure_reason', 'Unknown reason')}")
        print("========================================================================")
        
        # Save detailed results for later analysis
        results_file = save_results("cf_challenge_detailed_results", cloudflare_results)
        update_metrics("verification", "info", f"Detailed results saved to {results_file}")
        
        # Close the page
        try:
            await page.close()
            update_metrics("verification", "info", "Page closed")
        except Exception as close_error:
            update_metrics("verification", "warning", f"Error closing page: {close_error}")
        
        # If success is True, this test should not be marked as xfail anymore
        if test_metrics["success"]:
            pytest.skip("Test passed! Remove the xfail marker to make it part of the regular test suite.") 