# CDP Browser Development Setup

## Docker Setup

### Prerequisites
- Docker installed and running
- Port 9223 available on host machine

### Quick Start
```bash
# Build the Docker image
cd docker
docker build -t cdp-browser .

# Run the container
docker run -d -p 9223:9223 cdp-browser
```

### Verification Steps

1. Check CDP endpoints are accessible:
```bash
curl -s http://localhost:9223/json/version
```
Expected response should include Chrome version and WebSocket debugger URL.

2. List available targets:
```bash
curl -s http://localhost:9223/json/list
```
Should return an array of available debugging targets.

### Testing CDP Operations

We've verified the following CDP operations work correctly:

1. Page Navigation:
```javascript
{"id": 1, "method": "Page.navigate", "params": {"url": "https://example.com"}}
```

2. Screenshot Capture:
```javascript
{"id": 2, "method": "Page.captureScreenshot"}
```

3. DOM Content Retrieval:
```javascript
{"id": 3, "method": "Runtime.evaluate", "params": {"expression": "document.documentElement.outerHTML"}}
```

### Important Notes

1. The CDP endpoint requires enabling the Page domain before navigation:
```javascript
{"id": 0, "method": "Page.enable"}
```

2. All CDP commands should be sent via WebSocket connection to the debugger URL:
```
ws://localhost:9223/devtools/page/<target-id>
```

3. The Docker setup uses port 9223 by default - this can be modified if needed by changing the port mapping when running the container.

### Automated Testing

A test script is provided to verify the CDP setup:

```bash
./scripts/test_cdp.sh
```

This script will:
1. Check Docker and port availability
2. Build and run the container
3. Verify CDP endpoint connectivity
4. Create a new page
5. Provide example CDP commands for testing

### Troubleshooting

1. If Chrome crashes or becomes unresponsive:
   - Stop all running containers: `docker stop $(docker ps -q)`
   - Remove any existing containers: `docker rm $(docker ps -aq)`
   - Rebuild and restart the container

2. Verify Chrome is running correctly in the container:
```bash
docker logs <container-id>
```

3. Common issues:
   - Port conflicts: Ensure no other process is using port 9223
   - Connection refused: Check if the container is running and healthy
   - WebSocket connection failures: Verify the target ID is correct and Page domain is enabled 