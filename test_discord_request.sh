#!/bin/bash
# Script to test Discord interaction endpoint with properly formatted requests

# Define your server URL (adjust as needed)
SERVER_URL="https://your-domain.com/api/interactions"
if [ -n "$1" ]; then
  SERVER_URL="$1"
fi

echo "🔍 Testing Discord interaction endpoint at: $SERVER_URL"
echo ""

# Generate a timestamp (Discord uses seconds since epoch)
TIMESTAMP=$(date +%s)
echo "📅 Using timestamp: $TIMESTAMP"

# Prepare a simple ping request body (type 1 is PING)
BODY='{"type":1}'
echo "📦 Using request body: $BODY"

# Run the test request with proper headers but invalid signature
# This helps debug verification issues without needing a valid signature
echo ""
echo "🧪 Sending test request with proper headers but dummy signature..."
echo ""

# Properly formatted Ed25519 signature (128 hex chars = 64 bytes)
SIGNATURE="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

curl -v -X POST "$SERVER_URL" \
  -H "Content-Type: application/json" \
  -H "X-Signature-Ed25519: $SIGNATURE" \
  -H "X-Signature-Timestamp: $TIMESTAMP" \
  -d "$BODY"

echo "\n\nUsing signature with length: ${#SIGNATURE} characters"

echo ""
echo "✅ Test complete - check the discord_verification.log file for detailed debug info"
echo ""
echo "💡 Tip: You can inspect these log entries to see exactly why verification is failing"
echo "    - Look for 'DEBUG VERIFICATION' and 'DEBUG HEADERS' entries"
echo "    - Compare the timestamp and body being used for verification"
echo "    - Check if headers are being modified by your proxy/tunnel"
echo ""
echo "To run with a different URL: ./test_discord_request.sh https://your-custom-url.com/api/interactions"
