"""
Cloudflare Turnstile detection and handling.

This patch implements detection and handling for Cloudflare Turnstile challenges, which are 
anti-bot mechanisms used by Cloudflare-protected websites.
"""

import json
import logging
from typing import Dict, Optional

from cdp_browser.browser.stealth.patches.base import BasePatch
from . import register_patch

logger = logging.getLogger(__name__)


class CloudflareTurnstilePatch(BasePatch):
    """Patch to detect and handle Cloudflare Turnstile challenges."""

    NAME = "cloudflare_turnstile"
    DESCRIPTION = "Detects and handles Cloudflare Turnstile challenges"
    PRIORITY = 20  # Run before most other patches but after core functionality patches

    def __init__(self):
        super().__init__()
        self.turnstile_detected = False
        self.challenge_params = None
        self.callback_registered = False

    async def apply(self, browser, page):
        """Apply the Cloudflare Turnstile patch to the page.
        
        Args:
            browser: The browser instance
            page: The page to apply the patch to
        """
        # Step 1: Inject detection script
        await self._inject_detection_script(page)
        
        # Step 2: Set up message handler for turnstile detection
        await self._setup_message_handler(page)
        
        # Log that we've applied the patch
        logger.info("Applied Cloudflare Turnstile detection patch")
        return True
    
    def get_script(self):
        """
        Get the detection script for the patch.
        
        Returns:
            str: The JavaScript code for detection
        """
        return """
        (function() {
            // Store any console.clear calls to prevent them from hiding valuable info
            console.originalClear = console.clear;
            console.clear = function() {
                console.log('Console clear was intercepted');
                console.originalClear();
            };
            
            // Check for Turnstile Challenge Page indicators
            const checkForTurnstilePage = () => {
                // Check for _cf_chl_opt variable (Challenge Page indicator)
                if (typeof window._cf_chl_opt !== 'undefined') {
                    window._cdp_turnstile = {
                        type: 'challenge_page',
                        detected: true,
                        cf_chl_opt: JSON.parse(JSON.stringify(window._cf_chl_opt))
                    };
                    console.log('CDP-TURNSTILE-DETECTED:' + JSON.stringify(window._cdp_turnstile));
                }
                
                // Check for Ray ID (another Challenge Page indicator)
                const rayIdElement = document.querySelector('[class*="ray-id"]');
                if (rayIdElement) {
                    const rayId = rayIdElement.textContent.trim();
                    if (!window._cdp_turnstile) {
                        window._cdp_turnstile = { type: 'challenge_page', detected: true };
                    }
                    window._cdp_turnstile.rayId = rayId;
                    console.log('CDP-TURNSTILE-DETECTED:' + JSON.stringify(window._cdp_turnstile));
                }
            };
            
            // Initial check
            checkForTurnstilePage();
            
            // Set up interceptor for Turnstile widget
            const interceptTurnstile = () => {
                if (window.turnstile) {
                    // Save the original render function
                    if (!window.turnstile._original_render) {
                        window.turnstile._original_render = window.turnstile.render;
                    }
                    
                    // Override the render function
                    window.turnstile.render = function(container, params) {
                        window._cdp_turnstile = {
                            type: 'standalone',
                            detected: true,
                            params: {
                                sitekey: params.sitekey,
                                pageurl: window.location.href,
                                action: params.action || '',
                                cData: params.cData || '',
                                chlPageData: params.chlPageData || '',
                                theme: params.theme || 'light',
                                tabindex: params.tabindex || 0
                            }
                        };
                        
                        // Store the callback for later use
                        window._cdp_turnstile_callback = params.callback;
                        
                        console.log('CDP-TURNSTILE-DETECTED:' + JSON.stringify(window._cdp_turnstile));
                        
                        // Don't actually render to avoid being detected
                        return '_turnstile_dummy_widget_id';
                    };
                    
                    // Also intercept explicit method
                    if (!window.turnstile._original_getResponse) {
                        window.turnstile._original_getResponse = window.turnstile.getResponse;
                    }
                    
                    window.turnstile.getResponse = function(widgetId) {
                        if (window._cdp_turnstile && window._cdp_turnstile.solved) {
                            return window._cdp_turnstile.token;
                        }
                        return '';
                    };
                    
                    console.log('CDP-TURNSTILE-INTERCEPTED');
                }
            };
            
            // Check periodically for Turnstile
            const turnstileCheckInterval = setInterval(() => {
                if (window.turnstile) {
                    interceptTurnstile();
                    clearInterval(turnstileCheckInterval);
                }
            }, 50);
            
            // Listen for any new DOM changes that might indicate Turnstile
            const observer = new MutationObserver((mutations) => {
                for (const mutation of mutations) {
                    if (mutation.type === 'childList') {
                        const iframe = Array.from(mutation.addedNodes).find(
                            node => node.tagName === 'IFRAME' && 
                            (node.src || '').includes('challenges.cloudflare.com')
                        );
                        
                        if (iframe) {
                            if (!window._cdp_turnstile) {
                                window._cdp_turnstile = { 
                                    type: 'iframe', 
                                    detected: true,
                                    src: iframe.src
                                };
                                console.log('CDP-TURNSTILE-DETECTED:' + JSON.stringify(window._cdp_turnstile));
                            }
                        }
                    }
                }
                
                // Also check for Turnstile on each DOM change
                checkForTurnstilePage();
            });
            
            observer.observe(document.documentElement, {
                childList: true,
                subtree: true
            });
            
            // Set up solution handling
            window._cdp_apply_turnstile_solution = function(token) {
                if (!window._cdp_turnstile) {
                    console.error('No Turnstile challenge detected to solve');
                    return false;
                }
                
                try {
                    if (window._cdp_turnstile.type === 'standalone' && window._cdp_turnstile_callback) {
                        // For standalone Turnstile, call the callback with the token
                        window._cdp_turnstile_callback(token);
                        window._cdp_turnstile.solved = true;
                        window._cdp_turnstile.token = token;
                        console.log('CDP-TURNSTILE-SOLVED:standalone');
                        return true;
                    } else if (window._cdp_turnstile.type === 'challenge_page') {
                        // For challenge page, find the form input and submit
                        const input = document.querySelector('[name="cf-turnstile-response"]');
                        if (input) {
                            input.value = token;
                            
                            // Try to find and click the submit button
                            const form = input.closest('form');
                            if (form) {
                                form.submit();
                                window._cdp_turnstile.solved = true;
                                window._cdp_turnstile.token = token;
                                console.log('CDP-TURNSTILE-SOLVED:challenge_page');
                                return true;
                            }
                        }
                    }
                    
                    console.error('Could not apply Turnstile solution');
                    return false;
                } catch (error) {
                    console.error('Error applying Turnstile solution:', error);
                    return false;
                }
            };
        })();
        """

    async def _inject_detection_script(self, page):
        """Inject the detection script into the page.
        
        This script detects the presence of Cloudflare Turnstile and intercepts
        its parameters.
        """
        detection_script = self.get_script()
        await page.evaluateOnNewDocument(detection_script)

    async def _setup_message_handler(self, page):
        """Set up a handler for console messages to detect Turnstile presence."""
        # Function to handle console messages from the page
        async def handle_console_message(message):
            text = message.text
            if "CDP-TURNSTILE-DETECTED:" in text:
                # Extract the JSON data
                json_str = text.split("CDP-TURNSTILE-DETECTED:")[1]
                try:
                    data = json.loads(json_str)
                    self.turnstile_detected = True
                    self.challenge_params = data
                    logger.info(f"Detected Cloudflare Turnstile: {data['type']}")
                    
                    # If not already done, register the script to handle solutions
                    if not self.callback_registered:
                        await self._register_solution_handler(page)
                        self.callback_registered = True
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse Turnstile detection data: {json_str}")
            elif "CDP-TURNSTILE-INTERCEPTED" in text:
                logger.info("Successfully intercepted Turnstile render function")

        # Register the console message handler
        page.on("console", handle_console_message)

    async def _register_solution_handler(self, page):
        """Register a solution handler script that can apply tokens when available."""
        solution_script = """
        window._cdp_apply_turnstile_solution = function(token) {
            if (!window._cdp_turnstile) {
                console.error('No Turnstile challenge detected to solve');
                return false;
            }
            
            try {
                if (window._cdp_turnstile.type === 'standalone' && window._cdp_turnstile_callback) {
                    // For standalone Turnstile, call the callback with the token
                    window._cdp_turnstile_callback(token);
                    window._cdp_turnstile.solved = true;
                    window._cdp_turnstile.token = token;
                    console.log('CDP-TURNSTILE-SOLVED:standalone');
                    return true;
                } else if (window._cdp_turnstile.type === 'challenge_page') {
                    // For challenge page, find the form input and submit
                    const input = document.querySelector('[name="cf-turnstile-response"]');
                    if (input) {
                        input.value = token;
                        
                        // Try to find and click the submit button
                        const form = input.closest('form');
                        if (form) {
                            form.submit();
                            window._cdp_turnstile.solved = true;
                            window._cdp_turnstile.token = token;
                            console.log('CDP-TURNSTILE-SOLVED:challenge_page');
                            return true;
                        }
                    }
                }
                
                console.error('Could not apply Turnstile solution');
                return false;
            } catch (error) {
                console.error('Error applying Turnstile solution:', error);
                return false;
            }
        };
        """
        await page.evaluate(solution_script)

    async def apply_solution(self, page, token: str) -> bool:
        """Apply a solution token to the detected Turnstile challenge.
        
        Args:
            page: The page with the Turnstile challenge
            token: The solution token to apply
            
        Returns:
            bool: True if the solution was successfully applied
        """
        if not self.turnstile_detected:
            logger.warning("No Turnstile challenge detected to solve")
            return False
            
        result = await page.evaluate(f"window._cdp_apply_turnstile_solution('{token}')")
        return bool(result)

    async def is_detected(self, page) -> Dict:
        """Check if Turnstile is detected on the page.
        
        Args:
            page: The page to check
            
        Returns:
            Dict with detection status and information
        """
        result = await page.evaluate("""
        () => {
            return window._cdp_turnstile || { detected: false };
        }
        """)
        return result


def register():
    """Register the Cloudflare Turnstile patch with class-based approach."""
    return CloudflareTurnstilePatch()


# Register the script-based patch for compatibility with existing system
register_patch(
    name="cloudflare_turnstile_compat",
    description="Detects and handles Cloudflare Turnstile challenges (compatibility mode)",
    priority=20,  # Run before most other patches but after core functionality patches
    script=CloudflareTurnstilePatch().get_script()
) 