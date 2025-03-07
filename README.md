# CDP Browser

A lightweight Python client for Chrome DevTools Protocol (CDP) on ARM64 architecture.

## Why?
While developing tech, the standard it's working on my laptop issue hit.
I was moving to a docker compose setup and my chrome integrations were failing and I discovered that chrome was no longer support on Linux ARM64 or aarch64. 
Selenium which was driving the interactions, was also built only for x86_64, so even if I got a chrome docker instance working like browserless or puppettier they would still run afowl with selenium. 

CDP (Chrome Developer Protocol) seemed like the way to go, it's basically the DevTools in chrome listening on a websocket but with additonal functionality for browser control.

There are a few libraries out that implement CDP, however again I could not get them to work
some required a local instance meaning if you got a working docker chrome, your application would also work in that docker instance
Others were automated to transpile the CDP protocol and are simply not working. 

Hence regrettably we had to do our own.

## Features

- Direct Chrome DevTools Protocol (CDP) communication
- No Selenium dependencies
- ARM64 compatibility
- Proxy support
- Headless mode support
- Page navigation and interaction
- JavaScript execution
- Screenshot capture
- Cookie management
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

### Communication Flow with WebSocket Proxy

```
┌──────────┐     ┌───────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│          │     │           │     │          │     │          │     │          │
│  Python  │────▶│  CDP      │────▶│ WebSocket│────▶│ Chrome   │────▶│ Webpage  │
│  Client  │     │  Protocol │     │  Proxy   │     │ Browser  │     │          │
│          │◀────│           │◀────│          │◀────│          │◀────│          │
└──────────┘     └───────────┘     └──────────┘     └──────────┘     └──────────┘
    Action         WebSocket        Forwarding       Execution        Rendering
```

## Why Docker?

We use Docker for several critical reasons:

1. **ARM64 Compatibility**: Ensures consistent operation on ARM64 architecture without relying on Selenium or other drivers that have compatibility issues.

2. **Isolation**: Provides a clean, isolated environment for Chrome to run without interfering with the host system.

3. **Reproducibility**: Guarantees the same environment across different machines and deployments.

4. **Security**: Sandboxes the browser operations, limiting potential security risks.

5. **Dependency Management**: Bundles all necessary dependencies in a single container, avoiding version conflicts.

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

## Docker Usage

### Recommended Approach: Using Our Custom Image

The most reliable way to run Chrome with CDP support is to use our custom image:

```bash
# Build the custom image
docker build -t cdp-browser -f docker/Dockerfile .

# Run the custom image
docker run -d -p 9222:9222 -p 9223:9223 --name cdp-browser-container cdp-browser
```

This image includes:
- Chrome with CDP enabled
- A WebSocket proxy for remote connections
- Support for headless mode
- Support for proxy servers

### WebSocket Proxy

Our custom image includes a WebSocket proxy that allows connections from any IP address to the Chrome instance. The proxy:

- Listens on port 9223
- Forwards WebSocket connections to Chrome on port 9222
- Handles browser instance ID management
- Provides better stability for remote connections

To connect to the proxy, use port 9223 instead of 9222 in your CDP client:

```python
# Connect to the proxy
browser = Browser("localhost", 9223)
```

### Alternative: Using browserless/chrome

You can also use the browserless/chrome image directly:

```bash
# Run browserless/chrome
docker run -d -p 9222:3000 --name browserless-chrome browserless/chrome:latest
```

This image is specifically designed to expose the Chrome DevTools Protocol and works reliably with our CDP Browser client.

### How CDP Browser Interacts with Docker

1. **Connection Establishment**:
   - The CDP Browser client connects to the Chrome instance running in Docker via WebSocket
   - Connection is made to `ws://localhost:9223/` which is forwarded to the container

2. **Protocol Communication**:
   - Commands are sent as JSON messages over the WebSocket connection
   - Chrome executes the commands and returns responses

3. **Browser Control Flow**:
   ```
   ┌───────────────┐     ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
   │ CDP Browser   │     │ Docker        │     │ WebSocket     │     │ Chrome        │
   │ Client        │     │ Container     │     │ Proxy         │     │ Browser       │
   │               │     │               │     │               │     │               │
   │ 1. Connect    │────▶│               │────▶│               │────▶│ WebSocket     │
   │               │     │               │     │               │     │ Server        │
   │               │     │               │     │               │     │               │
   │ 2. Send       │────▶│ Port          │────▶│ Forward      │────▶│ Execute       │
   │    Command    │     │ Forwarding    │     │ Command      │     │ Command       │
   │               │     │               │     │               │     │               │
   │ 3. Receive    │◀────│               │◀────│               │◀────│ Return        │
   │    Response   │     │               │     │               │     │ Result        │
   └───────────────┘     └───────────────┘     └───────────────┘     └───────────────┘
   ```

## Usage Examples

### Basic Example

```python
import asyncio
from cdp_browser.browser.browser import Browser

async def main():
    # Create browser instance (using the proxy port)
    browser = Browser("localhost", 9223)
    
    try:
        # Connect to browser
        await browser.connect()
        
        # Create a new page
        page = await browser.new_page()
        
        # Navigate to URL
        await page.navigate("https://example.com")
        
        # Print page title
        print(f"Page title: {page.title}")
        
        # Take screenshot
        screenshot_data = await page.screenshot()
        with open("screenshot.png", "wb") as f:
            f.write(screenshot_data)
    finally:
        # Disconnect from browser
        await browser.disconnect()

# Run the example
asyncio.run(main())
```

### Using the Chrome DevTools Protocol Directly

For more advanced operations, you can use the CDP protocol directly:

```python
import asyncio
import aiohttp
import base64

async def take_screenshot(url):
    # Connect to the proxy
    async with aiohttp.ClientSession() as session:
        # Get available targets
        async with session.get("http://localhost:9223/json/list") as response:
            targets = await response.json()
            target = targets[0]
            
            # Connect to the target via WebSocket
            ws_url = target["webSocketDebuggerUrl"]
            async with session.ws_connect(ws_url) as ws:
                # Navigate to the URL
                await ws.send_json({
                    "id": 1,
                    "method": "Page.navigate",
                    "params": {"url": url}
                })
                
                # Wait for navigation to complete
                while True:
                    msg = await ws.receive_json()
                    if msg.get("id") == 1:
                        break
                
                # Wait a bit for the page to render
                await asyncio.sleep(1)
                
                # Capture screenshot
                await ws.send_json({
                    "id": 2,
                    "method": "Page.captureScreenshot",
                    "params": {"format": "png", "quality": 100}
                })
                
                # Wait for screenshot response
                while True:
                    msg = await ws.receive_json()
                    if msg.get("id") == 2:
                        return base64.b64decode(msg["result"]["data"])

async def main():
    screenshot = await take_screenshot("https://example.com")
    with open("screenshot.png", "wb") as f:
        f.write(screenshot)

asyncio.run(main())
```

### Command Line Interface

```bash
# Navigate to a URL
python -m cdp_browser.main https://example.com

# Take a screenshot
python -m cdp_browser.main https://example.com --screenshot screenshot.png

# Use a proxy
python -m cdp_browser.main https://example.com --proxy http://user:pass@host:port

# Enable debug logging
python -m cdp_browser.main https://example.com --debug
```

## Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run tests with Chrome available
CHROME_AVAILABLE=1 poetry run pytest
```

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure the Docker container is running and port 9222 is properly exposed.

2. **Empty Response**: Check if Chrome is binding to the correct address inside the container.

3. **Protocol Errors**: Verify that the Chrome version in the container supports the CDP commands you're using.

4. **Port Conflicts**: If port 9222 is already in use, you can use a different port by changing the port mapping in the Docker run command.

5. **ARM64 Compatibility**: If you're running on ARM64 architecture, make sure to use the ARM64 version of the browserless/chrome image.

## License

MIT
