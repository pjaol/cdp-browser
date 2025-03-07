#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1${NC}"
    else
        echo -e "${RED}✗ $1${NC}"
        exit 1
    fi
}

# Function to check if port is in use
check_port() {
    if lsof -i:$1 > /dev/null; then
        echo -e "${RED}Port $1 is already in use. Please free it up first.${NC}"
        exit 1
    fi
}

# Check if Docker is running
echo "Checking Docker status..."
docker info > /dev/null 2>&1
print_status "Docker is running"

# Check if port 9223 is available
echo "Checking if port 9223 is available..."
check_port 9223
print_status "Port 9223 is available"

# Stop any existing containers
echo "Stopping any existing containers..."
docker stop $(docker ps -q) > /dev/null 2>&1
print_status "Cleaned up existing containers"

# Build and run the container
echo "Building Docker image..."
cd docker && docker build -t cdp-browser . && cd ..
print_status "Docker image built"

echo "Starting container..."
CONTAINER_ID=$(docker run -d -p 9223:9223 cdp-browser)
print_status "Container started"

# Wait for Chrome to start
echo "Waiting for Chrome to initialize..."
sleep 5

# Test CDP endpoint
echo "Testing CDP endpoint..."
VERSION_INFO=$(curl -s http://localhost:9223/json/version)
if [ $? -eq 0 ] && [ ! -z "$VERSION_INFO" ]; then
    echo -e "${GREEN}✓ CDP endpoint is responding${NC}"
    echo "Chrome version info:"
    echo "$VERSION_INFO" | python3 -m json.tool
else
    echo -e "${RED}✗ CDP endpoint is not responding${NC}"
    exit 1
fi

# Test creating a new tab
echo -e "\nTesting page creation..."
TARGET_INFO=$(curl -s http://localhost:9223/json/new)
if [ $? -eq 0 ] && [ ! -z "$TARGET_INFO" ]; then
    echo -e "${GREEN}✓ Successfully created new page${NC}"
    TARGET_ID=$(echo $TARGET_INFO | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
    echo "Target ID: $TARGET_ID"
else
    echo -e "${RED}✗ Failed to create new page${NC}"
    exit 1
fi

# Test navigation using wscat
echo -e "\nTesting page navigation..."
echo "You can manually test WebSocket commands using:"
echo "wscat -c ws://localhost:9223/devtools/page/$TARGET_ID"
echo
echo "Example commands:"
echo "1. Enable Page domain:"
echo '{"id": 0, "method": "Page.enable"}'
echo
echo "2. Navigate to example.com:"
echo '{"id": 1, "method": "Page.navigate", "params": {"url": "https://example.com"}}'
echo
echo "3. Take screenshot:"
echo '{"id": 2, "method": "Page.captureScreenshot"}'
echo
echo "4. Get DOM content:"
echo '{"id": 3, "method": "Runtime.evaluate", "params": {"expression": "document.documentElement.outerHTML"}}'

# Print container logs for debugging
echo -e "\nContainer logs:"
docker logs $CONTAINER_ID

echo -e "\n${GREEN}Setup complete! CDP endpoint is ready for testing at ws://localhost:9223${NC}" 