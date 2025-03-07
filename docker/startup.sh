#!/bin/bash
set -x
set -e

# Default Chrome flags
DEFAULT_FLAGS="--remote-allow-origins=*\
	--no-first-run\
	--headless=new\
	--no-sandbox\
	--remote-debugging-address=0.0.0.0\
	--remote-debugging-port=9222"

	# --no-service-autorun\
	# --no-default-browser-check\
	# --homepage=about:blank\
	# --no-pings\
	# --password-store=basic\
	# --disable-infobars\
	# --disable-breakpad\
	# --disable-component-update\
	# --disable-backgrounding-occluded-windows\
	# --disable-renderer-backgrounding\
	# --disable-background-networking\
	# --disable-dev-shm-usage\
	# --disable-features=IsolateOrigins,site-per-process\
	# --disable-session-crashed-bubble\
	# --disable-search-engine-choice-screen\
	# --user-data-dir=/tmp/uc_11q83u2y\
	# --disable-features=IsolateOrigins,site-per-process\
	# --disable-session-crashed-bubble\

# Check if headless mode is enabled (default: true)
if [ "${HEADLESS:-true}" = "true" ]; then
    export CHROME_HEADLESS=true
    DEFAULT_FLAGS="$DEFAULT_FLAGS --headless=new"
else
    export CHROME_HEADLESS=false
fi

# Check if proxy server is configured
if [ -n "$PROXY_SERVER" ]; then
    DEFAULT_FLAGS="$DEFAULT_FLAGS --proxy-server=$PROXY_SERVER"
fi

# Export Chrome flags for browserless to use
export DEFAULT_FLAGS

# If a command is provided, run it
if [ $# -gt 0 ]; then
    exec "$@"
else
    # Otherwise, start Chrome and the proxy
    echo "Starting Chrome with flags: $DEFAULT_FLAGS"
    
    # Start Chrome in the background
    google-chrome $DEFAULT_FLAGS &
    CHROME_PID=$!
    
    # Wait a moment for Chrome to start
    sleep 2
    
    # Start the Node.js proxy
    echo "Starting WebSocket proxy..."
    node ./proxy.js &
    PROXY_PID=$!
    
    # Wait for either process to exit
    wait $CHROME_PID $PROXY_PID
fi 