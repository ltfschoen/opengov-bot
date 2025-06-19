#!/bin/bash
# Script to establish a secure SSH tunnel from local machine to VPS
# This creates a reverse tunnel so your VPS can forward requests to your local server

# Load environment variables from .env file
if [ -f .env ]; then
    echo "Loading VPS configuration from .env file"
    source .env
else
    echo "Error: .env file not found. Please create one with VPS_USER and VPS_HOST defined."
    exit 1
fi

# Check required variables
if [ -z "$VPS_USER" ] || [ -z "$VPS_HOST" ]; then
    echo "Error: VPS_USER and VPS_HOST must be defined in your .env file."
    exit 1
fi

# Configuration
LOCAL_PORT=8001
REMOTE_PORT=8001

# Use VPS_PORT from .env if defined, otherwise default to 22
SSH_PORT=${VPS_PORT:-22}

# Use VPS_PRIVATE_KEY_FILE from .env if defined, otherwise use default
SSH_KEY_PATH=${VPS_PRIVATE_KEY_FILE:-"$HOME/.ssh/id_rsa"}

# Expand ~ in SSH key path if present
SSH_KEY_PATH=${SSH_KEY_PATH/#\~/$HOME}

# Check if autossh is installed
if ! command -v autossh &> /dev/null; then
    echo "autossh is not installed. Installing it now:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install autossh
    elif [[ -f /etc/debian_version ]]; then
        sudo apt-get update && sudo apt-get install -y autossh
    elif [[ -f /etc/redhat-release ]]; then
        sudo yum install -y autossh
    else
        echo "Please install autossh manually for your system"
        exit 1
    fi
fi

# Create logs directory
mkdir -p logs

echo "Establishing secure SSH tunnel to VPS..."
echo "Local port $LOCAL_PORT will be exposed as port $REMOTE_PORT on $VPS_HOST"
echo "Press Ctrl+C to stop the tunnel"

# Install `autossh` for a more persistent solution
# Using autossh for reliable connection
autossh -M 0 -N -R $REMOTE_PORT:localhost:$LOCAL_PORT -i "$SSH_KEY_PATH" -p $SSH_PORT $VPS_USER@$VPS_HOST -o "ServerAliveInterval=60" -o "ServerAliveCountMax=3" -v

# Regular ssh alternative if autossh doesn't work
# Create secure SSH tunnel from local machine to forward traffic from VPS to local machine since local machine might be behind NAT.
# ssh -N -R $REMOTE_PORT:localhost:$LOCAL_PORT -i "$SSH_KEY_PATH" -p $SSH_PORT $VPS_USER@$VPS_HOST
