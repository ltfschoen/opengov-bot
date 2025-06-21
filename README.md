# JAM DAO Governance Bot

![GitHub License](https://img.shields.io/github/license/JamBrains/opengov-bot)
![Supported](https://img.shields.io/badge/python-3.13.4%2B-blue)
![GitHub commits since latest release](https://img.shields.io/github/commits-since/JamBrains/opengov-bot/latest)

![alt text](./assets/jam-dao/logo_jam_dao.png)

A dedicated discussion forum within the JAM DAO Discord server, specifically designed to facilitate thoughtful and constructive conversations around ongoing proposals. This interactive platform empowers members to openly share their insights, perspectives, and opinions on each referendum prior to the submission of an official vote by the designated proxy account on behalf of the JAM DAO.

The primary objective of this forum is to foster an environment of collaboration and informed decision-making, ensuring that every voice within the community is acknowledged and taken into consideration. By harnessing the collective wisdom of your community, you can make well-informed decisions that truly represent the best interests of the entire group.

We encourage everyone to actively participate in these discussions, as your input and feedback are invaluable in shaping the direction and outcomes of the JAM DAO. Together, we can forge a stronger, more unified community that thrives on the principles of transparency, cooperation, and shared vision.

Join the public rooms of the JAM DAO Discord server here: https://discord.gg/cJRQ4KwE

![alt text](https://i.imgur.com/Ogg29qC.png)

---

## Table of Contents

- [Initial Configuration and Dependencies](#initial-configuration-and-dependencies)
  - [Environment Variables](#environment-variables-envsample)
  - [Install Prerequisite Libraries / Tooling](#install-prerequisite-libraries--tooling)
- [Test Environment](#test-environment)
  - [Components](#components)
  - [Structure](#structure)
  - [Git Hooks](#git-hooks)
    - [Pre-commit Hook](#pre-commit-hook)
    - [Installing Git Hooks](#installing-git-hooks)
  - [Test Environment Usage](#test-environment-usage)
    - [Running Tests](#running-tests)
    - [Creating Your Own Tests](#creating-your-own-tests)
- [Linting](#linting)
- [Production Environment](#production-environment)
  - [Initial Setup](#initial-setup)
  - [Installing PM2 (Process Manager)](#installing-pm2-process-manager)
    - [Daemonizing the Bot to Run 24/7 with PM2](#daemonizing-the-bot-to-run-247-with-pm2)
  - [Running Docker Version](#running-docker-version)
- [Features](#features)
  - [Autonomous Voting](#autonomous-voting)
    - [Vote Settings](#vote-settings)
      - [Kusama Vote Periods](#kusama-vote-periods)
      - [Polkadot Vote Periods](#polkadot-vote-periods)
- [Support](#support)
  - [JAM DAO](#jam-dao)
  - [ChaosDAO](#chaosdao)

---

## Initial Configuration and Dependencies

### Environment Variables [.env.sample](https://raw.githubusercontent.com/JamBrains/opengov-bot/main/.env.sample)

Rename file .env.sample to .env and populate the values, as necessary.

```shell
cp .env.sample .env
```

### Install Prerequisite Libraries / Tooling

```shell
cd opengov-bot

# Install Python (possible macOS commands shown)
brew update && brew install pyenv && brew upgrade pyenv
pyenv local 3.13.4
pyenv use 3.13.4

# Install dependencies
pip3 install -r requirements.txt
```

## Test Environment

This project includes a comprehensive test environment for testing the Discord bot with mock components. This allows you to test the bot's functionality without connecting to Discord's API.

### Components

1. **Mock Discord Objects** - Mock implementations of Discord objects like User, Member, Role, Message, etc.
2. **Mock Task Loop** - A mock implementation of Discord's task loop for testing scheduled tasks
3. **Discord Test Environment** - A test environment class that sets up a mock Discord server with channels, roles, and users
4. **Example Tests** - Unit and integration tests that demonstrate how to use the test environment

### Structure

- **Generic Discord Test Environment** (`bot/test/core/test_env_generic.py`): Contains the base `DiscordTestEnvironment` class with generic Discord mocking functionality.
- **JAM DAO Discord Test Environment** (`bot/test/core/test_env_jam_dao.py`): Contains the `JamDaoDiscordTestEnvironment` class that extends the generic environment with JAM DAO specific setup and helper methods.
- **JAM DAO Configuration** (`bot/test/fixtures/config_jam_dao.py`): Contains centralized configuration data for the JAM DAO Discord server structure (roles, channels, forum tags, etc.).

### Git Hooks

This repository includes Git hooks to help maintain code quality:

#### Pre-commit Hook

The pre-commit hook runs tests before allowing commits to ensure code quality. It:

1. Runs the JAM DAO Discord bot unit tests
2. Ensures that the test environment is working correctly
3. Prevents commits if tests fail

#### Installing Git Hooks

To install the Git hooks, run the provided script:

```bash
./install-hooks.sh
```

This will copy the hooks to your `.git/hooks` directory and make them executable.

If you need to bypass the pre-commit hook in exceptional circumstances, you can use:

```bash
git commit --no-verify -m "Your commit message"
```

### Test Environment Usage

To run the test environment and see your bot in action with mock components:

```bash
python -m bot test-env
```

This will set up a mock Discord environment and run your bot with its scheduled tasks. It will simulate user interactions and print the results.

Additional options for the test environment:

```bash
# Run with debug output
python -m bot test-env --debug

# Specify a test scenario
python -m bot test-env --scenario voting

# Set a custom duration for the test environment
python -m bot test-env --duration 120
```

#### Running Tests

You can run tests using the new CLI interface:

```bash
# Run all tests
python -m bot test --all

# Run only unit tests
python -m bot test --unit

# Run only integration tests
python -m bot test --integration

# Run API-dependent tests
python -m bot test --api

# Run specific test modules
python -m bot test --scheduled-tasks
python -m bot test --ongoing-ref

# Suppress console output during tests
python -m bot test --all --quiet

# Set a custom timeout for tests (default is 60 seconds)
python -m bot test --all --timeout 30
```

You can also use the standard unittest framework directly:

```bash
# Run all tests with unittest
python -m unittest discover bot/test

# Run a specific test file
python -m unittest bot/test/unit/test_scheduled_tasks.py
python -m unittest bot/test/ongoing_ref_call_data.py
```

#### Creating Your Own Tests

You can create your own unit tests in bot/test/unit and integration tests in bot/test/integration using the Discord test environment.

## Linting

This project uses linting tools to maintain code quality and consistency.

### Code Style

The project follows PEP 8 style guidelines for Python code. You can use tools like flake8 or pylint to check your code for style issues.

### Whitespace Linting

A custom whitespace linting tool is included to ensure consistent formatting:

```bash
# Check files for trailing whitespace and missing final newlines without modifying them
python lint_whitespace.py --check

# Fix trailing whitespace and ensure files end with newlines
python lint_whitespace.py

# Show detailed information about each processed file
python lint_whitespace.py --verbose
```

The whitespace linter checks for:
- Trailing whitespace at the end of lines
- Missing newline at the end of files

It processes files with these extensions: `.py`, `.md`, `.txt`, `.json`, `.yml`, `.yaml`, `.sh`, `.html`, `.css`, `.js`, `.ts`, `.jsx`, `.tsx`

Directories like `.git`, `__pycache__`, `venv`, etc. are automatically ignored.

---

## Development with VPS-Based Reverse Proxy and Nginx for Discord Verification

The verification server is designed to run on a VPS with Nginx as a reverse proxy, which provides a secure and reliable way to expose your Discord interaction endpoint to the internet. Discord strictly requires HTTPS for all interaction endpoints in production environments. This was adopted instead of using Cloudflare's tunnels as it always returned 404 possibly due to not supporting subdomains.

### Prerequisites

- VPS Server with SSH access
- Nginx installed on your VPS with SSL/HTTPS configured
- A domain or subdomain pointed to your VPS
- Valid SSL certificate (e.g., from Let's Encrypt) as Discord requires HTTPS for interaction endpoints

### Nginx Configuration as Reverse Proxy for Discord Interactions

Assuming your config file is `/etc/nginx/sites-available/your.domain.com` with nginx and SSL certificate setup with letsenrypt, and domain pointing to VPS IP address using Ubuntu

Backup existing Nginx configuration
```bash
sudo cp /etc/nginx/sites-available/your.domain.com /etc/nginx/sites-available/your.domain.com.backup
```

Add a configuration block to your Nginx site configuration (in the server block with `listen 443 ssl;`) as shown in [nginx_signature_fix.conf](nginx_signature_fix.conf).

After making changes to the Nginx configuration, test and reload:

```bash
sudo nginx -t
```

Check symlink exists, otherwise create it `sudo ln -s /etc/nginx/sites-available/my-site /etc/nginx/sites-enabled/`
```bash
ls -l /etc/nginx/sites-enabled/
```

Reload Nginx if the test is successful
```bash
sudo systemctl reload nginx
```

### SSH Tunnel Setup

Update your `.env` file with the following VPS-related variables:

```bash
# VPS Configuration
VPS_USER="your_vps_username"
VPS_HOST="your.domain.com"
VPS_PORT=22  # SSH port, usually 22
VPS_PRIVATE_KEY_FILE="~/.ssh/your_private_key"  # Path to your SSH key
```

To forward requests from your VPS to your local development machine using reverse tunnel:

```bash
# Connect to your VPS with port forwarding
./connect_to_vps.sh
```

This script establishes an SSH tunnel between your local machine and the VPS, forwarding traffic on port 8001 from your VPS to your local verification server.

- Set up your `.env` file with the required configuration values:

  ```bash
  # Discord Bot Configuration
  DISCORD_API_KEY='your_discord_bot_token'           # From Discord Developer Portal > Bot > Token
  DISCORD_APPLICATION_ID='your_discord_application_id'  # From Discord Developer Portal > General Info
  DISCORD_SERVER_ID='your_discord_server_id'        # Enable Developer Mode in Discord, right-click server
  DISCORD_FORUM_CHANNEL_ID='your_forum_channel_id'  # Right-click on your forum channel (e.g. #referendas) to retrieve is channel id

  # Discord Role Configuration
  DISCORD_ADMIN_ROLE='admin'                        # Role that can use administrative  (e.g. Admin)
  DISCORD_NOTIFY_ROLE='DOT-GOV'                    # Role to notify for new proposals (e.g. DOT-GOV)

  # Network Configuration (for multi-network setup)
  NETWORK_NAME='polkadot'                           # Default network name
  SYMBOL='DOT'                                      # Token symbol
  TOKEN_DECIMAL=1e10                                # Decimal precision (1e10 for Polkadot, 1e12 for Kusama)
  SUBSTRATE_WSS='wss://polkadot.dotters.network'    # RPC endpoint
  ```

  See `.env.sample` for all available configuration options. For development, the Discord-related settings and basic network configuration are the minimum required.

- Enable privileged intents in the Discord Developer Portal:
  1. Go to [Discord Developer Portal](https://discord.com/developers/applications/)
  2. Select your application
  3. Go to the "Bot" tab
  4. Under "Privileged Gateway Intents" section, enable:
     - "Message Content Intent" (allows the bot to read message content)
     - "Server Members Intent" (allows the bot to access member information)
  5. Save your changes

  If you don't see these options, make sure you're on the "Bot" tab, not the "OAuth2" tab. These intents are required for the bot to function properly with commands and member tracking.

- Set up Discord roles for the bot:
  1. Go to your Discord server
  2. Click on the server name in the top-left corner
  3. Select "Server Settings" from the dropdown menu
  4. Click on "Roles" in the left sidebar
  5. Click the "+" button to create new roles
  6. Create the following recommended roles:
     - `Admin` - For server administrators who can use bot admin commands (e.g. Permissions > Advanced Permissions > Administrator)
     - `DOT-GOV` - For notifications about new proposals
     - `dao-team-representative` - For users who can vote on referenda in the #referendas channel
     - `dao-participant` - For general DAO members who can read and comment but cannot vote
  7. To assign roles to users:
     - Right-click on a user's name in the member list or in chat
     - Select "Roles" from the context menu
     - Check the boxes next to the roles you want to assign
     - Click outside the menu to save

  Make sure to update your `.env` file with the exact role names you create (e.g., `DISCORD_ADMIN_ROLE='Admin'`)

#### Role-Based Permissions

The OpenGov bot uses Discord roles to determine permissions for different actions. Below are the recommended roles with their bot permissions and minimum required Discord permissions:

| Role | Bot Permissions | Config | Minimum Discord Permissions |
|------|----------------|--------|-----------------------------|
| `JAM-DAO-Bot` | The bot itself - manages referenda, creates threads, processes votes | Required | See [Minimum Bot Role Permissions](#minimum-bot-role-permissions) section below |
| `Admin` | Can use administrative commands like `/network add`, `/network remove`, etc. Set in `.env` as `DISCORD_ADMIN_ROLE` | Required | Administrator, or: Manage Channels, Manage Roles, Manage Webhooks, Manage Server |
| `DOT-GOV` | Gets notified when new proposals are created. Set in `.env` as `DISCORD_NOTIFY_ROLE` | Required | No special permissions needed (this is just a notification role) |
| `dao-team-representative` | Can vote on referenda in the #referendas channel. Used for quorum calculation. | Optional | View Channels, Send Messages, Send Messages in Threads, Add Reactions |
| `dao-participant` | Can read and comment in #referendas, but cannot vote | Optional | View Channels, Send Messages, Send Messages in Threads |

Customize these role names to fit the server's needs, but make sure to update the corresponding environment variables in your `.env` file.

### Discord Bot Setup

#### Discord Developer Portal Configuration

1. **OAuth2 > URL Generator**:
   - Under "Scopes", you **must** select both:
     - `bot` (allows the bot to join servers)
     - `applications.commands` (allows the bot to use slash commands)

2. **OAuth2 > Default Authorization Link**:
   - Under "Authorization Method", select "In-app Authorization"
   - Under "Scopes", you **must** check both:
     - `bot`
     - `applications.commands`

3. **Bot > Privileged Gateway Intents**:
   - Enable all three privileged intents:
     - Presence Intent
     - Server Members Intent
     - Message Content Intent

4. **Installation > Guild Installation**:
   - This is **critical**: You must add your bot to the server here
   - Add your server to the "Authorized Guilds" section
   - Set the appropriate permissions for the bot in this guild

Without completing all these steps, particularly adding the bot to the Guild Installation scope, the bot will not function correctly.

When adding the bot to your server, these permissions should be automatically requested if you use the proper OAuth2 URL.

#### Bot Setup Sequence

1. **Add Bot to Server (MUST BE DONE FIRST)**:
   - Use this OAuth2 URL format to add your bot to your server:
   ```
   https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=399164042320&scope=bot%20applications.commands
   ```
   - Replace `YOUR_CLIENT_ID` with your Discord Application ID
   - Select your server from the dropdown menu
   - Click "Authorize" and complete any verification steps
   - Discord will automatically create a role for the bot with the necessary permissions

2. **Configure Discord Developer Portal**:
   - After adding the bot to your server, go to the Installation tab
   - Add your server to the "Authorized Guilds" section
   - Set appropriate permissions
   - **Note**: This is NOT the same as "Add to Server" - you've already added the bot to your server in step 1. This step is just configuring which servers your application can interact with.

3. **Run the Bot**:
   - Only after completing steps 1 and 2, run the bot script
   - The script will guide you through setting up the interactions endpoint URL https://discord.com/developers/docs/quick-start/getting-started#adding-interaction-endpoint-url

#### Discord Interaction Endpoint URL

**Important Note**: Our server supports endpoint path (`/api/interactions`), as Discord's API actually uses `/api/interactions` when verifying your endpoint. This has been confirmed by examining network requests in the browser's developer tools.

When you change the interaction endpoint URL in the Discord Developer Portal and click "Save Changes", Discord sends a PATCH request to:
```
https://discord.com/api/v9/applications/{YOUR_APPLICATION_ID}
```

With a payload containing:
```json
{
  "interactions_endpoint_url": "https://your-domain.com/api/interactions"
}
```

#### Discord Interaction Endpoint Verification with VPS

Follow this step-by-step workflow to set up and test your Discord interaction verification by updating the Discord application:

1. **Set up your VPS with Nginx and HTTPS**
   - Install Nginx on your VPS
   - Set up SSL with Let's Encrypt or another certificate provider
   - Configure Nginx using the configuration provided in [nginx_signature_fix.conf](nginx_signature_fix.conf)
   - Test that HTTPS works on your domain

2. **Configure your local environment**
   - Update your `.env` file with VPS connection details
   - Ensure DISCORD_PUBLIC_KEY is set properly in your `.env` file

3. **Testing locally with "debug" mode**
   ```bash
   # For local testing only as "debug" mode bypasses signature verification
   python verify_endpoint.py --debug 2>&1 | tee discord_verification.log
   ```

4. **For Discord verification, run in production mode**
   ```bash
   # Start your Discord verification server locally on port 8001
   # For actual Discord verification when saving Interactions Endpoint URL in Discord Developer Portal with proper signature verification enabled
   ./run_verification.sh

   # Wait for SSH tunnel to be established

   # OR without the debug flag:
   python verify_endpoint.py 2>&1 | tee discord_verification.log
   ```

   > **Important:** When saving the endpoint URL in Discord Developer Portal, the server MUST NOT be running debug mode, or verification will fail.

5. **Create SSH tunnel to your VPS**
   ```bash
   # In another terminal connect to your VPS via SSH tunnel to forward requests
   ./connect_to_vps.sh
   ```

6. **Test the endpoint locally first**
   ```bash
   # Test with the provided script
   ./test_discord_request.sh
   ```

7. **Set the Interactions Endpoint URL in Discord Developer Portal**
   - Go to your application in the Discord Developer Portal
   - In the "General Information" section, set the "Interactions Endpoint URL" to:
     `https://your-domain.com/api/interactions`
   - Click "Save Changes" and verify that the URL passes Discord's verification

8. **Monitor the Nginx server logs on VPS for activity**
   - Watch your local verification server logs
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

This setup:
- Uses a secure HTTPS endpoint required by Discord
- Leverages your VPS as a stable public-facing server
- Forwards traffic to your local development machine for easy debugging


- Show detailed information about Discord's verification attempts

If you're experiencing issues with Discord endpoint verification, follow these steps to debug:

1. **Record Network Traffic in Browser**:
   - Open Developer Tools in your browser (F12 or right-click > Inspect)
   - Go to the Network tab
   - Click the "Record" button (red circle) to ensure network logging is active
   - Clear the current logs (trash icon) for a clean slate
   - Try saving the interaction endpoint URL in Discord Developer Portal
   - Look for the PATCH request to `discord.com/api/v9/applications/{YOUR_APPLICATION_ID}`
   - Check the response status (200 = success, 400/401 = error)
   - If there's an error, examine the response body for specific error messages

2. **Check Verification Server Logs**:
   - Run the verification server in debug mode: `python verify_endpoint.py --debug`
   - Watch for incoming requests when you save the endpoint URL
   - If you don't see any logs, the request isn't reaching your server

3. **Verify SSH Tunnel Configuration**:
   - Make sure your SSH tunnel is active and forwarding to the correct port
   - Check that your VPS domain is correctly configured with HTTPS
   - Try reconnecting the tunnel with `./connect_to_vps.sh`

4. **Handle Port Conflicts**:
   - If you see an error like `Error: Port 8000 is already in use`, run this command to kill any processes using that port:
   ```bash
   lsof -ti :8000 | xargs kill -9 2>/dev/null || true
   ```
   - This safely terminates any processes using port 8000 without showing errors if none are found
   - You can replace `8000` with any port number you're trying to use
   - Ensure your Nginx configuration is correctly forwarding to your verification server port
   - Test your domain URL directly in a browser: `https://your-domain.com/api/interactions`
   - You should see a response from your verification server

#### Troubleshooting Verification Issues

If you encounter verification issues with the Discord interaction endpoint, try the following:

1. **Check SSH Tunnel Status**:
   - Verify your SSH tunnel is active with `netstat -tuln | grep 8001` (especially if get "Connection refused" errors)
   - Make sure the tunnel is properly forwarding to the right port
   - If needed, reconnect the SSH tunnel with `./connect_to_vps.sh`

2. **Check for firewall issues on VPS**: `sudo ufw status`

3. **Check Port Consistency**:
   - Ensure your verification server is running on port 8001 (or the port specified in connect_to_vps.sh)
   - Make sure Nginx is properly configured to forward requests to this port
   - You can specify a custom port when starting the verification server with `--port=8080`

4. **Debug Signature Verification**: The verification server includes a debug mode that bypasses signature verification, which can help isolate whether the issue is with the signature verification or something else:
   ```
   python verify_endpoint.py --debug
   ```
   > Note: Remember that you must use the non-debug mode for actual Discord verification when saving the intereactions endpoint URL in the Discord Developer Portal.

5. **Test Local Endpoint**: You can test if your verification server is working correctly by sending a test request locally:
   ```bash
   python -c "import requests; print(requests.post('http://localhost:8001/api/interactions', json={'type': 1}, headers={'X-Signature-Ed25519': '0'*128, 'X-Signature-Timestamp': '0'}).status_code)"
   ```
   This should return `401` with normal mode (invalid signature) or `200` with debug mode.

   Or use the provided test script with either your local server or VPS domain:
   ```bash
   # Test against local server
   ./test_discord_request.sh http://localhost:8001/api/interactions

   # Test against your VPS domain (production)
   ./test_discord_request.sh https://your-domain.com/api/interactions
   ```

6. **Examine Request Details**: The verification server logs detailed information about incoming requests. Look for:
   - The request path (should be `/api/interactions`)
   - Headers (especially `X-Signature-Ed25519` and `X-Signature-Timestamp`)
   - Request body (should be JSON with a `type` field)
   - Any signature verification errors

7. **Check Your Public Key**: Ensure your `DISCORD_PUBLIC_KEY` in the `.env` file matches exactly with the one in your Discord Developer Portal.

8. **Verify Tunnel URL**: Make sure your tunnel URL is accessible and correctly configured in the Discord Developer Portal.

9. **Browser Network Tab**: If you see a 400 error in your browser's network tab when saving the interaction endpoint URL, it could indicate:
   - The endpoint is not reachable from Discord's servers
   - The response format is incorrect
   - The signature verification is failing
   - CORS issues preventing proper communication

10. **CORS Support**: The verification server now includes proper CORS headers to support cross-origin requests from Discord:
   - Handles OPTIONS preflight requests
   - Includes appropriate Access-Control-Allow headers
   - You can see detailed logs of these requests in the server output

11. **Multiple Endpoints**: While Discord officially uses `/api/interactions`, our server also supports `/interactions`, `/api/discord/interactions`, and `/discord/interactions` for flexibility during testing.

### Advanced Troubleshooting

#### Security Software Configuration

Security software can interfere with Discord interactions. Check the following:

##### macOS Built-in Firewall

**Required Configuration:**
1. Allow incoming connections for Python:
   - Go to System Preferences > Security & Privacy > Firewall > Firewall Options
   - Add Python and allow incoming connections

2. Ensure stealth mode doesn't block verification:
   - If using "Enable stealth mode" in Firewall Options, try temporarily disabling it during testing

##### AVG Security Transparent Proxy

**Required Configuration:**
1. Temporarily disable the transparent proxy:
   - Open AVG application
   - Go to Menu > Preferences > Components
   - Find "Web Shield" or "HTTPS Scanning" and disable temporarily

2. Add exceptions for localhost connections:
   - Go to AVG Preferences > Exceptions
   - Add exceptions for: `127.0.0.1`, `localhost`, `::1` (IPv6 localhost)

##### VPN Software (like ProtonVPN)

**Required Configuration:**
1. Use Split Tunneling:
   - Configure your VPN to exclude Python from the tunnel
   - This allows verification server traffic to bypass the VPN

2. Try disabling VPN entirely during testing

#### Testing Commands

Use these commands to verify your server is functioning properly:

```bash
# Test local verification server directly
curl -I http://localhost:8001/api/interactions

# Test signature verification with a sample payload
curl -X POST http://localhost:8001/api/interactions \
  -H "Content-Type: application/json" \
  -H "X-Signature-Ed25519: $(python -c 'print("0"*128)')" \
  -H "X-Signature-Timestamp: $(date +%s)" \
  -d '{"type":1}'

# Test a HEAD request (which Discord uses for verification)
curl -I -X HEAD http://localhost:8001/api/interactions

# Monitor local network traffic on the verification server port
sudo tcpdump -i lo0 port 8001

# Check if SSH tunnel is properly forwarding
netstat -tuln | grep 8001
```

#### Network Interface Issues

If you're having issues with the server binding correctly:

1. Verify the server is binding to the right interface:
   ```python
   # Server should bind to either all interfaces or localhost
   server = HTTPServer(('0.0.0.0', SERVER_PORT), Handler)  # All interfaces
   # OR
   server = HTTPServer(('127.0.0.1', SERVER_PORT), Handler)  # Localhost only
   ```

2. Check available network interfaces:
   ```bash
   ifconfig   # macOS/Linux
   # OR
   ip addr    # Linux
   ```

#### Bot Role Setup

1. **Manual Role Adjustment**:
   - After adding the bot, you can find its role in Server Settings > Roles
   - The role will have the same name as your bot
   - You can manually adjust its permissions if needed
   - Ensure the bot role is positioned higher in the role hierarchy than any roles it needs to manage

#### Channel Permission Setup

1. **Forum Channel (#referendas)**:
   - **Set up as a Private Channel**:
     - Right-click the channel > Edit Channel > Permissions
     - Remove access for @everyone (set all permissions to ❌)
   - **Add specific roles with permissions**:
     - `JAM-DAO-Bot` (the bot's role):
       - **General Permissions**:
         - Manage Roles
         - View Channel
         - Manage Channels (for forum tags)
         - Manage Webhooks
         - Manage Expressions (for emoji reactions)
       - **Text Permissions**:
         - Send Messages
         - Send Messages in Threads
         - Create Public Threads
         - Create Private Threads
         - Embed Links
         - Attach Files
         - Add Reactions
         - Use External Emoji
         - Mention @everyone, @here, and All Roles
         - Manage Messages (for pinning)
         - Manage Threads
         - Read Message History
         - Use Application Commands
     - `Admin`: View Channel, Send Messages, Add Reactions, Create Public Threads
     - `DOT-GOV`: View Channel, Send Messages, Add Reactions
   - **Optional additional roles** (if you want to allow these roles access):
     - `dao-team-representative`: View Channel, Send Messages, Add Reactions
     - `dao-participant`: View Channel, Send Messages

2. **Public Discussions Channel**:
   - Configure similar to the forum channel, but doesn't need thread management

3. **Summarizer Channel**:
   - Ensure the bot has Send Messages and Embed Links permissions

4. **Private Channels**:
   - For channels like `coordination-representatives` that should be restricted:
     - Remove access for @everyone
     - Add specific roles (e.g., `@dao-team-representative`) with appropriate permissions

### Run Development Script

```shell
# Start verification server
./run_verification.sh
```

### Managing Interaction Commands

1. Ensure your server is accessible via your domain name
2. Update your `.env` file with your domain URL
3. Start the OpenGov bot using the multi-network version
4. Configure your Discord application's interaction endpoint URL in the Discord Developer Portal > General Information > Interaction Endpoint URL to point to your domain's endpoint (e.g., https://your-domain.com/api/interactions)

Press Ctrl+C when you want to stop.

### Testing Bot Functionality

After the bot is running with the development script, test its functionality in Discord:

#### Required Channel Setup

- **Forum Channel**: The bot requires a Discord forum channel to post referenda. You must create this channel manually and set its ID in your `.env` file as `DISCORD_FORUM_CHANNEL_ID`.
- **Regular Channels**: Slash commands can be used in any text channel where the bot has permission to read and send messages.
- **Optional Summarizer Channel**: If you want to use the summarization feature, create a regular text channel and set its ID in your `.env` file as `DISCORD_SUMMARIZER_CHANNEL_ID`.

The bot does NOT automatically create any channels - you must set up the required channels beforehand.

#### Forum Channel Tags

For the multi-network bot, forum tags are automatically created by the bot as needed. However, there are several benefits to setting up the most common tags manually in advance:

1. **Custom Colors**: When you create tags manually, you can assign network-specific colors (e.g., Polkadot pink, Kusama black)
2. **Avoid Tag Limits**: Discord has a limit of 20 tags per forum channel - manual setup ensures your most important tags are created
3. **Immediate Availability**: Tags are ready immediately without waiting for the bot to create them

To set up tags manually:

1. Go to your Discord server and select the forum channel you created for referenda
2. Click the gear icon next to the channel name to open channel settings
3. Select "Tags" from the left sidebar
4. Click "Create Tag" and add tags following the format `[NETWORK_NAME] Origin`
5. Customize tag colors to match network branding
6. Save your changes

**Important**: The bot will automatically create tags if they don't exist, but Discord has a limit of 20 tags per forum channel. The tag format used by the bot is:

```
[NETWORK_NAME] Origin
```

For example:
- `[POLKADOT] Root`
- `[KUSAMA] Council`
- `[MOONBEAM] Fellowship`

You don't need to create all possible combinations - the bot will create them as needed. However, creating the most common ones in advance with appropriate colors improves the user experience.

When the bot creates new forum posts for referenda, it will:
- Prefix thread titles with the network name (e.g., "[Polkadot] Referendum #123")
- Automatically apply or create the appropriate tag based on the network and origin
- Include network-specific information and branding in the post

This organization system allows all referenda from multiple networks to coexist in a single forum channel while maintaining clear visual separation. Users can filter the forum by tags to view only referenda from specific networks.

> **Note**: If you add new networks to the bot later using the `/network add` command, the bot will automatically create tags for them as needed.

#### Basic Commands

- `/info` - Display bot information and statistics across all networks
- `/help` - Show available commands and their descriptions
- `/participation` - Check current participation rates for active referenda

#### Network Management Commands

The multi-network bot supports these additional commands:

- `/network list` - List all configured networks
- `/network add` - Add a new network to monitor
- `/network remove` - Remove a network from monitoring
- `/network update` - Update an existing network's configuration

These commands are available to users with the admin role specified in your `.env` file as `DISCORD_ADMIN_ROLE`.

#### Forum Monitoring

The bot should automatically:

1. Create forum posts for new referenda
2. Update existing posts with voting information
3. Add comments when significant events occur (e.g., voting period changes)

#### Troubleshooting

If commands aren't working:

- Check console output for errors
- Verify that the bot has proper permissions in your Discord server
- Ensure the bot's role is high enough in the server hierarchy
- Confirm that slash commands are registered (may take up to an hour after first invite)
- Try re-inviting the bot with the correct scopes if commands don't appear

Common errors and solutions:

1. **"Guild not found with ID 0"** or **"Invalid Discord server ID"**
   - Make sure your `.env` file has a valid `DISCORD_SERVER_ID` set
   - To get your server ID: Enable Developer Mode in Discord (Settings > Advanced), then right-click your server and select "Copy ID"
   - Update your `.env` file with this ID

2. **"Entry Point command error"**
   - This is normal for Discord applications with Entry Points
   - The bot will continue to function despite this error
   - No action needed

#### Development Tips

- Use the bot's `/info` command to check when various operations were last performed
- Monitor the console output for real-time logs of bot activities
- Check the `data/bot_stats.json` file for detailed operation statistics
- Use Discord's Developer Mode (Settings > Advanced > Developer Mode) to easily copy IDs

---

## Production Environment

### Setup
- [Discord API key, Server & Forum ID](https://github.com/ChaosDAO-org/InternalGov-2.0/wiki/1.-Initial-Setup#discord-application-api-key)
- [Enabling your Community Server & Creating a Forum Channel](https://github.com/ChaosDAO-org/InternalGov-2.0/wiki/2.-Forum-Channels#what-are-forum-channels)
- [Organising with Categories](https://github.com/ChaosDAO-org/InternalGov-2.0/wiki/3.-Channel-Categories#adding-a-category)
- [FAQ](https://github.com/ChaosDAO-org/InternalGov-2.0/wiki/99.-FAQ)


[![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/SYnpgcgfDsA/0.jpg)](https://www.youtube.com/watch?v=SYnpgcgfDsA)

### Installing PM2 (Process Manager)

> PM2 is a daemon process manager that will help you manage and keep your application/bot online 24/7
https://pm2.keymetrics.io/docs/usage/quick-start/

Install PM2 globally:

```shell
npm install pm2 -g
```

#### Daemonizing the Bot to Run 24/7 with PM2

##### Single-Network Bot (Legacy)
```shell
# change directory
cd opengov-bot/bot/

# test before daemonizing (review log file in /data/logs/governance_bot.log)
python3 main.py

# daemonize
pm2 start main.py --name polkadot_gov --interpreter python3
pm2 save

# stopping/starting & restarting pm2 process
pm2 stop polkadot_gov
pm2 start polkadot_gov
pm2 restart polkadot_gov
```

##### Multi-Network Bot (Recommended)
```shell
# ensure networks.json file is in place
mkdir -p ../data
cp utils/samples/networks.json ../data/

# test before daemonizing
python3 main_multi_network.py

# daemonize
pm2 start main_multi_network.py --name opengov_multi --interpreter python3
pm2 save

# stopping/starting & restarting pm2 process
pm2 stop opengov_multi
pm2 start opengov_multi
pm2 restart opengov_multi
```

##### PM2 Management Commands
```shell
# list process(s)
pm2 list

# view logs
pm2 logs opengov_multi

# monitor processes
pm2 monit
```

### Running Docker Version

The repository contains several Docker-related files:
- `Dockerfile` - Original Dockerfile (uses main.py for single-network)
- `docker-compose.yaml` - Original Docker Compose file
- `Dockerfile.single` - Specialized for single-network operation
- `Dockerfile.multi` - Specialized for multi-network operation
- `docker-compose.single.yaml` - Compose file for single-network
- `docker-compose.multi.yaml` - Compose file for multi-network

#### Single-Network Docker (Legacy)

```shell
# Build the image using the dedicated single-network Dockerfile
docker build -t internal-gov-2-single -f Dockerfile.single .

# Create volume for data
docker volume create internal-gov-2-data

# Run with volume mount
docker run -d \
  --name internal-gov-2-single \
  --mount source=internal-gov-2-data,target=/app/data \
  --mount type=bind,source=$(pwd)/.env,target=/app/.env \
  --restart always \
  internal-gov-2-single

# Alternative with bind mounts
docker run -d \
  --name internal-gov-2-single \
  -v ./data:/app/data \
  -v ./.env:/app/.env \
  --restart always \
  internal-gov-2-single

# Copy .env file if needed
docker cp .env internal-gov-2-single:/app/
```

Or using docker-compose with the dedicated single-network compose file:

```shell
# Use the single-network docker-compose file
docker-compose -f docker-compose.single.yaml up -d
```

#### Multi-Network Docker

Multi-network version requires a network configuration file networks.json.

1. Prepare networks.json configuration:

```shell
# Create networks.json in data directory
mkdir -p data
cp bot/utils/samples/networks.json data/
```

2. Use dedicated multi-network Dockerfile `Dockerfile.multi`:

```shell
# Build multi-network image
docker build -t internal-gov-2-multi -f Dockerfile.multi .

# Run with data volume
docker run -d \
  --name internal-gov-2-multi \
  -v ./data:/app/data \
  -v ./.env:/app/.env \
  --restart always \
  internal-gov-2-multi
```

3. Or use docker-compose with the multi-network compose file `docker-compose.multi.yaml`.

```shell
# Use the multi-network docker-compose file
docker-compose -f docker-compose.multi.yaml up -d
```

Multi-network Docker setup includes:
- Pre-configured entry point for multi-network support
- Volume mounts for persistent data and network configuration
- Integration with database services

---

## Multi-Network Support

Bot now supports monitoring multiple blockchain networks (like Polkadot and Kusama) simultaneously within a single running instance. Eliminates the need to run separate bot instances for each network.

### Key Features

- **Dynamic Network Management**: Add, remove, or update networks at runtime without restarting the bot
- **Parallel Processing**: Fetch and process referenda from all enabled networks simultaneously
- **Network-Specific Tags**: Discord threads are tagged with network names for clear identification
- **Segregated Vote Tracking**: Votes are tracked separately for each network

### Migration from Single-Network to Multi-Network

If upgrading from a previous version that only supported a single network at a time, follow these steps to migrate:

1. **Backup Data**
   ```bash
   # Create backups of data files
   cp data/vote_counts.json data/vote_counts.json.backup
   cp data/archived_votes.json data/archived_votes.json.backup
   ```

2. **Create Networks Configuration File**
   ```bash
   # Create networks.json file in data directory
   mkdir -p data
   cp bot/utils/samples/networks.json data/
   ```

3. **Migrate Existing Vote Data**
   ```bash
   # Run migration script to convert vote data to multi-network format
   # You MUST specify which network ID your existing data belongs to
   cd bot
   python utils/migrate_to_multi_network.py --network-id polkadot

   # If bot was monitoring Kusama instead of Polkadot:
   python utils/migrate_to_multi_network.py --network-id kusama
   ```

4. **Update PM2 Configuration**
   ```bash
   # Stop existing bot instance
   pm2 stop polkadot_gov

   # Start new multi-network version
   pm2 start main_multi_network.py --name opengov_multi_net --interpreter python3
   pm2 save
   ```

### Adding New Networks

Once multi-network bot is running, add new networks using Discord slash commands:

1. **Using Discord Command (Recommended)**
   - Use `/network add` command in Discord
   - Provide network_id, network_name, substrate_wss, symbol, and token_decimal
   - Only users with admin role can add networks

2. **Manually Editing Configuration**
   - Edit `data/networks.json` file
   - Add new network configuration
   - Bot will detect file changes and reload automatically

### Running Multi-Network Bot

```bash
# Test before daemonizing
cd opengov-bot/bot/
python3 main_multi_network.py

# Daemonize with PM2
pm2 start main_multi_network.py --name opengov_multi_net --interpreter python3
pm2 save
```

---

## Features

### Autonomous Voting
![alt text](https://i.imgur.com/5d0HJsY.png)

When the bot votes is dictated by `/data/vote_periods`. Each origin of a proposal has its own setting on when the first vote should be made & second. A second vote will only be made if the result differs from the first vote. If the first vote is AYE and it remains AYE on the second period then no vote will be made on the network.
[Polkadot vote periods](/data/vote_periods/polkadot.json)
[Kusama vote periods](/data/vote_periods/kusama.json)


#### Vote Settings
##### Kusama Vote Periods

| Role                | Decision Period (days) | Internal Vote Period (days) | Revote Period (days) |
|---------------------|------------------------|-----------------------------|----------------------|
| Root                | 14                     | 5                           | 10                   |
| WhitelistedCaller   | 14                     | 3                           | 10                   |
| StakingAdmin        | 14                     | 5                           | 10                   |
| Treasurer           | 14                     | 5                           | 10                   |
| LeaseAdmin          | 14                     | 5                           | 10                   |
| FellowshipAdmin     | 14                     | 5                           | 10                   |
| GeneralAdmin        | 14                     | 5                           | 10                   |
| AuctionAdmin        | 14                     | 5                           | 10                   |
| ReferendumCanceller | 7                      | 2                           | 4                    |
| ReferendumKiller    | 14                     | 2                           | 10                   |
| SmallTipper         | 7                      | 1                           | 4                    |
| BigTipper           | 7                      | 1                           | 4                    |
| SmallSpender        | 14                     | 5                           | 10                   |
| MediumSpender       | 14                     | 5                           | 10                   |
| BigSpender          | 14                     | 5                           | 10                   |
| WishForChange       | 14                     | 5                           | 10                   |
> Example:
> > A proposal is submitted with its origin designated as 'Treasurer'. Following a period of five days after its on-chain introduction, a vote is conducted in accordance with the predetermined internal outcome. Should there be a shift in the voting stance from 'AYE' to 'NAY', a subsequent vote will be executed on the tenth day of the proposal's on-chain presence. In instances where the initial decision remains unaltered and the proposal has aged ten days or more, no further on-chain voting action will be undertaken.

---

##### Polkadot Vote Periods
| Role                | Decision Period (days) | Internal Vote Period (days) | Revote Period (days) |
|---------------------|------------------------|-----------------------------|----------------------|
| Root                | 28                     | 7                           | 20                   |
| WhitelistedCaller   | 28                     | 2                           | 20                   |
| StakingAdmin        | 28                     | 7                           | 20                   |
| Treasurer           | 28                     | 7                           | 20                   |
| LeaseAdmin          | 28                     | 7                           | 20                   |
| FellowshipAdmin     | 28                     | 7                           | 20                   |
| GeneralAdmin        | 28                     | 7                           | 20                   |
| AuctionAdmin        | 28                     | 7                           | 20                   |
| ReferendumCanceller | 7                      | 2                           | 4                    |
| ReferendumKiller    | 28                     | 4                           | 20                   |
| SmallTipper         | 7                      | 2                           | 4                    |
| BigTipper           | 7                      | 2                           | 4                    |
| SmallSpender        | 28                     | 7                           | 20                   |
| MediumSpender       | 28                     | 7                           | 20                   |
| BigSpender          | 28                     | 7                           | 20                   |
| WishForChange       | 28                     | 7                           | 20                   |
> Example:
> > A proposal is submitted with its origin designated as 'AuctionAdmin'. Following a period of seven days after its on-chain introduction, a vote is conducted in accordance with the predetermined internal outcome. Should there be a shift in the voting stance from 'AYE' to 'NAY', a subsequent vote will be executed on the twentieth day of the proposal's on-chain presence. In instances where the initial decision remains unaltered and the proposal has aged ten days or more, no further on-chain voting action will be undertaken.

---

## Database Access

### Database Configuration

The bot stores referenda vote counts and user votes in PostgreSQL. The database connection is configured using the `DB_`-prefixed environment variables in your `.env` file:

### Using the CLI Database Viewer

A CLI tool is provided to quickly view database content. You'll find it at `bot/cli/view_database.py`.

```bash
# Basic usage
python bot/cli/view_database.py

# View all threads including archived
python bot/cli/view_database.py --all

# View details of a specific thread
python bot/cli/view_database.py --thread THREAD_ID

# Show vote statistics
python bot/cli/view_database.py --summary

# Get help
python bot/cli/view_database.py --help
```

### Database Access with Docker

#### Starting PostgreSQL with Docker Compose

The OpenGov Bot provides Docker Compose configurations for both single-network and multi-network modes, which include PostgreSQL:

```bash
# For single network mode
docker-compose -f docker-compose.single.yaml up -d

# For multi-network mode
docker-compose -f docker-compose.multi.yaml up -d
```

#### Accessing PostgreSQL in the Docker Container

1. **Connect to the PostgreSQL container:**

```bash
docker-compose -f docker-compose.single.yaml exec db psql -U $DB_USER -d $DB_NAME
```

2. **Copy a query script into the container and run it:**

Create a query script (e.g., `vote_query.sql`):

```sql
-- vote_query.sql
SELECT rt.thread_id, rt.aye, rt.nay, rt.recuse, rt.abstain
FROM referenda_thread rt
WHERE rt.archived = FALSE
ORDER BY rt.epoch DESC;
```

Copy and execute the script:

```bash
# Copy the script to the container
docker cp vote_query.sql opengov-bot_db_1:/tmp/

# Run the script
docker-compose -f docker-compose.single.yaml exec db psql -U $DB_USER -d $DB_NAME -f /tmp/vote_query.sql
```

#### Running Python Scripts in the Bot Container

You can run Python scripts that query the database directly in the bot container:

```bash
# Create a simple query script
cat > check_votes.py << 'EOL'
import psycopg2
import os

# Use container networking - the hostname 'db' refers to the PostgreSQL service
conn = psycopg2.connect(
    dbname=os.environ.get('DB_NAME'),
    user=os.environ.get('DB_USER'),
    password=os.environ.get('DB_PASSWORD'),
    host='db',  # Use service name from docker-compose
    port=5432
)

cursor = conn.cursor()

# Get latest vote counts
cursor.execute("""
    SELECT rt.thread_id, rt.aye, rt.nay, rt.recuse 
    FROM referenda_thread rt 
    WHERE rt.archived = FALSE 
    ORDER BY rt.epoch DESC 
    LIMIT 5
""")

print("\n=== LATEST VOTE COUNTS ===")
print("Thread ID | Aye | Nay | Recuse")
print("-" * 35)

for row in cursor.fetchall():
    thread_id, aye, nay, recuse = row
    print(f"{thread_id} | {aye} | {nay} | {recuse}")

cursor.close()
conn.close()
EOL

# Copy the script to the bot container
docker cp check_votes.py opengov-bot_bot_1:/app/

# Run the script in the container
docker-compose -f docker-compose.single.yaml exec bot python /app/check_votes.py
```

### Direct Database Query Example

For local development, you can use this Python script to query the database:

```python
#!/usr/bin/env python3
import psycopg2
import os
from dotenv import load_dotenv

# Load database connection parameters from environment variables
load_dotenv()

# Database connection parameters
db_params = {
    'dbname': os.getenv('DB_NAME', 'opengov_bot'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}

# Connect to the database
conn = psycopg2.connect(**db_params)
cursor = conn.cursor()

# Example 1: View all referendum threads
print("\n== Referendum Threads ==")
cursor.execute("SELECT thread_id, aye, nay, recuse, abstain, epoch, archived FROM referenda_thread;")
threads = cursor.fetchall()
for thread in threads:
    print(f"Thread ID: {thread[0]}")
    print(f"Votes: Aye={thread[1]}, Nay={thread[2]}, Recuse={thread[3]}, Abstain={thread[4]}")
    print(f"Epoch: {thread[5]}, Archived: {thread[6]}")
    print("---")

# Example 2: View all user votes for a specific thread
thread_id = input("\nEnter thread ID to view votes (or press Enter to skip): ")
if thread_id:
    print(f"\n== Votes for Thread {thread_id} ==")
    cursor.execute("""
        SELECT u.username, vo.description 
        FROM users u 
        JOIN vote_options vo ON u.vote_type = vo.vote_id 
        WHERE u.thread_id = %s;
    """, (thread_id,))
    votes = cursor.fetchall()
    for vote in votes:
        print(f"User: {vote[0]}, Vote: {vote[1]}")

# Example 3: Count votes by type across all threads
print("\n== Vote Summary ==")
cursor.execute("""
    SELECT vo.description, COUNT(*) 
    FROM users u 
    JOIN vote_options vo ON u.vote_type = vo.vote_id 
    GROUP BY vo.description;
""")
vote_counts = cursor.fetchall()
for vote_type in vote_counts:
    print(f"{vote_type[0]}: {vote_type[1]}")

# Close the connection
cursor.close()
conn.close()
```

## TODO

### Environment Variable Cleanup for Multi-Network Support

The following environment variables in `.env.sample` and `.env` files should be removed and their functionality incorporated to use the networks defined in `/data/networks.json` instead:

- [ ] `NETWORK_NAME` - Should be derived from selected network in networks.json
- [ ] `SYMBOL` - Should be derived from selected network in networks.json
- [ ] `TOKEN_DECIMAL` - Should be derived from selected network in networks.json
- [ ] `SUBSTRATE_WSS` - Should be derived from selected network in networks.json
- [ ] `PEOPLE_WSS` - Should be derived from selected network in networks.json

The multi-network architecture already supports configuring these values in the networks.json file, and having them duplicated in the .env file creates potential for configuration conflicts.

Note that if legacy single network support is removed then it may be necessary to remove the main.py file and use only main_multi_network.py instead.

## Support
For assistance or inquiries, please refer to the following official channels of communication:

### JAM DAO

| Platform | UID/URL |
|----------|------------------------------------------------------|
| Discord  | [![Discord](https://img.shields.io/badge/Discord-7289DA?style=for-the-badge&logo=discord&logoColor=white&link=https%3A%2F%2Fdiscord.gg%2FcJRQ4KwE)](https://discord.gg/cJRQ4KwE) |


### ChaosDAO

| Platform | User   | UID/URL                                                                                                                                                                                      |
|----------|--------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Telegram | n4droj | [![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white&link=https://t.me/n4droj)](https://t.me/n4droj)                                  |
| Discord  | n4dro  | [![Discord](https://img.shields.io/badge/Discord-7289DA?style=for-the-badge&logo=discord&logoColor=white&link=https%3A%2F%2Fdiscord.gg%2FfGJe2AWkGe)](https://discord.com/invite/fGJe2AWkGe) |
| Twitter  | n4dro  | [![Twitter](https://img.shields.io/twitter/follow/N4DRO)](https://www.x.com/N4DRO)                                                                                                           |
