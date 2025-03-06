"""
Example script for form interaction using browserless/chrome API.
"""
import asyncio
import base64
import json
import os
import sys
from urllib.parse import urljoin

import aiohttp

# Base URL for browserless API
BROWSERLESS_URL = "http://localhost:9222"


async def execute_function(code: str) -> dict:
    """
    Execute a function using browserless API.
    
    Args:
        code: JavaScript function code
        
    Returns:
        Result of function execution
    """
    function_endpoint = "/function"
    full_url = urljoin(BROWSERLESS_URL, function_endpoint)
    
    payload = {
        "code": code
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(full_url, json=payload) as response:
            if response.status != 200:
                raise Exception(f"Failed to execute function: {response.status} - {await response.text()}")
            
            return await response.json()


async def search_duckduckgo(query: str) -> tuple:
    """
    Search DuckDuckGo for a query.
    
    Args:
        query: Search query
        
    Returns:
        Tuple of (search results, screenshot)
    """
    # Create a function that will be executed by browserless
    code = f"""
    module.exports = async function({{ page }}) {{
        // Navigate to DuckDuckGo
        await page.goto('https://duckduckgo.com', {{ waitUntil: 'networkidle2' }});
        
        // Take a screenshot before search
        const beforeScreenshot = await page.screenshot({{ encoding: 'base64' }});
        
        // Fill the search box
        await page.type('input[name="q"]', '{query}');
        
        // Find the right button (could be different selectors depending on the page version)
        const buttonSelectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            '#search_button',
            '.search__button',
            '.searchbox_searchButton'
        ];
        
        let buttonFound = false;
        for (const selector of buttonSelectors) {{
            const button = await page.$(selector);
            if (button) {{
                // Submit the form by clicking the button
                await Promise.all([
                    page.waitForNavigation({{ waitUntil: 'networkidle2' }}),
                    button.click()
                ]);
                buttonFound = true;
                break;
            }}
        }}
        
        if (!buttonFound) {{
            // If no button found, try submitting the form directly
            await Promise.all([
                page.waitForNavigation({{ waitUntil: 'networkidle2' }}),
                page.evaluate(() => {{
                    document.querySelector('form').submit();
                }})
            ]);
        }}
        
        // Wait for results to load (different selectors for results)
        const resultSelectors = ['.result__title', '.serp__results', '.react-results--main'];
        let resultsFound = false;
        
        for (const selector of resultSelectors) {{
            try {{
                await page.waitForSelector(selector, {{ timeout: 5000 }});
                resultsFound = true;
                break;
            }} catch (e) {{
                // Try next selector
            }}
        }}
        
        // Get search results
        let results = [];
        if (resultsFound) {{
            results = await page.evaluate(() => {{
                // Try different result selectors
                const selectors = ['.result__title', '.serp__results a', '.react-results--main a'];
                for (const selector of selectors) {{
                    const elements = document.querySelectorAll(selector);
                    if (elements.length > 0) {{
                        return Array.from(elements).map(el => el.textContent.trim());
                    }}
                }}
                return [];
            }});
        }}
        
        // Take a screenshot after search
        const afterScreenshot = await page.screenshot({{ encoding: 'base64', fullPage: true }});
        
        return {{ 
            results, 
            beforeScreenshot,
            afterScreenshot
        }};
    }};
    """
    
    # Execute the function
    result = await execute_function(code)
    
    # Extract search results and screenshots
    search_results = result.get("results", [])
    before_screenshot_base64 = result.get("beforeScreenshot", "")
    after_screenshot_base64 = result.get("afterScreenshot", "")
    
    before_screenshot_data = base64.b64decode(before_screenshot_base64) if before_screenshot_base64 else None
    after_screenshot_data = base64.b64decode(after_screenshot_base64) if after_screenshot_base64 else None
    
    return search_results, before_screenshot_data, after_screenshot_data


async def main():
    """
    Main function.
    """
    try:
        # Search query
        query = "Python CDP Browser"
        print(f"Searching DuckDuckGo for '{query}'...")
        
        # Search DuckDuckGo
        search_results, before_screenshot, after_screenshot = await search_duckduckgo(query)
        
        # Save screenshots
        if before_screenshot:
            before_path = "duckduckgo_before.png"
            with open(before_path, "wb") as f:
                f.write(before_screenshot)
            print(f"Before screenshot saved to: {before_path}")
            
        if after_screenshot:
            after_path = "duckduckgo_after.png"
            with open(after_path, "wb") as f:
                f.write(after_screenshot)
            print(f"After screenshot saved to: {after_path}")
        
        # Print search results
        print(f"Found {len(search_results)} search results:")
        for i, result in enumerate(search_results[:5], 1):
            print(f"{i}. {result}")
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main()) 