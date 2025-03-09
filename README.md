# CDP Browser

A lightweight Python client for Chrome DevTools Protocol (CDP) with ARM64 support.

## Features

- Direct Chrome DevTools Protocol (CDP) communication
- No Selenium dependencies
- ARM64 compatibility
- Async/await interface
- Page navigation and interaction
- JavaScript execution
- Event handling
- Clean resource management with context managers

## Installation

### Prerequisites

- Python 3.9+
- Poetry
- Docker (for containerized usage)

### Install with Poetry

```bash
# Clone the repository
git clone https://github.com/pjaol/cdp-browser.git
cd cdp-browser

# Install dependencies
poetry install
```

## Docker Setup

### Using browserless/chrome (Recommended)

The simplest way to get started is using browserless/chrome:

```bash
docker run -d -p 9223:3000 --name browserless-chrome browserless/chrome:latest
```

This provides a Chrome instance with CDP enabled on port 9223.

## Usage Examples

### Basic Example

```python
import asyncio
from cdp_browser.browser import Browser

async def main():
    async with Browser(port=9223) as browser:
        # Create a new page using context manager
        async with await browser.create_page() as page:
            # Navigate to URL
            await page.navigate("https://example.com")
            
            # Get current URL
            current_url = await page.get_current_url()
            print(f"Current URL: {current_url}")

# Run the example
asyncio.run(main())
```

### Form Interaction Example

```python
import asyncio
from cdp_browser.browser import Browser

async def main():
    async with Browser(port=9223) as browser:
        async with await browser.create_page() as page:
            # Navigate to login page
            await page.navigate("https://www.saucedemo.com/")
            
            # Type into form fields
            await page.type("#user-name", "standard_user")
            await page.type("#password", "secret_sauce")
            
            # Click login button
            await page.click("#login-button")
            
            # Wait for navigation
            await page.wait_for_navigation()
            
            # Verify we're on the inventory page
            current_url = await page.get_current_url()
            assert current_url == "https://www.saucedemo.com/inventory.html"

# Run the example
asyncio.run(main())
```

### Multiple Pages Example

```python
import asyncio
from cdp_browser.browser import Browser

async def main():
    async with Browser(port=9223) as browser:
        # Create and navigate first page
        page1 = await browser.create_page()
        await page1.navigate("https://example.com")
        
        # Create and navigate second page
        page2 = await browser.create_page()
        await page2.navigate("https://www.example.org")
        
        # Clean up
        await page1.close()
        await page2.close()

# Run the example
asyncio.run(main())
```

## Event Handling

The browser and page classes support Chrome DevTools Protocol events. You can add custom event handlers:

```python
async def handle_load_event(params):
    print("Page load complete!")

async with Browser(port=9223) as browser:
    async with await browser.create_page() as page:
        # Add event handler
        page.add_event_handler("Page.loadEventFired", handle_load_event)
        
        # Navigate and watch for events
        await page.navigate("https://example.com")
```

## Running Tests

```bash
# Start Chrome in Docker
docker run -d -p 9223:3000 --name browserless-chrome browserless/chrome:latest

# Run tests
PYTHONPATH=. pytest -sv tests/test_simple.py
```

## Architecture

CDP Browser uses a simple client-server architecture to interact with Chrome:

```
┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │
│  CDP Browser    │────▶│  Chrome         │
│  Python Client  │     │  (in Docker)    │
│                 │◀────│                 │
└─────────────────┘     └─────────────────┘
   Port: any            Port: 9223
```

### Key Components

1. **Browser Class**: Main entry point for CDP interactions
   - Manages connection to Chrome
   - Creates and tracks pages
   - Handles browser-level commands

2. **Page Class**: Represents a browser tab/page
   - Handles navigation
   - Manages page-specific events
   - Provides interaction methods (click, type, etc.)
   - Uses context managers for clean resource management

3. **Event System**: Handles CDP events
   - Supports custom event handlers
   - Tracks page load and navigation states
   - Manages attached targets (e.g., service workers)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
