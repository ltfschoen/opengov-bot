#!/bin/bash
# Script to run the simple proxy server and cloudflared tunnel together

# Function to cleanup processes on exit
cleanup() {
    echo "Cleaning up processes..."
    pkill -f "python.*simple_proxy.py" 2>/dev/null || true
    pkill cloudflared 2>/dev/null || true
    exit 0
}

# Set up cleanup on script exit
trap cleanup EXIT INT TERM

# Stop any existing processes
echo "Stopping any existing processes..."
pkill -f "python.*simple_proxy.py" 2>/dev/null || true
pkill cloudflared 2>/dev/null || true

# Make sure the verification server is running on port 8001
if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/api/interactions; then
    echo "⚠️  Warning: Verification server doesn't seem to be running on port 8001"
    echo "Please start it first with: python verify_endpoint.py --port 8001"
    exit 1
fi

# Start the proxy server on port 8002
echo "Starting proxy server on port 8002..."
python simple_proxy.py --port 8002 --target http://localhost:8001 --debug &
PROXY_PID=$!

# Wait for the proxy server to start
sleep 2

# Check if proxy server is running
if ! ps -p $PROXY_PID > /dev/null; then
    echo "❌ Failed to start proxy server"
    exit 1
fi

echo "✅ Proxy server started with PID: $PROXY_PID"

# Start cloudflared tunnel pointing to the proxy server
echo "Starting cloudflared tunnel to proxy server..."
cloudflared tunnel --url http://localhost:8002 --loglevel debug

# The script will exit and cleanup when the cloudflared process is terminated
