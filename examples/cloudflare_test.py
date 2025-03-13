"""
Cloudflare challenge test example for CDP Browser.

This example demonstrates how to test your stealth browser configuration against
Cloudflare's bot detection mechanisms. This is an advanced use case that shows
the limitations of automated browser navigation.
"""
import asyncio
import os
import sys
from datetime import datetime
import base64

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cdp_browser.browser.stealth import StealthBrowser
from cdp_browser.browser.stealth.profile import StealthProfile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Cloudflare challenge test example."""
    # Create a stealth profile with maximum protection
    profile = StealthProfile(
        level="maximum",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        window_size={"width": 1920, "height": 1080},
        languages=["en-US", "en"]
    )
    
    # Create the stealth browser
    async with StealthBrowser(profile=profile, port=9223) as browser:
        logger.info("Stealth browser connected")
        
        # Apply additional advanced stealth patches
        temp_page = await browser.create_page()
        
        try:
            # Apply additional patches to bypass CloudFlare detection
            await temp_page.send_command("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    (() => {
                        // Override the webdriver property more aggressively
                        const navigatorKeys = Object.keys(Object.getPrototypeOf(navigator));
                        if (navigatorKeys.includes('webdriver')) {
                            delete Object.getPrototypeOf(navigator).webdriver;
                        }
                        
                        // Apply advanced techniques: redefine the property
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => false,
                            configurable: true,
                            enumerable: true
                        });
                        
                        // Ensure chrome object exists (used for detection)
                        if (!window.chrome) {
                            window.chrome = {
                                runtime: {},
                                loadTimes: function() {},
                                csi: function() {},
                                app: {}
                            };
                        }
                        
                        // Add realistic plugins
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
                    })();
                """
            })
            
            logger.info("Applied advanced stealth patches")
        finally:
            await temp_page.close()
        
        # Create a page for testing Cloudflare
        page = await browser.create_page()
        logger.info("Test page created with stealth protections")
        
        try:
            # Navigate to a site with Cloudflare protection
            url = "https://www.scrapingcourse.com/cloudflare-challenge"
            logger.info(f"Navigating to Cloudflare protected site: {url}")
            await page.navigate(url)
            
            # Take an early screenshot to capture challenge page
            logger.info("Taking early screenshot...")
            try:
                os.makedirs("cloudflare_results", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                screenshot_base64 = await page.send_command("Page.captureScreenshot")
                screenshot_data = screenshot_base64.get("data", "")
                
                if screenshot_data:
                    screenshot_path = f"cloudflare_results/cf_early_{timestamp}.png"
                    with open(screenshot_path, "wb") as f:
                        f.write(base64.b64decode(screenshot_data))
                    logger.info(f"Early screenshot saved to {screenshot_path}")
            except Exception as e:
                logger.error(f"Failed to capture early screenshot: {e}")
            
            # Wait a bit for the challenge to possibly complete
            logger.info("Waiting for Cloudflare challenge...")
            await asyncio.sleep(10)
            
            # Take another screenshot to see if anything changed
            logger.info("Taking final screenshot...")
            try:
                screenshot_base64 = await page.send_command("Page.captureScreenshot")
                screenshot_data = screenshot_base64.get("data", "")
                
                if screenshot_data:
                    screenshot_path = f"cloudflare_results/cf_final_{timestamp}.png"
                    with open(screenshot_path, "wb") as f:
                        f.write(base64.b64decode(screenshot_data))
                    logger.info(f"Final screenshot saved to {screenshot_path}")
            except Exception as e:
                logger.error(f"Failed to capture final screenshot: {e}")
            
            # Get the page content
            logger.info("Getting page content...")
            try:
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
                    html_file = f"cloudflare_results/cf_html_{timestamp}.html"
                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    logger.info(f"HTML content saved to {html_file}")
                    
                    # Check for Cloudflare challenge indicators
                    challenge_indicators = [
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
                    
                    detected = [indicator for indicator in challenge_indicators 
                               if indicator in html_content.lower()]
                    
                    if detected:
                        logger.warning(f"⚠️ Cloudflare challenge detected: {detected}")
                        logger.warning("Bot detection was triggered - bypassing Cloudflare requires additional measures")
                    else:
                        logger.info("✅ No Cloudflare challenge detected - stealth mode working!")
                    
                    # Check page title
                    title = "Unknown"
                    if "<title>" in html_content and "</title>" in html_content:
                        title = html_content.split("<title>")[1].split("</title>")[0]
                        logger.info(f"Page title: {title}")
                    
                    # Determine if we successfully bypassed the challenge
                    if title == "Just a moment..." or any(i in html_content.lower() for i in challenge_indicators):
                        logger.warning("❌ Failed to bypass Cloudflare challenge")
                    else:
                        logger.info("✅ Successfully bypassed Cloudflare challenge!")
                
            except Exception as e:
                logger.error(f"Error getting page content: {e}")
            
            # Get current URL to see if we were redirected
            try:
                current_url = await page.get_current_url()
                logger.info(f"Current URL: {current_url}")
            except Exception as e:
                logger.error(f"Error getting current URL: {e}")
        
        finally:
            # Close the page
            await page.close()
            logger.info("Page closed")

if __name__ == "__main__":
    # Run the example
    asyncio.run(main()) 