#!/bin/bash

# Script to set up a cron job for the OpenGov Bot
# This will add a cron job that runs the check_referenda.py script every hour

# Get the absolute path to the project directory
PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Default frequency (every hour)
FREQUENCY="0 * * * *"

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -f|--frequency) FREQUENCY="$2"; shift ;;
        -h|--help)
            echo "Usage: $0 [-f|--frequency CRON_PATTERN]"
            echo ""
            echo "Options:"
            echo "  -f, --frequency CRON_PATTERN   Set custom cron frequency (default: '0 * * * *' = hourly)"
            echo ""
            echo "Common cron patterns:"
            echo "  '0 * * * *'    Every hour (default)"
            echo "  '0 */2 * * *'  Every 2 hours"
            echo "  '0 */6 * * *'  Every 6 hours"
            echo "  '0 0 * * *'    Once a day at midnight"
            echo "  '*/15 * * * *' Every 15 minutes"
            exit 0
            ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

echo "Setting up cron job to run check_referenda.py with frequency: $FREQUENCY"

# Create a temporary file for the cron job
TEMP_CRON=$(mktemp)

# Export current crontab
crontab -l > "$TEMP_CRON" 2>/dev/null || echo "# OpenGov Bot cron jobs" > "$TEMP_CRON"

# Check if the cron job already exists
if grep -q "bot.scripts.check_referenda" "$TEMP_CRON"; then
    echo "Cron job for check_referenda.py already exists. Updating..."
    # Remove the existing cron job
    sed -i '/bot.scripts.check_referenda/d' "$TEMP_CRON"
fi

# Add the new cron job
echo "# OpenGov Bot - Check for new referenda" >> "$TEMP_CRON"
echo "$FREQUENCY cd $PROJECT_DIR && python -m bot.scripts.check_referenda >> $PROJECT_DIR/logs/cron_check_referenda.log 2>&1" >> "$TEMP_CRON"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_DIR/logs"

# Install the new crontab
crontab "$TEMP_CRON"

# Clean up
rm "$TEMP_CRON"

echo "Cron job installed successfully!"
echo "The bot will run with frequency: $FREQUENCY"
echo "Logs will be written to: $PROJECT_DIR/logs/cron_check_referenda.log"
echo ""
echo "To view or edit all cron jobs, run: crontab -e"
echo "To verify the cron job was added, run: crontab -l"
