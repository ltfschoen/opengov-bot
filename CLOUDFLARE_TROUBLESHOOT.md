# verify_endpoint.py + start_dev.py

## How Cloudflare Tunnel Works
The Cloudflare tunnel works like this:

1. The `cloudflared` process runs on your machine and establishes an outbound connection to Cloudflare's edge servers
2. When someone makes a request to your tunnel URL (e.g., aaa-ebony-explorer-parallel.trycloudflare.com), it goes to Cloudflare's servers
3. Cloudflare then forwards that request through the established tunnel back to your local `cloudflared` process
4. The `cloudflared` process then forwards the request to your local server (http://127.0.0.1:8001)


# test_server.py + start_dev.py

## Troubleshooting Checklist (test_server.py + start_dev.py)

### 1. Verify Server Configuration
- [ ] Confirm test_server.py is running with the correct port: `python test_server.py --port=8001 --debug`
- [ ] Verify server is binding to all interfaces (0.0.0.0): Check line 163 in test_server.py
- [ ] Test direct connection to the server: `curl -I http://localhost:8001/api/interactions`
- [ ] Confirm server logs show the request and 200 OK response
- [ ] Verify HEAD method handler is properly implemented in test_server.py

### 2. Verify start_dev.py Port Detection
- [ ] Check if start_dev.py correctly detects the running server: `python start_dev.py --port=8001 --tunnel-verbose`
- [ ] Confirm the log message: "Found verification server running on port 8001"
- [ ] Verify the tunnel is configured to use port 8001: "Tunnel will connect to: http://127.0.0.1:8001"
- [ ] Check if the port detection logic in find_running_verification_server() is working correctly

### 3. Test Tunnel Connectivity
- [ ] Run test_server.py and start_dev.py in separate terminals with matching ports
- [ ] Use verbose curl to test the tunnel: `curl -v https://your-tunnel-url.trycloudflare.com/api/interactions`
- [ ] Check if the request appears in the test_server.py logs
- [ ] Look for 404 errors in the tunnel logs and identify the path causing them

### 4. Alternative Tunnel Configurations
- [ ] Try direct path mapping: `cloudflared tunnel --url http://127.0.0.1:8001/api/interactions --loglevel=debug`
- [ ] Test with explicit localhost binding: `server = HTTPServer(('127.0.0.1', SERVER_PORT), SimpleHandler)` in test_server.py
- [ ] Try a different port (e.g., 8000 or 3000) in case port 8001 has issues
- [ ] Test with a minimal tunnel command outside of start_dev.py: `cloudflared tunnel --url http://127.0.0.1:8001`

### 5. Debug Request Handling
- [ ] Add more detailed logging in test_server.py to print full request details
- [ ] Modify the HEAD handler to log all headers and path information
- [ ] Test with different path variations: `/api/interactions/`, `/interactions`, etc.
- [ ] Check if the server responds differently to requests from localhost vs. from the tunnel

### 6. Network and Firewall Issues
- [ ] Check if any local firewall is blocking connections between cloudflared and your server
- [ ] Verify network interfaces and routing with: `ifconfig` or `ip addr`
- [ ] Test if the server is reachable from another local device on your network
- [ ] Try temporarily disabling any security software that might interfere

## Troubleshooting Checklist (verify_endpoint.py + start_dev.py)

### 1. Verify Local Server Operation
- [ ] Confirm verify_endpoint.py is running on the expected port: `ps aux | grep verify_endpoint`
- [ ] Test direct connection to the server: `curl -I http://localhost:8001/api/interactions`
- [ ] Verify the server returns 200 OK with proper CORS headers
- [ ] Check server logs for any errors or warnings

### 2. Verify Tunnel Configuration
- [ ] Confirm tunnel command is using the correct port: `cloudflared tunnel --url http://127.0.0.1:8001 --loglevel=debug`
- [ ] Check tunnel logs for connection errors or routing issues
- [ ] Verify the tunnel URL is correctly detected and displayed
- [ ] Test the tunnel with verbose curl: `curl -v https://your-tunnel-url.trycloudflare.com/api/interactions`

### 3. Network and Binding Issues
- [ ] Ensure verify_endpoint.py is binding to all interfaces (0.0.0.0) not just localhost
- [ ] Check if the server supports both IPv4 and IPv6 (dual-stack)
- [ ] Verify no firewall is blocking local connections between cloudflared and your server
- [ ] Test with explicit IPv4 binding: `--host=127.0.0.1` in verify_endpoint.py

### 4. Alternative Tunnel Configurations
- [ ] Try direct path mapping: `cloudflared tunnel --url http://127.0.0.1:8001/api/interactions`
- [ ] Test with different port numbers if 8001 might be restricted
- [ ] Try running cloudflared with elevated permissions if needed
- [ ] Check if cloudflared is up to date: `cloudflared update`

### 5. Discord Verification Specifics
- [ ] Ensure HEAD requests are properly handled with 200 OK responses
- [ ] Verify CORS headers include: `Access-Control-Allow-Methods: POST, GET, OPTIONS, HEAD`
- [ ] Check that `/api/interactions` path is explicitly supported
- [ ] Test with variations: `/api/interactions/` (trailing slash) and case variations


## Common Issues and Solutions

### 1. Path Routing Issue in Cloudflare Tunnel
**Problem**: The Cloudflare tunnel might not be correctly routing requests to the `/api/interactions` path. When you make a request to `https://aaa-ebony-explorer-parallel.trycloudflare.com/api/interactions`, the tunnel should forward it to `http://127.0.0.1:8001/api/interactions`, but it might be stripping the path or modifying it.

**Solution**: Try running the Cloudflare tunnel with explicit path configuration:
```bash
cloudflared tunnel --url http://127.0.0.1:8001 --loglevel=debug --no-autoupdate
```

### 2. Network Interface Binding
**Problem**: Even though your server is binding to all interfaces (0.0.0.0), there could be an issue with how the Cloudflare tunnel is connecting to it.

**Solution**: Try explicitly binding to 127.0.0.1 instead of 0.0.0.0 in your test_server.py:
```python
server = HTTPServer(('127.0.0.1', SERVER_PORT), SimpleHandler)
```

### 3. Firewall or Security Software
**Problem**: Local security software might be blocking the Cloudflare tunnel from connecting to your local server.

**Solution**: Temporarily disable any firewall or security software to test if that's the issue.

### 4. Cloudflare Configuration Issue
**Problem**: There might be a configuration issue with how Cloudflare is handling the requests.

**Solution**: Try running the tunnel with a different configuration that explicitly maps the root of the tunnel to your `/api/interactions` endpoint:
```bash
cloudflared tunnel --url http://127.0.0.1:8001/api/interactions --loglevel=debug --no-autoupdate
```

### 5. Diagnosing with curl Verbose Mode
**Approach**: To better understand what's happening, use curl in verbose mode to see the full request and response:
```bash
curl -v https://aaa-ebony-explorer-parallel.trycloudflare.com/api/interactions
```
This will show you the complete HTTP conversation, which might reveal why the 404 is occurring.

### 6. Path Handling Variations
**Problem**: Some servers handle paths differently based on case sensitivity or trailing slashes.

**Solution**: Try variations of the path:
```bash
curl -I https://aaa-ebony-explorer-parallel.trycloudflare.com/api/interactions/
curl -I https://aaa-ebony-explorer-parallel.trycloudflare.com/API/interactions
```

## Security Software Configuration

### macOS Built-in Firewall

**Required Configuration:**
1. Allow incoming connections for Python and cloudflared:
   - Open System Preferences > Security & Privacy > Firewall
   - Click the lock icon to make changes (enter your password)
   - Click "Firewall Options..."
   - Click "+" to add applications:
     - Add `/usr/local/bin/cloudflared` or wherever cloudflared is installed
     - Add your Python executable (typically `/usr/bin/python3` or from your virtual environment)
   - Set both to "Allow incoming connections"

2. Disable Stealth Mode (temporarily for testing):
   - In the same Firewall Options dialog
   - Uncheck "Enable stealth mode"
   - This allows ICMP ping responses and improves connection discovery

3. Verify configuration:
   - Run `sudo pfctl -s all | grep "block drop"` to see blocked connections
   - Check Console.app for firewall block messages

4. Force Firewall Permission Prompt:
   - When running cloudflared directly with the `--metrics` flag, it will trigger the macOS firewall prompt
   - Example: `cloudflared tunnel --url http://localhost:8001 --metrics 0.0.0.0:45678`
   - This explicitly binds to all interfaces on port 45678 for metrics
   - When prompted, click "Allow" and enter your admin password

> **Important Note**: When cloudflared is launched through start_dev.py as a subprocess, it might not trigger the firewall prompt even though it needs the same permissions. This is because macOS applies firewall rules to the application binary, not how it's invoked. If cloudflared works when run directly but fails when run through start_dev.py, this could indicate a firewall permission issue.

### AVG Security Transparent Proxy

**Required Configuration:**
1. Temporarily disable the transparent proxy:
   - Open AVG application
   - Go to Menu > Preferences > Components
   - Find "Web Shield" or "HTTPS Scanning" and disable temporarily

2. Add exceptions for localhost connections:
   - Go to AVG Preferences > Exceptions
   - Add exceptions for:
     - `127.0.0.1`
     - `localhost`
     - `::1` (IPv6 localhost)
     - Any custom domains you're using for testing

3. Disable deep packet inspection:
   - In AVG settings, find "Deep Packet Inspection" or "SSL scanning"
   - Disable this feature or add exceptions for cloudflared and Python

### ProtonVPN

**Required Configuration:**
1. Use Split Tunneling:
   - Open ProtonVPN settings
   - Go to "Connection" > "Split Tunneling"
   - Add the following to excluded applications (traffic will bypass VPN):
     - Python/python3 executable
     - cloudflared executable

2. Disable Kill Switch temporarily:
   - In ProtonVPN settings, disable "Kill Switch" feature during testing
   - This prevents network lockdown if VPN connection drops

3. Try Alternate Connection Modes:
   - If using "Secure Core" or "Tor" modes, switch to a standard VPN server
   - Try different VPN protocols (OpenVPN TCP instead of UDP)

4. Disable NetShield if enabled:
   - NetShield can block certain connections
   - Disable in ProtonVPN settings during testing

### Testing After Configuration

After making these changes, run these tests to verify connectivity:

1. Test local server directly:
```bash
curl -I http://localhost:8001/api/interactions
```

2. Check if cloudflared can connect to Cloudflare:
```bash
# Verify cloudflared is installed correctly
cloudflared --version

# Test quick tunnel connectivity (this will create a temporary tunnel)
cloudflared tunnel --no-autoupdate --url http://localhost:8001 --metrics 0.0.0.0:45678

# In another terminal, check if metrics are available (indicates cloudflared is working)
curl http://localhost:45678/metrics
```

> Note: The metrics command will start a real tunnel. Press Ctrl+C to stop it after testing.

3. Test the complete tunnel path:
```bash
curl -v https://your-tunnel-url.trycloudflare.com/api/interactions
```

4. Monitor for blocked connections:
```bash
sudo tcpdump -i lo0 port 8001
```

> **Important**: Remember to restore your security settings after testing is complete, especially firewall stealth mode and VPN kill switch features.

## Troubleshooting Error 1033 (Cloudflare Tunnel Error)

If you see an error like this when accessing your tunnel URL:

```
Error 1033: Cloudflare Tunnel error
You've requested a page on a website that is on the Cloudflare network. 
The host is configured as a Cloudflare Tunnel, and Cloudflare is currently unable to resolve it.
```

This indicates that Cloudflare can't connect to your local tunnel endpoint. Here's how to troubleshoot:

### 1. Verify the tunnel process is running

```bash
# Check if cloudflared is running
ps aux | grep cloudflared
```

### 2. Check if the tunnel is properly registered

When using quick tunnels, the tunnel URL is only valid while the cloudflared process is running. If you restart cloudflared, you'll get a new tunnel URL. Make sure you're using the most recent tunnel URL from your console output.

### 3. Check for connection issues

```bash
# Check if your local server is responding
curl -I http://localhost:8001/api/interactions

# Check if the metrics endpoint is available (if you added the metrics flag)
curl http://localhost:45678/metrics
```

### 4. Restart the tunnel with more verbose logging

```bash
cloudflared tunnel --loglevel=debug --no-autoupdate --url http://localhost:8001
```

### 5. Check for network interference

- Temporarily disable any VPN or security software
- Try connecting from a different network
- Check if your ISP or network is blocking Cloudflare's edge network
