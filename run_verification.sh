#!/bin/bash

# Script to run both verification server and tunnel with proper log output
# Created to ensure logs are visible even when running in background

# Kill any existing cloudflared processes
echo "🛑 Stopping any existing cloudflared processes..."
pkill cloudflared 2>/dev/null || true

# Kill port 8001
lsof -ti :8001 | xargs kill -9 2>/dev/null || true

# Set port and config file
PORT=8001
CONFIG_FILE="cloudflared-config.yml"

# Start verification server in background but redirect output to main terminal
echo "🚀 Starting verification server on port $PORT..."
python verify_endpoint.py --debug --port=$PORT > >(while read line; do echo "[Verify] $line"; done) 2>&1 &
VERIFY_PID=$!

# Give the verification server a moment to start
sleep 2

# Start the tunnel with the config file
echo "🚇 Starting Cloudflare tunnel with config file $CONFIG_FILE..."
python start_dev.py --port=$PORT --tunnel-verbose --config-file=$CONFIG_FILE

# If start_dev.py exits, also kill the verification server
kill $VERIFY_PID 2>/dev/null || true

echo "✅ All processes terminated"
