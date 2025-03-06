#!/bin/bash
set -e

# Default Chrome flags
CHROME_FLAGS="--no-sandbox --disable-gpu --disable-dev-shm-usage --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0"

# Check if headless mode is enabled (default: true)
if [ "${HEADLESS:-true}" = "true" ]; then
    CHROME_FLAGS="$CHROME_FLAGS --headless=new"
fi

# Check if proxy server is configured
if [ -n "$PROXY_SERVER" ]; then
    CHROME_FLAGS="$CHROME_FLAGS --proxy-server=$PROXY_SERVER"
fi

# If a command is provided, run it
if [ $# -gt 0 ]; then
    exec "$@"
else
    # Otherwise, start Chrome with the configured flags
    echo "Starting Chrome with flags: $CHROME_FLAGS"
    exec google-chrome $CHROME_FLAGS
fi 