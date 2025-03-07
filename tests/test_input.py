"""
Tests for input functionality.
"""
import os
import pytest

from cdp_browser.browser.browser import Browser
from cdp_browser.core.exceptions import CDPError


@pytest.mark.asyncio
async def test_click():
    """Test clicking on elements."""
    # Skip if Chrome is not available
    if not os.environ.get("CHROME_AVAILABLE"):
        pytest.skip("Chrome not available")
    
    browser = Browser()
    try:
        # Connect to browser
        await browser.connect()
        
        # Create a new page
        page = await browser.new_page()
        
        # Create a test page with a button
        await page.evaluate("""
        document.body.innerHTML = `
            <button id="test-button">Click Me</button>
            <div id="result"></div>
            <script>
                document.getElementById('test-button').addEventListener('click', () => {
                    document.getElementById('result').textContent = 'Button Clicked';
                });
            </script>
        `;
        """)
        
        # Click the button
        await page.browser.input.click("#test-button")
        
        # Check that the button was clicked
        result = await page.evaluate("document.getElementById('result').textContent")
        assert result.get("result", {}).get("value") == "Button Clicked"
    finally:
        # Disconnect from browser
        await browser.disconnect()


@pytest.mark.asyncio
async def test_type():
    """Test typing into input fields."""
    # Skip if Chrome is not available
    if not os.environ.get("CHROME_AVAILABLE"):
        pytest.skip("Chrome not available")
    
    browser = Browser()
    try:
        # Connect to browser
        await browser.connect()
        
        # Create a new page
        page = await browser.new_page()
        
        # Create a test page with an input field
        await page.evaluate("""
        document.body.innerHTML = `
            <input id="test-input" type="text">
            <div id="result"></div>
            <script>
                document.getElementById('test-input').addEventListener('input', () => {
                    document.getElementById('result').textContent = document.getElementById('test-input').value;
                });
            </script>
        `;
        """)
        
        # Type into the input field
        await page.browser.input.type("#test-input", "Hello, World!")
        
        # Check that the text was typed
        result = await page.evaluate("document.getElementById('test-input').value")
        assert result.get("result", {}).get("value") == "Hello, World!"
        
        # Check that the input event was fired
        result = await page.evaluate("document.getElementById('result').textContent")
        assert result.get("result", {}).get("value") == "Hello, World!"
        
        # Test clearing the input
        await page.browser.input.type("#test-input", "New Text", clear=True)
        
        # Check that the text was cleared and new text was typed
        result = await page.evaluate("document.getElementById('test-input').value")
        assert result.get("result", {}).get("value") == "New Text"
    finally:
        # Disconnect from browser
        await browser.disconnect()


@pytest.mark.asyncio
async def test_select():
    """Test selecting options in a select element."""
    # Skip if Chrome is not available
    if not os.environ.get("CHROME_AVAILABLE"):
        pytest.skip("Chrome not available")
    
    browser = Browser()
    try:
        # Connect to browser
        await browser.connect()
        
        # Create a new page
        page = await browser.new_page()
        
        # Create a test page with a select element
        await page.evaluate("""
        document.body.innerHTML = `
            <select id="test-select">
                <option value="option1">Option 1</option>
                <option value="option2">Option 2</option>
                <option value="option3">Option 3</option>
            </select>
            <div id="result"></div>
            <script>
                document.getElementById('test-select').addEventListener('change', () => {
                    document.getElementById('result').textContent = document.getElementById('test-select').value;
                });
            </script>
        `;
        """)
        
        # Select an option
        await page.browser.input.select("#test-select", ["option2"])
        
        # Check that the option was selected
        result = await page.evaluate("document.getElementById('test-select').value")
        assert result.get("result", {}).get("value") == "option2"
        
        # Check that the change event was fired
        result = await page.evaluate("document.getElementById('result').textContent")
        assert result.get("result", {}).get("value") == "option2"
    finally:
        # Disconnect from browser
        await browser.disconnect()


@pytest.mark.asyncio
async def test_check():
    """Test checking checkboxes."""
    # Skip if Chrome is not available
    if not os.environ.get("CHROME_AVAILABLE"):
        pytest.skip("Chrome not available")
    
    browser = Browser()
    try:
        # Connect to browser
        await browser.connect()
        
        # Create a new page
        page = await browser.new_page()
        
        # Create a test page with a checkbox
        await page.evaluate("""
        document.body.innerHTML = `
            <input id="test-checkbox" type="checkbox">
            <div id="result"></div>
            <script>
                document.getElementById('test-checkbox').addEventListener('change', () => {
                    document.getElementById('result').textContent = document.getElementById('test-checkbox').checked ? 'Checked' : 'Unchecked';
                });
            </script>
        `;
        """)
        
        # Check the checkbox
        await page.browser.input.check("#test-checkbox")
        
        # Check that the checkbox was checked
        result = await page.evaluate("document.getElementById('test-checkbox').checked")
        assert result.get("result", {}).get("value") is True
        
        # Check that the change event was fired
        result = await page.evaluate("document.getElementById('result').textContent")
        assert result.get("result", {}).get("value") == "Checked"
        
        # Uncheck the checkbox
        await page.browser.input.check("#test-checkbox", False)
        
        # Check that the checkbox was unchecked
        result = await page.evaluate("document.getElementById('test-checkbox').checked")
        assert result.get("result", {}).get("value") is False
        
        # Check that the change event was fired
        result = await page.evaluate("document.getElementById('result').textContent")
        assert result.get("result", {}).get("value") == "Unchecked"
    finally:
        # Disconnect from browser
        await browser.disconnect()


@pytest.mark.asyncio
async def test_fill_form():
    """Test filling a form."""
    # Skip if Chrome is not available
    if not os.environ.get("CHROME_AVAILABLE"):
        pytest.skip("Chrome not available")
    
    browser = Browser()
    try:
        # Connect to browser
        await browser.connect()
        
        # Create a new page
        page = await browser.new_page()
        
        # Create a test page with a form
        await page.evaluate("""
        document.body.innerHTML = `
            <form id="test-form">
                <input id="name" type="text">
                <input id="email" type="email">
                <select id="country">
                    <option value="us">United States</option>
                    <option value="ca">Canada</option>
                    <option value="uk">United Kingdom</option>
                </select>
                <input id="subscribe" type="checkbox">
                <button id="submit" type="submit">Submit</button>
            </form>
            <div id="result"></div>
            <script>
                document.getElementById('test-form').addEventListener('submit', (e) => {
                    e.preventDefault();
                    const name = document.getElementById('name').value;
                    const email = document.getElementById('email').value;
                    const country = document.getElementById('country').value;
                    const subscribe = document.getElementById('subscribe').checked;
                    document.getElementById('result').textContent = JSON.stringify({name, email, country, subscribe});
                });
            </script>
        `;
        """)
        
        # Fill the form
        form_data = {
            "#name": "John Doe",
            "#email": "john@example.com",
            "#country": "uk",
            "#subscribe": "true"
        }
        
        await page.browser.input.fill_form(form_data, submit=True, submit_selector="#submit")
        
        # Check that the form was submitted with the correct data
        result = await page.evaluate("document.getElementById('result').textContent")
        result_json = result.get("result", {}).get("value", "{}")
        
        # Check that the result contains the expected values
        assert "John Doe" in result_json
        assert "john@example.com" in result_json
        assert "uk" in result_json
        assert "true" in result_json
    finally:
        # Disconnect from browser
        await browser.disconnect()


@pytest.mark.asyncio
async def test_press_key_combination():
    """Test pressing key combinations."""
    # Skip if Chrome is not available
    if not os.environ.get("CHROME_AVAILABLE"):
        pytest.skip("Chrome not available")
    
    browser = Browser()
    try:
        # Connect to browser
        await browser.connect()
        
        # Create a new page
        page = await browser.new_page()
        
        # Create a test page that listens for key combinations
        await page.evaluate("""
        document.body.innerHTML = `
            <div id="result"></div>
            <script>
                document.addEventListener('keydown', (e) => {
                    if (e.ctrlKey && e.key === 'a') {
                        document.getElementById('result').textContent = 'Ctrl+A pressed';
                    }
                });
            </script>
        `;
        """)
        
        # Press Ctrl+A
        await page.browser.input.press_key_combination(["Control", "a"])
        
        # Check that the key combination was detected
        result = await page.evaluate("document.getElementById('result').textContent")
        assert result.get("result", {}).get("value") == "Ctrl+A pressed"
    finally:
        # Disconnect from browser
        await browser.disconnect() 