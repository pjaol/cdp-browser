#!/bin/bash
# Script to build and run the Docker container

# Build the Docker image
echo "Building Docker image..."
docker build -t cdp-browser -f docker/Dockerfile .

# Run the Docker container
echo "Running Docker container..."
docker run -p 9223:9223 --rm cdp-browser

# Note: Add additional options as needed:
# - To disable headless mode: -e HEADLESS=false
# - To use a proxy: -e PROXY_SERVER=http://host:port
# - To run in detached mode: -d
# - To specify a name: --name cdp-browser-container 