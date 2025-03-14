#!/bin/bash
set -x
set -e

# Define Chrome flags in an array to preserve spaces and quotes correctly
CHROME_FLAGS=(
    --remote-allow-origins=*
    --no-first-run
    --user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    --no-sandbox
    --disable-gpu
    --remote-debugging-address=0.0.0.0
    --remote-debugging-port=9222
    --disable-blink-features=AutomationControlled
)

# Check if headless mode is enabled (default: true)
if [ "${HEADLESS:-true}" = "true" ]; then
    export CHROME_HEADLESS=true
    CHROME_FLAGS+=(--headless=new)
else
    export CHROME_HEADLESS=false
fi

# Check if proxy server is configured
if [ -n "$PROXY_SERVER" ]; then
    CHROME_FLAGS+=(--proxy-server="$PROXY_SERVER")
fi

# Print Chrome flags
echo "Starting Chrome with flags: ${CHROME_FLAGS[*]}"

# Start Chrome in the background with the proper array expansion
google-chrome "${CHROME_FLAGS[@]}" &
CHROME_PID=$!

# Wait a moment for Chrome to start
sleep 2

# Start the Node.js proxy
echo "Starting WebSocket proxy..."
node ./proxy.js &
PROXY_PID=$!

# Wait for either process to exit
wait $CHROME_PID $PROXY_PID
