#!/usr/bin/env python
"""
Development startup script for OpenGov Discord Bot.
Creates a Cloudflare tunnel and starts the bot for local development.
"""

import os
import re
import time
import signal
import socket
import threading
import subprocess
import requests
import sys
from pathlib import Path
from dotenv import load_dotenv

# Path to .env file
ENV_PATH = Path(__file__).parent / '.env'

def update_env_file(tunnel_url):
    """Update .env file with tunnel URL"""
    try:
        # Read current .env file
        if ENV_PATH.exists():
            with open(ENV_PATH, 'r') as f:
                env_content = f.read()
        else:
            env_content = ''

        # Check if TUNNEL_URL exists
        if re.search(r'TUNNEL_URL=.*(\r?\n|$)', env_content):
            # Replace existing TUNNEL_URL
            env_content = re.sub(r'TUNNEL_URL=.*(\r?\n|$)', f'TUNNEL_URL="{tunnel_url}"\\1', env_content)
        else:
            # Add new TUNNEL_URL
            env_content = env_content.strip() + f'\nTUNNEL_URL="{tunnel_url}"\n'

        # Write updated content back to .env file
        with open(ENV_PATH, 'w') as f:
            f.write(env_content)

        print(f"\n✅ Updated .env with TUNNEL_URL=\"{tunnel_url}\"")
        return True
    except Exception as e:
        print(f"❌ Error updating .env file: {e}")
        return False

def get_client_id():
    """Get Discord application ID from .env file"""
    load_dotenv(ENV_PATH)
    return os.getenv('DISCORD_APPLICATION_ID', 'your-application-id')

def start_tunnel(port=8000, verbose=False, config_file=None):
    """Start Cloudflare tunnel and capture the URL without blocking the main thread"""
    print("🚇 Starting Cloudflare tunnel...")

    # Initialize tunnel_url and tunnel_process
    tunnel_url = None
    tunnel_process = None

    # Enhanced debugging - check if the server is actually running on the port
    print(f"\n🔍 Verifying server is running on port {port} before starting tunnel...")
    server_running = check_server_running(port, timeout=5)
    if not server_running:
        print(f"\n⚠️ WARNING: No server detected on port {port}!")
        print("The tunnel may not work correctly if no server is running.")
        print("Consider starting the verification server first.")
    else:
        print(f"\n✅ Server confirmed running on port {port}")

    # Create command for cloudflared tunnel
    cmd = ['cloudflared', 'tunnel', '--no-autoupdate']

    # Use --metrics flag to trigger macOS firewall permission prompt if needed
    cmd.extend(['--metrics', '0.0.0.0:45678'])

    # Add URL parameter - this is the local server to forward to
    cmd.extend(['--url', f'http://127.0.0.1:{port}'])

    # Add config file if specified
    if config_file and os.path.exists(config_file):
        cmd.extend(['--config', config_file])
        print(f"🔧 Using cloudflared config file: {config_file}")

    # Add verbose flag if requested
    if verbose:
        cmd.extend(['--loglevel', 'debug'])

    # Add metrics flag to explicitly bind to all interfaces, which will trigger the firewall prompt
    # This helps ensure cloudflared has proper network permissions
    cmd.extend(['--metrics', '0.0.0.0:45678'])

    # CRITICAL: For quick tunnels, we must use the --url flag
    # CRITICAL: For quick tunnels with explicit path mapping
    # Map the specific /api/interactions path explicitly to avoid routing issues
    # This ensures the exact path is preserved when forwarding requests
    origin_url = f"http://localhost:{port}/api/interactions=/api/interactions"
    cmd.extend(['--url', origin_url])

    # Also add a general mapping for the base URL to handle other paths
    base_url = f"http://localhost:{port}"
    cmd.extend(['--url', base_url])

    # Add no-tls-verify to avoid any potential certificate issues
    cmd.append('--no-tls-verify')

    print(f"\n⚠️ IMPORTANT: Starting quick tunnel to {origin_url}")
    print(f"Full command: {' '.join(cmd)}")
    print(f"This will forward all requests including /api/interactions to your local server")

    # Test the local server directly to confirm it's working
    try:
        import requests
        test_url = f"{origin_url}/api/interactions"
        print(f"\n🔍 Testing direct connection to {test_url}...")
        response = requests.head(test_url, timeout=5)
        print(f"Direct HEAD request to {test_url}: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Local server is responding correctly to HEAD requests")
        else:
            print(f"⚠️ Local server returned status code {response.status_code} to HEAD requests")
    except Exception as e:
        print(f"⚠️ Could not connect directly to local server: {e}")
        print("This may indicate a problem with the local server, not the tunnel.")

    # Save the configuration for reference, but don't use it for the tunnel
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cloudflared-config.yml')

    # Create a basic config file for reference (not used for quick tunnels)
    basic_config = f"""# Cloudflare tunnel configuration reference
# This file is for reference only - quick tunnels use command line arguments

# For quick tunnels, use: cloudflared tunnel --url http://127.0.0.1:{port}

# For named tunnels with more complex routing, use this configuration:
tunnel: your-tunnel-name
ingress:
  # IPv4 specific mapping for /api/interactions
  - hostname: "*"
    service: http://127.0.0.1:{port}
    path: /api/interactions
    originRequest:
      noTLSVerify: true

  # IPv6 specific mapping for /api/interactions
  - hostname: "*"
    service: http://[::1]:{port}
    path: /api/interactions
    originRequest:
      noTLSVerify: true

  # IPv4 fallback for all other paths
  - hostname: "*"
    service: http://127.0.0.1:{port}
    originRequest:
      noTLSVerify: true

  # IPv6 fallback for all other paths
  - hostname: "*"
    service: http://[::1]:{port}
    originRequest:
      noTLSVerify: true
"""

    with open(config_path, 'w') as f:
        f.write(basic_config)

    print(f"Created reference config file at {config_path} (not used for quick tunnels)")
    print(f"Running tunnel command: {' '.join(cmd)}")

    # Start the cloudflared tunnel process
    try:
        tunnel_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )

        # Wait for the tunnel URL to appear in the output
        print("🔍 Waiting for tunnel URL to appear in output...")
        print("This may take up to 30 seconds. Looking for https://*.trycloudflare.com")
        url_found = False
        start_time = time.time()

        # Track 404 errors and their causes
        error_404_count = 0
        error_paths = set()

        while time.time() - start_time < 30:  # Wait up to 30 seconds
            line = tunnel_process.stdout.readline()
            if not line:
                time.sleep(0.1)
                continue

            print(f"[Tunnel] {line.strip()}")

            # Look for 404 errors in the tunnel logs
            if "404 Not Found" in line or "http_status:404" in line:
                error_404_count += 1
                print(f"\n⚠️ DETECTED 404 ERROR in tunnel logs (#{error_404_count})")

                # Try to extract the path that caused the 404
                path_match = re.search(r'path=([^ ]+)', line)
                if path_match:
                    path = path_match.group(1)
                    error_paths.add(path)
                    print(f"Path causing 404: {path}")

                # Look for origin service info
                origin_match = re.search(r'originService=([^ ]+)', line)
                if origin_match:
                    origin = origin_match.group(1)
                    print(f"Origin service: {origin}")

                # Check for ingress rule info
                ingress_match = re.search(r'ingressRule=(\d+)', line)
                if ingress_match:
                    rule = ingress_match.group(1)
                    print(f"Ingress rule: {rule}")

                print("This indicates the local server is not responding correctly to the request")
                print("Check that your server is handling this path correctly")

            # Look for the tunnel URL in the output
            if 'https://' in line and 'trycloudflare.com' in line:
                print(f"DEBUG: Found potential tunnel URL line: {line.strip()}")

                # Try to extract the URL with regex
                pattern = r'https://[\w\-]+([\-\w]+)*\.trycloudflare\.com'
                match = re.search(pattern, line)

                if match:
                    tunnel_url = match.group(0)
                    print(f"DEBUG: Matched URL: {tunnel_url}")
                    url_found = True
                    update_env_file(tunnel_url)
                    print(f"\n✅ Updated .env with TUNNEL_URL=\"{tunnel_url}\"")
                    break

        # If we didn't find a URL but the tunnel is running, continue anyway
        if not url_found:
            print("⚠️ Timed out waiting for tunnel URL, but tunnel appears to be running")
            print("You can check the tunnel output manually for the URL")

        # Start a background thread to continue reading output
        def keep_reading_output():
            while tunnel_process.poll() is None:
                output = tunnel_process.stdout.readline()
                if output:
                    if verbose or '404' in output or 'error' in output.lower():
                        print(f"[Tunnel] {output.strip()}")
                time.sleep(0.1)

        # Start the background thread
        output_thread = threading.Thread(target=keep_reading_output)
        output_thread.daemon = True
        output_thread.start()

        return tunnel_url, tunnel_process

    except Exception as e:
        print(f"❌ Error starting tunnel: {e}")
        return None, None

def start_bot():
    """Start OpenGov Discord bot"""
    print("🤖 Starting OpenGov Discord bot...")

    try:
        # Get the project root directory
        project_root = os.path.dirname(os.path.abspath(__file__))

        # Load environment variables from .env file
        env_path = os.path.join(project_root, '.env')
        if os.path.exists(env_path):
            print(f"✅ Loading environment from: {env_path}")
            from dotenv import dotenv_values
            env_vars = dotenv_values(env_path)
            # Merge with current environment
            env = {**os.environ, **env_vars, 'PYTHONPATH': project_root}
        else:
            print(f"⚠️ Warning: .env file not found at {env_path}")
            env = dict(os.environ, PYTHONPATH=project_root)

        # Use multi-network version of bot
        bot_process = subprocess.Popen(
            ['python', 'bot/main_multi_network.py'],
            cwd=project_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # Print bot output in real-time
        for line in bot_process.stdout:
            print(line.strip())

        return bot_process
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        return None

def handle_exit(tunnel_process, bot_process):
    """Handle clean exit of all processes"""
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down...")
        if bot_process and bot_process.poll() is None:
            bot_process.terminate()
            print("✅ Bot stopped")

        if tunnel_process and tunnel_process.poll() is None:
            tunnel_process.terminate()
            print("✅ Tunnel stopped")

        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def is_port_in_use(port):
    """Check if a port is already in use using both IPv4 and IPv6 socket connections"""
    # Try IPv4 first
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10)  # Short timeout to avoid hanging
            result = s.connect_ex(('127.0.0.1', port))
            if result == 0:
                print(f"Socket check: Port {port} is in use (IPv4)")
                return True
    except Exception as e:
        print(f"IPv4 socket check error: {e}")

    # Then try IPv6
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
            s.settimeout(10)  # Short timeout to avoid hanging
            result = s.connect_ex(('::1', port))
            if result == 0:
                print(f"Socket check: Port {port} is in use (IPv6)")
                return True
    except Exception as e:
        print(f"IPv6 socket check error: {e}")

    print(f"Socket check: Port {port} is NOT in use")
    return False

def check_server_running(port=8000, timeout=5):
    """Check if a server is running on the given port with a shorter timeout to avoid hangs."""
    # Try multiple ways to connect to the server, prioritizing the Discord API endpoint
    # Discord sends verification requests to /api/interactions, so this is the most important endpoint to check

    # First try the Discord API endpoints with both IPv4 and IPv6 support using HEAD requests
    # Discord uses HEAD requests for initial verification
    api_urls = [
        f"http://localhost:{port}/api/interactions",  # This can resolve to IPv4 or IPv6
        f"http://127.0.0.1:{port}/api/interactions",  # IPv4 specific
        f"http://[::1]:{port}/api/interactions"      # IPv6 specific
    ]

    print(f"\n🔍 Checking for Discord verification server on port {port}...")
    print(f"Discord requires the /api/interactions endpoint for verification")
    print(f"Testing with HEAD requests (what Discord uses for verification)...")

    # First check the critical Discord API endpoints with HEAD requests
    for url in api_urls:
        print(f"Trying Discord endpoint with HEAD request: {url}...")
        try:
            response = requests.head(url, timeout=timeout)
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                print(f"✅ Server running on {url}: HTTP {response.status_code}")
                print(f"✅ VERIFIED: Found working Discord verification server on port {port}")
                print(f"This server will handle Discord interaction verification HEAD requests")
                return True
            else:
                print(f"⚠️ Server responded with non-200 status: {response.status_code}")
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Connection error for {url}: {e}")
        except requests.exceptions.Timeout as e:
            print(f"⚠️ Timeout connecting to {url}: {e}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to connect to {url}: {e}")

    # Try POST requests with a Discord ping payload
    print("\nTrying POST requests with Discord ping payload...")
    # Discord ping payload (type 1)
    ping_payload = {"type": 1}
    # Headers that Discord would send
    headers = {
        'Content-Type': 'application/json',
        'X-Signature-Ed25519': 'test_signature',  # Dummy value
        'X-Signature-Timestamp': str(int(time.time()))  # Current timestamp
    }

    for url in api_urls:
        print(f"Trying Discord endpoint with POST request: {url}...")
        try:
            response = requests.post(url, json=ping_payload, headers=headers, timeout=timeout)
            print(f"Response status: {response.status_code}")
            try:
                response_json = response.json()
                print(f"Response JSON: {response_json}")
                # Check if the response is a valid Discord response (type 1 = PONG)
                if response.status_code == 200 and response_json.get('type') == 1:
                    print(f"✅ Server running on {url}: HTTP {response.status_code}")
                    print(f"✅ VERIFIED: Found working Discord verification server on port {port}")
                    print(f"Server correctly responded to ping with pong!")
                    return True
            except ValueError:
                print(f"Response was not valid JSON: {response.text[:100]}" + ('...' if len(response.text) > 100 else ''))
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Connection error for {url}: {e}")
        except requests.exceptions.Timeout as e:
            print(f"⚠️ Timeout connecting to {url}: {e}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to connect to {url}: {e}")

    # Try GET requests as fallback
    print("\nTrying GET requests as fallback...")
    for url in api_urls:
        print(f"Trying Discord endpoint with GET request: {url}...")
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                print(f"✅ Server running on {url}: HTTP {response.status_code}")
                print(f"Server response: {response.text[:100]}..." if len(response.text) > 100 else f"Server response: {response.text}")
                print(f"✅ VERIFIED: Found working Discord verification server on port {port}")
                print(f"This server will handle Discord interaction verification requests")
                return True
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Connection error for {url}: {e}")
        except requests.exceptions.Timeout as e:
            print(f"⚠️ Timeout connecting to {url}: {e}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to connect to {url}: {e}")

    # If API endpoints don't work, try the base URLs as fallback
    base_urls = [
        f"http://localhost:{port}",      # This resolves to both IPv4 and IPv6 depending on system config
        f"http://127.0.0.1:{port}",      # IPv4 specific
        f"http://[::1]:{port}"           # IPv6 specific
    ]

    print("Trying base URLs as fallback...")
    for url in base_urls:
        print(f"Trying {url}...")
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                print(f"✅ Server running on {url}: HTTP {response.status_code}")
                print(f"Server response: {response.text[:100]}..." if len(response.text) > 100 else f"Server response: {response.text}")
                print(f"✅ VERIFIED: Found working server on port {port}")
                print(f"WARNING: Server responded on base URL but not on /api/interactions")
                print(f"Discord verification may fail if /api/interactions is not properly handled")
                return True
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Connection error for {url}: {e}")
        except requests.exceptions.Timeout as e:
            print(f"⚠️ Timeout connecting to {url}: {e}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to connect to {url}: {e}")

    # Last resort: check if the port is in use at the socket level
    if is_port_in_use(port):
        print(f"✅ Port {port} is in use according to socket check")
        print(f"Assuming verification server is running on port {port}")
        return True

    # If we get here, we couldn't connect to any URL
    return False

def find_running_verification_server(custom_port=None):
    """Check if a verification server is already running on common ports or a custom port"""
    common_ports = [8000, 8001, 3000]

    # If a custom port is specified, check it first
    if custom_port and custom_port not in common_ports:
        common_ports.insert(0, custom_port)

    print("\n🔍 Checking for running verification servers...")
    print(f"Checking ports: {', '.join(map(str, common_ports))}")

    for port in common_ports:
        print(f"\n🔍 Checking port {port}...")
        if check_server_running(port):
            print(f"✅ Found verification server running on port {port}")
            print(f"✅ IMPORTANT: Will use port {port} for the tunnel")
            return port
        else:
            print(f"❌ No verification server found on port {port}")

    print("\n❌ No verification server found on any common ports")

    # If no ports found, check specifically for verify_endpoint.py process
    try:
        if sys.platform.startswith('win'):
            # Windows
            try:
                output = subprocess.check_output('tasklist /FI "IMAGENAME eq python*" /FO CSV', shell=True).decode()
                if 'verify_endpoint.py' in output:
                    print("Found verify_endpoint.py process but couldn't determine port")
                    return 8000  # Default port for verify_endpoint.py
            except subprocess.CalledProcessError:
                pass
        else:
            # Unix-like
            try:
                output = subprocess.check_output('ps aux | grep verify_endpoint.py | grep -v grep', shell=True).decode()
                if output:
                    print("Found verify_endpoint.py process but couldn't determine port")
                    return 8000  # Default port for verify_endpoint.py
            except subprocess.CalledProcessError:
                pass
    except Exception as e:
        print(f"Error checking for verify_endpoint.py process: {e}")

    return None

def kill_process_on_port(port):
    """Kill any process using the specified port"""
    try:
        # Find process using the port
        if sys.platform.startswith('win'):
            # Windows
            result = subprocess.run(
                f"netstat -ano | findstr :{port}",
                shell=True,
                capture_output=True,
                text=True
            )
            if result.stdout:
                pid = result.stdout.strip().split()[-1]
                subprocess.run(f"taskkill /F /PID {pid}", shell=True)
                return True
        else:
            # macOS/Linux
            result = subprocess.run(
                f"lsof -i :{port} -t",
                shell=True,
                capture_output=True,
                text=True
            )
            if result.stdout:
                pid = result.stdout.strip()
                subprocess.run(f"kill -9 {pid}", shell=True)
                return True
        return False
    except Exception as e:
        print(f"Error killing process on port {port}: {e}")
        return False

def run_verification_server(tunnel_url, debug_mode=False, port=8000):
    """Run the verification server for Discord interaction endpoint"""
    print("\n🔍 Starting Discord verification server...")

    # Check if the specified port is already in use
    if is_port_in_use(port):
        print(f"⚠️ Port {port} is already in use. Attempting to free it...")
        if kill_process_on_port(port):
            print(f"✅ Successfully freed port {port}")
            # Give it a moment to fully release
            time.sleep(1)
        else:
            print(f"❌ Failed to free port {port}. Trying an alternative port...")
            # Try an alternative port
            alt_port = port + 1
            while is_port_in_use(alt_port) and alt_port < port + 10:  # Try up to 10 ports
                alt_port += 1

            if alt_port < port + 10:
                print(f"✅ Found available port: {alt_port}")
                port = alt_port
            else:
                print("❌ Could not find an available port. Please manually close applications using these ports.")
                return False

    # Start the verification server
    cmd = [sys.executable, 'verify_endpoint.py', f'--port={port}']
    if debug_mode:
        cmd.append('--debug')
        print("🐛 Running in DEBUG mode - signature verification will be bypassed")

    print(f"Starting verification server on port {port}")
    verification_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Give it a moment to start
    time.sleep(2)

    # Start a thread to read and print output from the verification server
    def read_output(process):
        for line in process.stdout:
            print(f"[Verification] {line.strip()}")

    output_thread = threading.Thread(target=read_output, args=(verification_process,), daemon=True)
    output_thread.start()

    # Display instructions for Discord Developer Portal
    client_id = get_client_id()
    print("\n==== IMPORTANT: DISCORD CONFIGURATION ====")
    print(f"Tunnel URL: {tunnel_url}")
    print(f"Verification Server Port: {port}")
    print("\nFollow these steps to verify your Discord interaction endpoint:")
    print("1. Go to Discord Developer Portal:")
    print(f"   https://discord.com/developers/applications/{client_id}/bot")
    print("2. In the 'General Info > Interactions Endpoint URL' field, enter:")
    print(f"   {tunnel_url}/api/interactions")
    print("   ⚠️ IMPORTANT: Discord's API actually uses this specific path when verifying")
    print("3. Click 'Save Changes' - it should verify successfully")
    print("\nIf verification fails, check:")
    print("- Is the verification server running? (python verify_endpoint.py --debug)")
    print("- Is the tunnel forwarding to the correct port?")
    print("- Are you using the correct endpoint path? (/api/interactions)")
    print("- Check browser network logs for the actual request Discord is making")

    if debug_mode:
        print("\n🐛 DEBUG MODE IS ENABLED - Discord verification will succeed even with invalid signatures")
        print("   This is useful for testing but should NOT be used in production")

    # Prompt user to continue
    input("\n⏸️  Press Enter after you've successfully saved the endpoint URL...\n")

    # Terminate the verification server
    if verification_process and verification_process.poll() is None:
        verification_process.terminate()
        print("✅ Verification server stopped")

    return True

def main():
    """Main function to coordinate the processes"""
    # Parse command line arguments
    debug_mode = '--debug' in sys.argv
    tunnel_verbose = '--tunnel-verbose' in sys.argv

    # Check for custom port in arguments
    port = 8000  # Default port
    config_file = None  # Default: no config file

    for arg in sys.argv:
        if arg.startswith('--port='):
            try:
                port = int(arg.split('=')[1])
                print(f"Using custom port: {port}")
            except (ValueError, IndexError):
                print("⚠️ Invalid port specified, using default port 8000")
        elif arg.startswith('--config-file='):
            config_file = arg.split('=')[1]
            print(f"Using cloudflared config file: {config_file}")
            if not os.path.exists(config_file):
                print(f"⚠️ Warning: Config file {config_file} not found!")

    if tunnel_verbose:
        print("💬 Tunnel verbose logging enabled - you'll see detailed request/response logs")
        print("This will help diagnose issues with Discord's verification requests")
        print("Look for [Tunnel REQUEST] log entries when saving the endpoint URL in Discord")
        print()

    # Check if a verification server is already running
    verification_port = find_running_verification_server(custom_port=port)

    # If a verification server is found, use its port for the tunnel
    if verification_port:
        print(f"\n✅ Using detected verification server on port {verification_port} for tunnel")
        port = verification_port
        existing_port = verification_port  # Track that we're using an existing server
        print(f"\n✅ IMPORTANT: Setting tunnel to use port {port} for the verification server")
    else:
        existing_port = None  # No existing server found
        print(f"\n⚠️ No existing verification server found. Will use port {port} for new server.")

    # Double check that we're using the right port
    print(f"\n🔍 Final port configuration: {port}")
    print(f"Tunnel will connect to: http://127.0.0.1:{port}")
    print(f"Verification server status: {'DETECTED on port ' + str(existing_port) if existing_port else 'NOT DETECTED'}")
    print(f"Will create new verification server: {'NO' if existing_port else 'YES'}")
    print("")

    # Start tunnel and wait for URL
    tunnel_url, tunnel_process = start_tunnel(port, verbose=tunnel_verbose, config_file=config_file)
    if not tunnel_url:
        print("⚠️ Could not automatically detect tunnel URL. Continuing anyway...")
        print("You can manually check the Cloudflare tunnel output for the URL.")
        print("Look for a line containing 'https://*.trycloudflare.com'")
        tunnel_url = "<Check Cloudflare output for URL>"
    else:
        print(f"\n✅ Successfully started tunnel at: {tunnel_url}")
        print(f"Tunnel is forwarding to http://127.0.0.1:{port}")

    # Double-check if we can connect to the local server
    server_running = False
    print(f"\n🔍 Testing connection to local server at http://127.0.0.1:{port}...")

    # Try multiple endpoints with increasing timeouts
    endpoints = [
        ("/", 10),                      # Base URL with longer timeout
        ("/api/interactions", 10)       # Discord endpoint with longer timeout
    ]

    for endpoint, timeout in endpoints:
        try:
            print(f"Trying {endpoint} with {timeout}s timeout...")
            response = requests.get(f"http://127.0.0.1:{port}{endpoint}", timeout=timeout)
            print(f"✅ Successfully connected to server at {endpoint}: HTTP {response.status_code}")
            print(f"Server response: {response.text[:100]}" + ('...' if len(response.text) > 100 else ''))
            server_running = True
            break
        except requests.exceptions.Timeout:
            print(f"⏱️ Connection timed out after {timeout}s. Server might be busy.")
        except requests.exceptions.ConnectionError:
            print(f"🔌 Connection error. Server might not be listening on port {port}.")
        except requests.RequestException as e:
            print(f"❌ Error connecting to server: {e}")

    # If we couldn't connect to the server
    if not server_running:
        # Try a simple socket check as last resort
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            result = s.connect_ex(('127.0.0.1', port))
            s.close()
            if result == 0:
                print(f"✅ Port {port} is open, but HTTP requests are timing out.")
                print("This suggests a server is running but might be busy or not responding properly.")
                server_running = True
            else:
                print(f"❌ Port {port} is not open. No server is listening.")
        except Exception as e:
            print(f"❌ Socket check failed: {e}")

        if not server_running:
            print("\nThe tunnel will not work correctly without a server to forward to.")
            print("Would you like to start a verification server now? (y/n)")
            choice = input("> ").strip().lower()
            if choice == 'y':
                existing_port = None  # Force starting a new verification server
            else:
                print("\n⚠️ Continuing without a verification server. Discord verification will likely fail.")
                print("You can manually start one with: python verify_endpoint.py --debug")

    # Wait a moment for the tunnel to fully establish
    time.sleep(2)

    # Always display the Discord configuration instructions
    client_id = get_client_id()
    print("\n==== IMPORTANT: DISCORD CONFIGURATION ====")
    print(f"Tunnel URL: {tunnel_url}")
    print(f"Verification Server Port: {port}" + (" (already running)" if existing_port else ""))
    print("\nFollow these steps to verify your Discord interaction endpoint:")
    print("1. Go to Discord Developer Portal:")
    print(f"   https://discord.com/developers/applications/{client_id}/bot")
    print("2. In the 'General Info > Interactions Endpoint URL' field, enter:")
    print(f"   {tunnel_url}/api/interactions")
    print("   ⚠️ IMPORTANT: Discord's API actually uses this specific path when verifying")
    print("3. Click 'Save Changes' - it should verify successfully")

    # If we're using an existing server, we don't need to run the verification server
    # Just prompt the user to continue after they've verified the endpoint
    input("⏸️  Press Enter after you've successfully saved the endpoint URL...")

    # Now start the actual bot
    print("🤖 Starting OpenGov Discord bot...")

    # Start bot
    bot_process = start_bot()
    if not bot_process:
        print("❌ Failed to start bot. Exiting.")
        if tunnel_process and tunnel_process.poll() is None:
            tunnel_process.terminate()
        return 1

    # Set up clean exit handler
    handle_exit(tunnel_process, bot_process)

    print("\n✅ Development environment is running")
    print("Press Ctrl+C to stop all processes")

    # Keep script running
    try:
        bot_process.wait()
    except KeyboardInterrupt:
        pass

    return 0

if __name__ == "__main__":
    sys.exit(main())
