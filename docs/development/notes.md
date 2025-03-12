# CDP Browser Developer Notes

## Current Status and Findings

### Docker Setup Verification (browserless/chrome)

Our setup uses browserless/chrome as the base image, which provides Chrome with CDP support on ARM64/aarch64 architectures. The setup includes a proxy that forwards requests from port 9223 to Chrome's internal port.

#### 1. Build and Run Container

```bash
# Build the container
cd docker
docker build -t cdp-browser .

# Run the container
docker run -d -p 9223:9223 cdp-browser
```

#### 2. Verify CDP Endpoints

Basic endpoint verification:

```bash
# Get browser version info
curl -s http://localhost:9223/json/version | jq '.'

# Expected output:
{
  "Browser": "Chrome/121.0.6167.57",
  "Protocol-Version": "1.3",
  "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/121.0.0.0 Safari/537.36",
  "V8-Version": "12.1.285.20",
  "WebKit-Version": "537.36 (@add6d6ffbc3a1c7e78cc15e6ba2dcb15208bedd5)",
  "webSocketDebuggerUrl": "ws://localhost:9223/devtools/browser/[browser-id]"
}

# List available targets (tabs)
curl -s http://localhost:9223/json/list | jq '.'
```

#### 3. Create a New Tab

**Important Note**: browserless/chrome expects PUT instead of POST for creating new tabs:

```bash
# Create a new tab (using PUT method)
curl -s -X PUT http://localhost:9223/json/new | jq '.'

# Expected output:
{
  "description": "",
  "id": "[tab-id]",
  "title": "",
  "type": "page",
  "url": "about:blank",
  "webSocketDebuggerUrl": "ws://localhost:9223/devtools/page/[tab-id]"
}
```

#### 4. WebSocket Communication

After getting the WebSocket URL, you can connect and send CDP commands:

```bash
# Install wscat if needed
npm install -g wscat

# Connect to browser WebSocket
wscat -c "ws://localhost:9223/devtools/browser/[browser-id]"

# Or connect to a specific page
wscat -c "ws://localhost:9223/devtools/page/[tab-id]"

# Example commands in wscat session:
# Navigate to URL
{"id": 1, "method": "Page.navigate", "params": {"url": "https://example.com"}}

# Take screenshot
{"id": 2, "method": "Page.captureScreenshot"}

# Get page DOM
{"id": 3, "method": "Runtime.evaluate", "params": {"expression": "document.documentElement.outerHTML"}}
```

### Current Setup Status

✅ Docker container running with browserless/chrome  
✅ Proxy forwarding requests from 9223 to Chrome's internal port  
✅ CDP endpoints responding correctly  
✅ Ability to create new tabs (using PUT method)  
✅ WebSocket URLs available for both browser and page connections  

### Known Differences from Standard Chrome

1. Uses PUT instead of POST for `/json/new` endpoint
2. Includes Puppeteer by default (version 21.9.0)
3. Runs on port 3000 internally (proxied to 9223)
4. Supports ARM64/aarch64 architectures

### Next Steps

1. [ ] Implement WebSocket connection handling in our code
2. [ ] Add proper error handling for CDP commands
3. [ ] Create automated tests using the verified endpoints
4. [ ] Document any other browserless/chrome specific behaviors we discover
5. [ ] Consider implementing connection pooling or retry logic

### Useful Resources

1. [Chrome DevTools Protocol Viewer](https://chromedevtools.github.io/devtools-protocol/)
2. [Browserless Chrome Documentation](https://docs.browserless.io/)
3. [CDP Browser Research Notes](../documentation/research.md)

## Resource Cleanup and Event Loop Management

### Current Status
- All tests are passing successfully
- Connection cleanup has been significantly improved
- WebSocket connections are closed gracefully
- Task management and cancellation is working properly

### Known Issues
1. WebSocket Task Cleanup Warning
   - During test teardown, some WebSocket tasks may still be pending when the event loop is closed
   - This is a known limitation of the websockets library interaction with pytest's async test runner
   - Warning appears as: `Task was destroyed but it is pending!` for WebSocket protocol tasks
   - Not affecting functionality but should be monitored

### Implementation Notes
1. Connection Lifecycle
   - Using `preserve_loop_state` context manager to handle event loop closure gracefully
   - Implemented explicit task tracking and cleanup
   - Reduced timeouts to minimize wait time during cleanup
   - Added proper cancellation of message listener tasks

2. Task Management
   - All tasks are tracked in `_pending_tasks` set
   - Tasks are automatically removed when completed
   - Explicit cancellation during cleanup with timeout
   - Message processing tasks are created and tracked properly

3. WebSocket Handling
   - Graceful closure with short timeouts
   - Proper error handling for connection closure
   - Event listener cleanup during disconnection
   - Callback cancellation and cleanup

### Future Improvements
1. WebSocket Task Cleanup
   - Investigate ways to ensure all WebSocket tasks are completed before event loop closure
   - Consider implementing custom WebSocket protocol handler
   - Monitor websockets library updates for potential fixes

2. Testing Infrastructure
   - Consider implementing custom pytest fixtures for better async cleanup
   - Add more granular logging for task lifecycle
   - Consider adding metrics for connection/task lifecycle

## Docker Integration
- Chrome instance running in Docker container
- Remote debugging port exposed on 9223
- Connection working properly with Docker setup

## Test Coverage
1. Browser Tests
   - All core functionality tested
   - Resource cleanup verified
   - Error handling tested
   - Navigation and page management tested

2. Planned Tests
   - Input handling (test_input.py)
   - More complex navigation scenarios
   - Network condition simulation
   - Performance metrics collection 