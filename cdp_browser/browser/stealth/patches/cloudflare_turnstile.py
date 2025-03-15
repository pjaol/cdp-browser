"""
Cloudflare Turnstile detection and handling.

This patch implements detection and handling for Cloudflare Turnstile challenges, which are 
anti-bot mechanisms used by Cloudflare-protected websites.
"""

import json
import logging
import random
import asyncio
import math
from typing import Dict, Optional, Tuple, List

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
            
            // Detect Turnstile checkbox challenges directly
            const findTurnstileCheckbox = () => {
                // Common selectors for Turnstile checkbox
                const selectors = [
                    'iframe[src*="challenges.cloudflare.com"]',
                    'iframe[src*="turnstile"]',
                    'iframe.cf-turnstile',
                    'div[class*="turnstile"]',
                    'div[data-sitekey]'
                ];
                
                for (const selector of selectors) {
                    const element = document.querySelector(selector);
                    if (element) {
                        // Get iframe position and size if found
                        if (element.tagName === 'IFRAME') {
                            const rect = element.getBoundingClientRect();
                            if (!window._cdp_turnstile) {
                                window._cdp_turnstile = { 
                                    type: 'checkbox', 
                                    detected: true,
                                    frameId: element.id || '',
                                    position: {
                                        x: rect.left,
                                        y: rect.top,
                                        width: rect.width,
                                        height: rect.height,
                                        centerX: rect.left + rect.width / 2,
                                        centerY: rect.top + rect.height / 2
                                    }
                                };
                                console.log('CDP-TURNSTILE-DETECTED:' + JSON.stringify(window._cdp_turnstile));
                            }
                            return true;
                        } 
                        
                        // For non-iframe elements
                        const rect = element.getBoundingClientRect();
                        if (!window._cdp_turnstile) {
                            window._cdp_turnstile = { 
                                type: 'checkbox', 
                                detected: true,
                                elementId: element.id || '',
                                position: {
                                    x: rect.left,
                                    y: rect.top,
                                    width: rect.width,
                                    height: rect.height,
                                    centerX: rect.left + rect.width / 2,
                                    centerY: rect.top + rect.height / 2
                                }
                            };
                            console.log('CDP-TURNSTILE-DETECTED:' + JSON.stringify(window._cdp_turnstile));
                        }
                        return true;
                    }
                }
                return false;
            };
            
            // Look for Turnstile checkboxes initially
            findTurnstileCheckbox();
            
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
                                const rect = iframe.getBoundingClientRect();
                                window._cdp_turnstile = { 
                                    type: 'iframe', 
                                    detected: true,
                                    src: iframe.src,
                                    position: {
                                        x: rect.left,
                                        y: rect.top,
                                        width: rect.width,
                                        height: rect.height,
                                        centerX: rect.left + rect.width / 2,
                                        centerY: rect.top + rect.height / 2
                                    }
                                };
                                console.log('CDP-TURNSTILE-DETECTED:' + JSON.stringify(window._cdp_turnstile));
                            }
                        } else {
                            // Check for non-iframe Turnstile components
                            findTurnstileCheckbox();
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
                        
                    # Auto-solve if we have position data
                    if 'position' in data and data.get('type') in ['checkbox', 'iframe']:
                        logger.info("Attempting auto-solve for Turnstile checkbox")
                        await self.solve_turnstile_challenge(page, data)
                        
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse Turnstile detection data: {json_str}")
            elif "CDP-TURNSTILE-INTERCEPTED" in text:
                logger.info("Successfully intercepted Turnstile render function")
            elif "CDP-TURNSTILE-SOLVED:" in text:
                logger.info(f"Cloudflare Turnstile solved: {text.split('CDP-TURNSTILE-SOLVED:')[1]}")

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

    async def solve_turnstile_challenge(self, page, challenge_data: Dict) -> bool:
        """Attempt to solve a Turnstile challenge using human-like interactions.
        
        Args:
            page: The page with the Turnstile challenge
            challenge_data: The detected challenge parameters
            
        Returns:
            bool: True if the solution was successful, False otherwise
        """
        logger.info(f"Attempting to solve Turnstile challenge type: {challenge_data.get('type')}")
        
        if 'position' not in challenge_data:
            logger.warning("No position data available for Turnstile challenge")
            return False
        
        position = challenge_data['position']
        center_x = position.get('centerX', position.get('x', 0) + position.get('width', 0) / 2)
        center_y = position.get('centerY', position.get('y', 0) + position.get('height', 0) / 2)
        
        # Simulate natural mouse movement
        try:
            await self._move_mouse_like_human(page, center_x, center_y)
            
            # Slight pause before clicking (natural human behavior)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Click the checkbox
            await page.mouse.click(center_x, center_y)
            
            logger.info(f"Clicked on Turnstile challenge at ({center_x}, {center_y})")
            
            # Wait for any animations or state changes
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # Check if our click worked by looking for success indicators
            is_solved = await self._check_turnstile_solved(page)
            
            if is_solved:
                logger.info("Successfully solved Turnstile challenge with human-like interaction")
                return True
            else:
                logger.warning("Turnstile challenge not solved after click, may require additional interaction")
                return False
                
        except Exception as e:
            logger.error(f"Error while solving Turnstile challenge: {e}")
            return False

    async def _move_mouse_like_human(self, page, target_x: float, target_y: float, steps: int = None):
        """Move the mouse in a human-like pattern to the target coordinates.
        
        Args:
            page: The page to interact with
            target_x: The x coordinate to move to
            target_y: The y coordinate to move to
            steps: Number of steps (if None, calculated based on distance)
        """
        # Get current mouse position
        current_position = await page.evaluate("""
        () => {
            return {x: 0, y: 0}; // Default to (0,0) if we can't get current position
        }
        """)
        
        start_x = current_position.get('x', 0)
        start_y = current_position.get('y', 0)
        
        # Calculate distance
        distance = ((target_x - start_x) ** 2 + (target_y - start_y) ** 2) ** 0.5
        
        # If steps not provided, calculate based on distance
        if steps is None:
            steps = max(10, min(25, int(distance / 10)))
        
        # Generate a slightly curved path with varying speeds
        points = self._generate_human_mouse_path(start_x, start_y, target_x, target_y, steps)
        
        # Move through the path
        for i, (x, y, delay) in enumerate(points):
            await page.mouse.move(x, y)
            
            # Variable delay based on position in the path (slower at start and end)
            if i < len(points) - 1:
                await asyncio.sleep(delay)

    def _generate_human_mouse_path(self, start_x: float, start_y: float, 
                                   end_x: float, end_y: float, 
                                   steps: int) -> List[Tuple[float, float, float]]:
        """Generate a mouse path that mimics human movement.
        
        Args:
            start_x: Starting x coordinate
            start_y: Starting y coordinate
            end_x: Ending x coordinate
            end_y: Ending y coordinate
            steps: Number of points in the path
            
        Returns:
            List of (x, y, delay) tuples representing points along the path
        """
        path = []
        
        # Add some randomness to the path (slight curve)
        # Bezier curve implementation would be best, but this is a simple approximation
        for i in range(steps + 1):
            # Progress along the path (0.0 to 1.0)
            t = i / steps
            
            # Ease-in-out timing function (slower at start and end)
            # This makes the movement more natural
            if t < 0.5:
                progress = 2 * t * t
            else:
                progress = -1 + (4 - 2 * t) * t
                
            # Linear interpolation with slight random deviation
            deviation_x = random.uniform(-5, 5) * math.sin(t * math.pi)
            deviation_y = random.uniform(-5, 5) * math.sin(t * math.pi)
            
            # Calculate point on path
            x = start_x + (end_x - start_x) * progress + deviation_x
            y = start_y + (end_y - start_y) * progress + deviation_y
            
            # Variable speed (slower at beginning and end)
            if i < steps / 4 or i > steps * 3 / 4:
                delay = random.uniform(0.01, 0.03)  # Slower
            else:
                delay = random.uniform(0.005, 0.01)  # Faster
                
            path.append((x, y, delay))
            
        return path

    async def _check_turnstile_solved(self, page) -> bool:
        """Check if the Turnstile challenge has been solved.
        
        Args:
            page: The page with the Turnstile challenge
            
        Returns:
            bool: True if solved, False otherwise
        """
        # Different ways to check if the challenge was solved
        result = await page.evaluate("""
        () => {
            // Check if we have a solved flag in our detection
            if (window._cdp_turnstile && window._cdp_turnstile.solved) {
                return {solved: true, method: 'flag'};
            }
            
            // Check for successful callback execution
            if (window._cdp_turnstile_callback && window._cdp_turnstile.token) {
                return {solved: true, method: 'callback'};
            }
            
            // Check if we're no longer on a challenge page
            if (window._cf_chl_opt && window._cf_chl_opt.chlStatus === 'passed') {
                return {solved: true, method: 'status'};
            }
            
            // Look for success indicators in the DOM
            const successIndicators = [
                // No longer showing challenge elements
                !document.querySelector('iframe[src*="challenges.cloudflare.com"]'),
                !document.querySelector('iframe[src*="turnstile"]'),
                document.querySelector('.cf-turnstile-success'),
                document.querySelector('.turnstile-success')
            ];
            
            if (successIndicators.some(Boolean)) {
                return {solved: true, method: 'dom'};
            }
            
            return {solved: false};
        }
        """)
        
        logger.debug(f"Turnstile solution check result: {result}")
        return result.get('solved', False)


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