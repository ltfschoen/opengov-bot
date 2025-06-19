#!/bin/bash
# Script to run the minimal verification server and cloudflared tunnel together

# Function to cleanup processes on exit
cleanup() {
    echo "Cleaning up processes..."
    pkill -f "python.*minimal_verification.py" 2>/dev/null || true
    pkill cloudflared 2>/dev/null || true
    exit 0
}

# Set up cleanup on script exit
trap cleanup EXIT INT TERM

# Stop any existing processes
echo "Stopping any existing processes..."
pkill -f "python.*minimal_verification.py" 2>/dev/null || true
pkill cloudflared 2>/dev/null || true

# Free up port 8001 if it's in use
PORT_PID=$(lsof -ti :8001 2>/dev/null)
if [ ! -z "$PORT_PID" ]; then
    echo "Port 8001 is in use by PID $PORT_PID. Stopping it..."
    kill -9 $PORT_PID
fi

# Start the minimal verification server
echo "Starting minimal verification server on port 8001..."
python minimal_verification.py --port 8001 --debug &
SERVER_PID=$!

# Wait for the server to start
sleep 2

# Check if server is running
if ! ps -p $SERVER_PID > /dev/null; then
    echo "❌ Failed to start minimal verification server"
    exit 1
fi

echo "✅ Minimal verification server started with PID: $SERVER_PID"

# Start cloudflared tunnel
echo "Starting cloudflared tunnel..."
cloudflared tunnel --url http://localhost:8001 --loglevel debug

# The script will exit and cleanup when the cloudflared process is terminated
