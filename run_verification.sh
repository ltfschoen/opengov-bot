#!/bin/bash

# Script to run the Discord verification server
# Updated to work with VPS SSH tunnel approach instead of Cloudflare

# Kill any process already using port 8001
echo "🛑 Stopping any processes using port 8001..."
lsof -ti :8001 | xargs kill -9 2>/dev/null || true

# Set port for the verification server
PORT=8001

# Start verification server
echo "🚀 Starting Discord verification server on port $PORT..."
echo "📝 This server will handle Discord interaction verification requests"
echo "🔄 The SSH tunnel (connect_to_vps.sh) will forward requests from your VPS to this server"

# Run verification server in foreground with proper error handling
python verify_endpoint.py --port=$PORT # > discord_verification_endpoint.log 2>&1

# The script will stay running until you press Ctrl+C
