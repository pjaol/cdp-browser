# CDP Browser

A lightweight Python client for Chrome DevTools Protocol (CDP) on ARM64 architecture.

## Why?
I ran into the classic "it works on my laptop" problem when migrating to a Docker Compose setup. 
My Chrome integrations suddenly failed because Chrome was no longer supported on Linux ARM64/aarch64. 
And docker on Mac's are ARM64 architectures... 
Selenium web driver, which handled browser interactions, only works on x86_64, 
so even solutions like selenium, Puppeteer, Undetectable weren't working. 

*I'm a huge fan of [Undetectable](https://github.com/ultrafunkamsterdam/undetected-chromedriver) and took inspiration from [nodriver](https://github.com/ultrafunkamsterdam/nodriver) for this.*

The Chrome Developer Protocol (CDP) looked promising, since it exposes Chrome's DevTools over a WebSocket and provides additional features for browser control. Unfortunately, existing CDP libraries either required a local Chrome instance—forcing your application to run in the same container — and / or relied on transpiling the CDP protocol and are currently broken...

In the end, I had to build my own solution.

## Features

- Direct Chrome DevTools Protocol (CDP) communication
- No Selenium dependencies
- ARM64 compatibility
- Proxy support
- Headless mode support
- Page navigation and interaction
- JavaScript execution
- Event handling
- WebSocket proxy for remote connections

## Architecture Overview

CDP Browser uses a client-server architecture to interact with Chrome:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  CDP Browser    │────▶│  WebSocket      │────▶│  Chrome         │
│  Python Client  │     │  Connection     │     │  Browser        │
│                 │◀────│                 │◀────│                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
       Client                Transport              Browser
```

### Docker-based Architecture

For ARM64 compatibility and isolation, we use Docker to run Chrome:

```
┌─────────────────────────────────────────────────────────────┐
│ Host Machine                                                │
│                                                             │
│  ┌─────────────────┐       ┌─────────────────────────────┐  │
│  │                 │       │ Docker Container            │  │
│  │  CDP Browser    │       │                             │  │
│  │  Python Client  │◀─────▶│  Chrome with CDP enabled    │  │
│  │                 │       │  (browserless/chrome)       │  │
│  └─────────────────┘       │                             │  │
│                            └─────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.9+
- Docker (for containerized usage)

### Install

```bash
# Clone the repository
git clone https://github.com/pjaol/cdp-browser.git
cd cdp-browser

# Install dependencies
pip install -r requirements.txt
```

## Docker Usage

### Using Our Custom Image

The most reliable way to run Chrome with CDP support is to use our custom image:

```bash
# Build the custom image
docker build -t cdp-browser -f docker/Dockerfile .

# Run the custom image
docker run -d -p 9223:9223 --name cdp-browser-container cdp-browser
```

This image includes:
- Chrome with CDP enabled
- A WebSocket proxy for remote connections
- Support for headless mode
- Support for proxy servers

### WebSocket Proxy

Our custom image includes a WebSocket proxy that allows connections from any IP address to the Chrome instance. The proxy:

- Listens on port 9223
- Forwards WebSocket connections to Chrome
- Handles browser instance ID management
- Provides better stability for remote connections

## Usage Examples

### Basic Example

```python
import asyncio
from cdp_browser.browser import Browser

async def main():
    async with Browser(port=9223) as browser:
        # Create a new page
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
            
            # Type username and password
            await page.type("#user-name", "standard_user")
            await page.type("#password", "secret_sauce")
            
            # Click login button
            await page.click("#login-button")
            
            # Wait for navigation
            await page.wait_for_navigation()
            
            # Get current URL
            current_url = await page.get_current_url()
            print(f"Current URL after login: {current_url}")

# Run the example
asyncio.run(main())
```

### Multiple Pages Example

```python
import asyncio
from cdp_browser.browser import Browser

async def main():
    async with Browser(port=9223) as browser:
        # Create multiple pages
        page1 = await browser.create_page()
        page2 = await browser.create_page()
        
        # Navigate pages independently
        await page1.navigate("https://example.com")
        await page2.navigate("https://www.example.org")
        
        # Get URLs
        url1 = await page1.get_current_url()
        url2 = await page2.get_current_url()
        
        print(f"Page 1 URL: {url1}")
        print(f"Page 2 URL: {url2}")
        
        # Close pages
        await page1.close()
        await page2.close()

# Run the example
asyncio.run(main())
```

## Stealth Mode

The CDP Browser includes a stealth mode that helps avoid detection by fingerprinting services. The stealth mode is implemented in the `StealthBrowser` class and includes various techniques to avoid detection:

### Features

- Chrome runtime emulation
- WebDriver property removal
- User agent spoofing
- Window size customization
- Language preferences
- Plugin and extension emulation
- Function prototype integrity preservation
- Advanced iframe handling

### Testing Against Fingerprinting Services

The stealth mode has been tested against multiple fingerprinting and bot detection services:

1. **CreepJS** - A comprehensive browser fingerprinting tool
   - Test results are saved in the `fingerprint_results` directory
   - Screenshots and HTML content are captured for analysis
   - Our stealth mode successfully avoids many basic fingerprinting techniques

2. **Fingerprint.js Pro** - A commercial fingerprinting service
   - Tests are marked as experimental due to potential WebSocket connection issues
   - Current implementation can be detected by advanced fingerprinting techniques

3. **Cloudflare Challenge** - One of the most sophisticated bot detection systems
   - Tests against specific Cloudflare challenge pages show current limitations
   - Our implementation can't yet bypass Cloudflare's Turnstile CAPTCHA system
   - Results provide valuable insights into improving stealth capabilities

### Running Fingerprinting Tests

```bash
CHROME_AVAILABLE=1 PYTHONPATH=. pytest -vs tests/test_stealth_fingerprint.py
```

### Current Status

The stealth mode successfully avoids basic bot detection, but some advanced fingerprinting techniques can still detect automation:

- WebDriver property is detected as "on" by some fingerprinting services
- Worker user agent is sometimes detected as headless
- Cloudflare's Turnstile CAPTCHA system can detect our automation
- Specific JavaScript challenge responses require further improvement

### Stealth Mode Examples

See the examples directory for practical applications of stealth mode:

- `examples/stealth_mode.py` - Basic stealth mode usage against fingerprinting
- `examples/cloudflare_test.py` - Testing against Cloudflare's bot detection

### Future Improvements

- Enhanced WebDriver property spoofing
- Worker user agent fixes
- More sophisticated browser behavior emulation
- Improved handling of advanced JavaScript challenges
- Human-like mouse movement and interaction patterns
- Network fingerprint normalization
- TLS fingerprint matching
- Enhanced iframe and worker context handling

## Examples

The `examples` directory contains several examples demonstrating how to use CDP Browser:

- `simple_navigation.py` - Demonstrates basic page navigation
- `form_interaction.py` - Shows how to interact with forms
- `stealth_mode.py` - Demonstrates the stealth mode capabilities against fingerprinting
- `cloudflare_test.py` - Tests the stealth mode against Cloudflare's bot detection

To run an example:

```bash
# Make sure Chrome is running with CDP enabled
# Run a specific example
python examples/simple_navigation.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
