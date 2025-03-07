#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# CDP endpoint
CDP_PORT=9223
CDP_HOST=localhost

echo "Testing CDP functionality..."

# Test 1: Check if CDP endpoint is responding
echo -e "\n1. Testing CDP endpoint..."
VERSION_INFO=$(curl -s http://${CDP_HOST}:${CDP_PORT}/json/version)
if [ $? -eq 0 ] && [ ! -z "$VERSION_INFO" ]; then
    echo -e "${GREEN}✓ CDP endpoint is responding${NC}"
    echo "Chrome version info:"
    echo "$VERSION_INFO" | python3 -m json.tool || echo "$VERSION_INFO"
else
    echo -e "${RED}✗ CDP endpoint is not responding${NC}"
    exit 1
fi

# Test 2: List available targets
echo -e "\n2. Testing target listing..."
TARGET_LIST=$(curl -s http://${CDP_HOST}:${CDP_PORT}/json/list)
if [ $? -eq 0 ] && [ ! -z "$TARGET_LIST" ]; then
    echo -e "${GREEN}✓ Successfully retrieved target list${NC}"
    echo "Available targets:"
    echo "$TARGET_LIST" | python3 -m json.tool || echo "$TARGET_LIST"
    
    # Try to get an existing target ID first
    TARGET_ID=$(echo "$TARGET_LIST" | python3 -c "import sys, json; targets = json.load(sys.stdin); print(targets[0]['id'] if targets else '')" 2>/dev/null)
else
    echo -e "${RED}✗ Failed to retrieve target list${NC}"
    exit 1
fi

# Test 3: Create new page if we don't have a target
if [ -z "$TARGET_ID" ]; then
    echo -e "\n3. Creating new page..."
    TARGET_INFO=$(curl -s -X PUT http://${CDP_HOST}:${CDP_PORT}/json/new)
    if [ $? -eq 0 ] && [ ! -z "$TARGET_INFO" ]; then
        echo -e "${GREEN}✓ Successfully created new page${NC}"
        TARGET_ID=$(echo "$TARGET_INFO" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null)
        if [ -z "$TARGET_ID" ]; then
            echo -e "${RED}✗ Failed to parse target ID${NC}"
            echo "Raw response: $TARGET_INFO"
            exit 1
        fi
        echo "Target ID: $TARGET_ID"
    else
        echo -e "${RED}✗ Failed to create new page${NC}"
        exit 1
    fi
else
    echo -e "\n3. Using existing target: $TARGET_ID"
fi

# Test 4: Test WebSocket connection with retry
echo -e "\n4. Testing WebSocket connection..."
MAX_RETRIES=3
for i in $(seq 1 $MAX_RETRIES); do
    echo "Attempt $i of $MAX_RETRIES..."
    WS_TEST=$(wscat -c "ws://${CDP_HOST}:${CDP_PORT}/devtools/page/$TARGET_ID" -x '{"id": 0, "method": "Page.enable"}' 2>&1)
    WS_STATUS=$?
    if [ $WS_STATUS -eq 0 ]; then
        echo -e "${GREEN}✓ WebSocket connection successful${NC}"
        echo "Response: $WS_TEST"
        break
    else
        echo "WebSocket attempt failed: $WS_TEST"
        if [ $i -eq $MAX_RETRIES ]; then
            echo -e "${RED}✗ WebSocket connection failed after $MAX_RETRIES attempts${NC}"
            exit 1
        fi
        sleep 2
    fi
done

# Test 5: Navigate to example.com
echo -e "\n5. Testing page navigation..."
WS_NAV=$(wscat -c "ws://${CDP_HOST}:${CDP_PORT}/devtools/page/$TARGET_ID" -x '{"id": 1, "method": "Page.navigate", "params": {"url": "https://example.com"}}' 2>&1)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Navigation command sent successfully${NC}"
    echo "Response: $WS_NAV"
else
    echo -e "${RED}✗ Navigation command failed${NC}"
    echo "Error: $WS_NAV"
    exit 1
fi

echo -e "\n${GREEN}All CDP tests completed successfully!${NC}"
echo "CDP endpoint is working at ws://${CDP_HOST}:${CDP_PORT}" 