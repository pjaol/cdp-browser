#!/bin/bash
set -e

# Default Chrome flags
DEFAULT_FLAGS="--no-sandbox --disable-gpu --disable-dev-shm-usage"

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
    # Otherwise, start the browserless service
    echo "Starting browserless with Chrome flags: $DEFAULT_FLAGS"
    
    # Set environment variables for browserless
    export CHROME_REFRESH_TIME=86400000
    export ENABLE_CORS=true
    export FUNCTION_ENABLE=true
    export FUNCTION_EXTERNALS=true
    export ENABLE_DEBUGGER=true
    export PREBOOT_CHROME=true
    export KEEP_ALIVE=true
    export MAX_CONCURRENT_SESSIONS=10
    export MAX_QUEUE_LENGTH=10
    export TIMEOUT=60000
    
    # Start the browserless service
    exec ./start.sh
fi 