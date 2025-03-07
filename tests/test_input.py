"""
Tests for input interactions.
"""
import asyncio
import os
import pytest

from cdp_browser.browser.browser import Browser
from cdp_browser.core.exceptions import CDPConnectionError


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_click():
    """Test clicking on elements."""
    browser = Browser("localhost", 9223)
    
    try:
        await browser.connect()
        page = await browser.new_page()
        await page.navigate("about:blank")
        
        # Create a button and click it
        await page.evaluate("""
            () => {
                const button = document.createElement('button');
                button.id = 'test-button';
                button.textContent = 'Click me';
                document.body.appendChild(button);
                
                button.addEventListener('click', () => {
                    button.textContent = 'Clicked!';
                });
            }
        """)
        
        # Click the button
        await page.click('#test-button')
        
        # Verify the button text changed
        text = await page.evaluate("document.querySelector('#test-button').textContent")
        assert text == 'Clicked!'
        
    except CDPConnectionError:
        pytest.skip("Chrome not available")
    finally:
        await browser.disconnect()


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_type():
    """Test typing into input elements."""
    browser = Browser("localhost", 9223)
    
    try:
        await browser.connect()
        page = await browser.new_page()
        await page.navigate("about:blank")
        
        # Create an input field
        await page.evaluate("""
            () => {
                const input = document.createElement('input');
                input.id = 'test-input';
                input.type = 'text';
                document.body.appendChild(input);
            }
        """)
        
        # Type into the input
        await page.type('#test-input', 'Hello, World!')
        
        # Verify the input value
        value = await page.evaluate("document.querySelector('#test-input').value")
        assert value == 'Hello, World!'
        
    except CDPConnectionError:
        pytest.skip("Chrome not available")
    finally:
        await browser.disconnect()


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_select():
    """Test selecting options from a select element."""
    browser = Browser("localhost", 9223)
    
    try:
        await browser.connect()
        page = await browser.new_page()
        await page.navigate("about:blank")
        
        # Create a select element
        await page.evaluate("""
            () => {
                const select = document.createElement('select');
                select.id = 'test-select';
                
                const options = ['Option 1', 'Option 2', 'Option 3'];
                options.forEach((text, index) => {
                    const option = document.createElement('option');
                    option.value = `value${index + 1}`;
                    option.text = text;
                    select.appendChild(option);
                });
                
                document.body.appendChild(select);
            }
        """)
        
        # Select an option
        await page.select('#test-select', 'value2')
        
        # Verify the selected value
        value = await page.evaluate("document.querySelector('#test-select').value")
        assert value == 'value2'
        
    except CDPConnectionError:
        pytest.skip("Chrome not available")
    finally:
        await browser.disconnect()


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_check():
    """Test checking checkboxes."""
    browser = Browser("localhost", 9223)
    
    try:
        await browser.connect()
        page = await browser.new_page()
        await page.navigate("about:blank")
        
        # Create a checkbox
        await page.evaluate("""
            () => {
                const checkbox = document.createElement('input');
                checkbox.id = 'test-checkbox';
                checkbox.type = 'checkbox';
                document.body.appendChild(checkbox);
            }
        """)
        
        # Check the checkbox
        await page.check('#test-checkbox')
        
        # Verify the checkbox is checked
        checked = await page.evaluate("document.querySelector('#test-checkbox').checked")
        assert checked is True
        
        # Uncheck the checkbox
        await page.uncheck('#test-checkbox')
        
        # Verify the checkbox is unchecked
        checked = await page.evaluate("document.querySelector('#test-checkbox').checked")
        assert checked is False
        
    except CDPConnectionError:
        pytest.skip("Chrome not available")
    finally:
        await browser.disconnect()


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_fill_form():
    """Test filling out a form."""
    browser = Browser("localhost", 9223)
    
    try:
        await browser.connect()
        page = await browser.new_page()
        await page.navigate("about:blank")
        
        # Create a form
        await page.evaluate("""
            () => {
                const form = document.createElement('form');
                form.id = 'test-form';
                
                // Text input
                const textInput = document.createElement('input');
                textInput.type = 'text';
                textInput.id = 'name';
                form.appendChild(textInput);
                
                // Email input
                const emailInput = document.createElement('input');
                emailInput.type = 'email';
                emailInput.id = 'email';
                form.appendChild(emailInput);
                
                // Submit button
                const submit = document.createElement('button');
                submit.type = 'submit';
                submit.textContent = 'Submit';
                form.appendChild(submit);
                
                document.body.appendChild(form);
                
                // Track form submission
                window.formSubmitted = false;
                form.addEventListener('submit', (e) => {
                    e.preventDefault();
                    window.formSubmitted = true;
                });
            }
        """)
        
        # Fill out the form
        await page.type('#name', 'John Doe')
        await page.type('#email', 'john@example.com')
        
        # Submit the form
        await page.click('button[type="submit"]')
        
        # Verify form values and submission
        name = await page.evaluate("document.querySelector('#name').value")
        email = await page.evaluate("document.querySelector('#email').value")
        submitted = await page.evaluate("window.formSubmitted")
        
        assert name == 'John Doe'
        assert email == 'john@example.com'
        assert submitted is True
        
    except CDPConnectionError:
        pytest.skip("Chrome not available")
    finally:
        await browser.disconnect()


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_press_key_combination():
    """Test pressing key combinations."""
    browser = Browser("localhost", 9223)
    
    try:
        await browser.connect()
        page = await browser.new_page()
        await page.navigate("about:blank")
        
        # Create a div to display key combinations
        await page.evaluate("""
            () => {
                const div = document.createElement('div');
                div.id = 'test-div';
                div.textContent = 'Press Ctrl+A';
                document.body.appendChild(div);
                
                // Track key combination
                window.ctrlAPressed = false;
                document.addEventListener('keydown', (e) => {
                    if (e.ctrlKey && e.key === 'a') {
                        window.ctrlAPressed = true;
                        div.textContent = 'Ctrl+A pressed!';
                    }
                });
            }
        """)
        
        # Press Ctrl+A
        await page.press_keys(['Control', 'a'])
        
        # Verify the key combination was detected
        pressed = await page.evaluate("window.ctrlAPressed")
        text = await page.evaluate("document.querySelector('#test-div').textContent")
        
        assert pressed is True
        assert text == 'Ctrl+A pressed!'
        
    except CDPConnectionError:
        pytest.skip("Chrome not available")
    finally:
        await browser.disconnect() 