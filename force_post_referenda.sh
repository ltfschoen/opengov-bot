#!/bin/bash

# Script to force posting of all referenda by deleting cache and running check_referenda.py

# Print current working directory
echo "Current working directory: $(pwd)"

# Create data directory if it doesn't exist
if [ ! -d "data" ]; then
  echo "Creating data directory"
  mkdir -p data
fi

# Check if cache file exists and delete it to force treating all referenda as new
CACHE_FILE="data/governance.cache"
if [ -f "$CACHE_FILE" ]; then
  echo "Deleting existing cache file: $CACHE_FILE"
  rm -f "$CACHE_FILE"
else
  echo "No cache file found at: $CACHE_FILE"
fi

# Create an empty cache file
echo "{}" > "$CACHE_FILE"
echo "Created empty cache file at: $CACHE_FILE"

echo "DISCORD_API_KEY set: $(test -n "$DISCORD_API_KEY" && echo 'Yes' || echo 'No')"
echo "DISCORD_SERVER_ID set: $(test -n "$DISCORD_SERVER_ID" && echo 'Yes' || echo 'No')"
echo "DISCORD_FORUM_CHANNEL_ID set: $(test -n "$DISCORD_FORUM_CHANNEL_ID" && echo 'Yes' || echo 'No')"

# Run the check_referenda script
echo "Running check_referenda.py to post all referenda..."
python -m bot.scripts.check_referenda

echo "Done!"
