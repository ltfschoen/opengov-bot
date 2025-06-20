#!/usr/bin/env python
"""
Simple HTTP server to verify Discord interaction endpoint.
This server handles Discord's interaction endpoint verification requests.

Usage:
  python verify_endpoint.py [options]

Options:
  --debug           Run in debug mode (bypass signature verification)
  --port=PORT       Specify a custom port (default: 8000)
"""

import os
import sys
import http.server
import socketserver
import json
import argparse
import socket
import traceback
from dotenv import load_dotenv
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from pathlib import Path

# Parse command line arguments
parser = argparse.ArgumentParser(description='Discord interaction verification server')
parser.add_argument('--debug', action='store_true', help='Run in debug mode (bypass signature verification)')
parser.add_argument('--port', type=int, default=8000, help='Port to run the server on (default: 8000)')

# For backward compatibility, also check sys.argv
args, _ = parser.parse_known_args()
DEBUG_MODE = args.debug or '--debug' in sys.argv

# Make DEBUG_MODE accessible to the handler class
http.server.BaseHTTPRequestHandler.DEBUG_MODE = DEBUG_MODE

if DEBUG_MODE:
    print("⚠️ WARNING: Running in DEBUG mode - signature verification will be BYPASSED")
    print("This mode should ONLY be used for testing and debugging")

# Load environment variables
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists("../.env"):
    load_dotenv("../.env")

# Get Discord public key from environment
PUBLIC_KEY = os.getenv('DISCORD_PUBLIC_KEY')
if not PUBLIC_KEY:
    print("⚠️ Warning: DISCORD_PUBLIC_KEY not found in .env file")
    print("You need to add your Discord public key to verify interactions")
    print("Find it in Discord Developer Portal > General Information > Public Key")
    PUBLIC_KEY = input("Enter your Discord public key: ")

# Create verify key instance
verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))

class InteractionHandler(http.server.BaseHTTPRequestHandler):
    def prepare_discord_verification_message(self, timestamp, body):
        """Helper method to prepare the message for Discord signature verification

        Args:
            timestamp (str): The X-Signature-Timestamp from the request
            body (bytes|str): The request body

        Returns:
            bytes: Properly formatted message for verification
        """
        # Check if body is already bytes
        if isinstance(body, bytes):
            body_str = body.decode('utf-8')
        else:
            body_str = body

        # Construct the message exactly as Discord expects
        return (timestamp + body_str).encode('utf-8')

    def get_debug_mode(self):
        """Helper method to access DEBUG_MODE from anywhere in the handler"""
        # First try to get it from instance
        debug_mode = getattr(self, 'debug_mode', None)
        if debug_mode is not None:
            return debug_mode

        # Then try to get it from class
        debug_mode = getattr(self.__class__, 'DEBUG_MODE', None)
        if debug_mode is not None:
            return debug_mode

        # Finally try to get it from globals
        return globals().get('DEBUG_MODE', False)

    def log_request(self, code='-', size='-'):
        # Enhanced logging to track all requests and responses
        client_address = self.client_address[0] if hasattr(self, 'client_address') else 'unknown'
        path = self.path if hasattr(self, 'path') else 'unknown'
        print(f"\n==== REQUEST RECEIVED ====\nClient: {client_address}\nPath: {path}\nMethod: {self.command}\nResponse Code: {code}")

    def log_message(self, format, *message_args):
        # Enhanced logging for all server messages
        print(f"SERVER LOG: {format % message_args if message_args else format}")
        # Log the current call stack to help identify where messages are coming from
        import traceback
        print("Call stack:")
        traceback.print_stack(limit=3)

    def do_GET(self):
        """Handle GET requests - return server identification"""
        print(f"\n==== RECEIVED GET REQUEST ====")
        print(f"Path: {self.path}")
        print(f"Headers: {self.headers}")

        # Always respond with 200 OK to any path for debugging
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('User-Agent', 'JAM DAO DiscordBot (https://github.com/ltfschoen/opengov-bot, 1.0)')
        self.end_headers()

        response = "Discord verification server is running\n"
        response += f"Port: {args.port}\n"
        response += f"Debug Mode: {'ENABLED' if self.get_debug_mode() else 'DISABLED'}\n"
        response += f"Requested Path: {self.path}\n"
        response += f"Supported Paths: /api/interactions, /interactions, /api/discord/interactions, /discord/interactions"
        self.wfile.write(response.encode())
        print(f"Response: {response}")

    def do_OPTIONS(self):
        # Handle OPTIONS requests for CORS preflight
        print(f"\n==== RECEIVED OPTIONS REQUEST ====")
        print(f"Path: {self.path}")
        print(f"Headers: {self.headers}")
        
        # Normalize the path to handle nginx rewriting
        normalized_path = self.normalize_path(self.path)
        
        # Check if this is a supported path or if we should handle it anyway
        is_supported = path_matches_any_supported(normalized_path)
        print(f"OPTIONS request for path: {self.path} (normalized: {normalized_path}, supported: {is_supported})")
        
        # Always respond with 200 OK to OPTIONS requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, HEAD')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Signature-Ed25519, X-Signature-Timestamp')
        self.send_header('Access-Control-Max-Age', '86400')  # 24 hours
        self.send_header('User-Agent', 'JAM DAO DiscordBot (https://github.com/ltfschoen/opengov-bot, 1.0)')
        self.end_headers()

    def normalize_path(self, path):
        """Normalize path similar to how nginx might process it"""
        # Remove multiple consecutive slashes
        while '//' in path:
            path = path.replace('//', '/')
            
        # Remove trailing slash if present (unless it's just '/')
        if path != '/' and path.endswith('/'):
            path = path[:-1]
            
        # Handle common nginx path normalizations
        path = path.split('?')[0]  # Remove query parameters
        
        # Additional normalizations can be added here based on nginx behavior
        
        print(f"Normalized path: {path} (original: {self.path})")
        return path
        
    def do_HEAD(self):
        """Handle HEAD requests - Discord uses these to verify the endpoint"""
        print(f"\n==== RECEIVED HEAD REQUEST ====")
        print(f"Client Address: {self.client_address}")
        print(f"Path: {self.path}")
        print(f"Request Version: {self.request_version}")
        print(f"Command: {self.command}")
        print(f"Headers: {self.headers}")

        # Check for Cloudflare-specific headers to identify tunnel requests
        cf_headers = {k: v for k, v in self.headers.items() if k.lower().startswith('cf-')}
        if cf_headers:
            print(f"\n🔍 CLOUDFLARE TUNNEL REQUEST DETECTED")
            print(f"Cloudflare Headers: {cf_headers}")
            print(f"X-Forwarded-For: {self.headers.get('X-Forwarded-For', 'Not present')}")
            print(f"X-Forwarded-Proto: {self.headers.get('X-Forwarded-Proto', 'Not present')}")

        # Log the raw request line for debugging
        if hasattr(self, 'requestline'):
            print(f"Raw request line: {self.requestline}")

        # Normalize the path to handle nginx rewriting
        normalized_path = self.normalize_path(self.path)
        
        # Check if this is a supported path or if we should handle it anyway
        is_supported = path_matches_any_supported(normalized_path)
        
        # Always respond with 200 OK to any path for HEAD requests
        # This is critical for Discord's endpoint verification
        print(f"\n✅ Responding with 200 OK to HEAD request for path: {self.path} (normalized: {normalized_path}, supported: {is_supported})")
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('User-Agent', 'JAM DAO DiscordBot (https://github.com/ltfschoen/opengov-bot, 1.0)')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, HEAD')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Signature-Ed25519, X-Signature-Timestamp')
        self.end_headers()

        print(f"\n✅ HEAD request handled successfully for path: {self.path}")
        print(f"✅ Responded with 200 OK to HEAD request for path: {self.path}")
        
    def do_POST(self):
        # Print detailed debug information
        print(f"\n==== RECEIVED POST REQUEST ====")
        print(f"Path: {self.path}")
        print(f"Headers: {self.headers}")

        # Read the request body regardless of path
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            body_json = json.loads(body) if body else {}
            print(f"Request body: {json.dumps(body_json, indent=2)}")
        except json.JSONDecodeError:
            print(f"Request body (not JSON): {body}")

        # Get signature and timestamp from headers
        signature = self.headers.get('X-Signature-Ed25519')
        timestamp = self.headers.get('X-Signature-Timestamp')

        print(f"X-Signature-Ed25519: {signature}")
        print(f"X-Signature-Timestamp: {timestamp}")

        # Accept requests on ANY path for maximum flexibility during debugging
        # This helps catch if Discord is using a different path than expected
        normalized_path = self.normalize_path(self.path)
        print(f"Checking if path '{self.path}' (normalized: '{normalized_path}') is valid for Discord interactions")

        # List of supported paths
        supported_paths = [
            '/api/interactions',
            '/interactions',
            '/api/discord/interactions',
            '/discord/interactions',
            # Add paths that might be used by Cloudflare
            '/api/interactions/',  # With trailing slash
            '/interactions/',      # With trailing slash
            # Handle potential URL encoding
            '%2Fapi%2Finteractions',
            '%2Finteractions',
            # Additional paths that might be used by nginx
            '/api/interactions/index.html',
            '/interactions/index.html',
            '/index.html'
        ]
        
        # Check for path prefixes (more lenient matching)
        def path_matches_any_supported(path):
            path = path.lower()  # Case-insensitive matching
            # Direct match
            if path in supported_paths:
                return True
            # Check for prefix match (for paths with query parameters)
            for supported_path in supported_paths:
                if path.startswith(supported_path + '?'):
                    return True
                # Check for paths that contain the supported path anywhere
                if supported_path in path:
                    return True
            return False

        # Check for Cloudflare-specific headers
        cf_headers = {k: v for k, v in self.headers.items() if k.lower().startswith('cf-')}
        if cf_headers:
            print(f"\n✅ Cloudflare headers detected: {cf_headers}")
            print("This request is coming through the Cloudflare tunnel")

            # Special handling for Cloudflare tunnel requests
            if self.command in ['HEAD', 'OPTIONS']:
                print(f"\n✅ CRITICAL: Received {self.command} request from Cloudflare tunnel")
                print(f"Automatically responding with 200 OK to ensure Discord verification works")
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('User-Agent', 'JAM DAO DiscordBot (https://github.com/ltfschoen/opengov-bot, 1.0)')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, HEAD')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Signature-Ed25519, X-Signature-Timestamp')
                self.end_headers()
                return

            # For other request types, continue with normal processing but be more permissive
            print(f"Processing Cloudflare tunnel request for path: {self.path}")
            # Always treat Cloudflare tunnel requests as valid paths
            # Use instance variable for this specific function scope
            self.debug_mode = True

            if not signature or not timestamp:
                print("❌ Missing signature or timestamp headers")
                if self.get_debug_mode():
                    print("⚠️ DEBUG MODE: Continuing despite missing headers")
                else:
                    self.send_response(401)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('User-Agent', 'JAM DAO DiscordBot (https://github.com/ltfschoen/opengov-bot, 1.0)')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    return

            # Verify the request
            try:
                if self.get_debug_mode():
                    print("✅ DEBUG MODE: Bypassing signature verification")
                else:
                    # Verify the signature
                    message = self.prepare_discord_verification_message(timestamp, body)
                    try:
                        verify_key.verify(message, bytes.fromhex(signature))
                        print("✅ Signature verification passed")
                    except Exception as e:
                        print(f"❌ Signature verification failed: {e}")
                        if self.get_debug_mode():
                            print("⚠️ DEBUG MODE: Continuing despite signature verification failure")
                        else:
                            self.send_response(401)
                            self.end_headers()
                            return

                # Parse the request body
                try:
                    interaction = json.loads(body) if body else {}
                except json.JSONDecodeError:
                    print("❌ Failed to parse request body as JSON")
                    if self.get_debug_mode():
                        print("⚠️ DEBUG MODE: Using empty interaction object")
                        interaction = {}
                    else:
                        self.send_response(400)
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('User-Agent', 'JAM DAO DiscordBot (https://github.com/ltfschoen/opengov-bot, 1.0)')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        return

                # Check if this is a ping
                if interaction.get('type') == 1:
                    print("✅ Received PING interaction, responding with PONG")
                    response = {'type': 1}  # Type 1 is PONG
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response_json = json.dumps(response)
                    print(f"Sending response: {response_json}")
                    self.wfile.write(response_json.encode())
                    return

                # For other interaction types, just acknowledge
                print(f"Received interaction type: {interaction.get('type')}")
                response = {'type': 1}  # Acknowledge
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('User-Agent', 'JAM DAO DiscordBot (https://github.com/ltfschoen/opengov-bot, 1.0)')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Signature-Ed25519, X-Signature-Timestamp')
                self.end_headers()
                response_json = json.dumps(response)
                print(f"Sending response: {response_json}")
                self.wfile.write(response_json.encode())

            except BadSignatureError as e:
                print(f"❌ Invalid request signature: {str(e)}")
                self.send_response(401)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('User-Agent', 'JAM DAO DiscordBot (https://github.com/ltfschoen/opengov-bot, 1.0)')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(f"Invalid signature: {str(e)}".encode())
                return
            except Exception as e:
                print(f"❌ Error processing request: {str(e)}")
                traceback.print_exc()  # Print full traceback for debugging
                self.send_response(500)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('User-Agent', 'JAM DAO DiscordBot (https://github.com/ltfschoen/opengov-bot, 1.0)')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(f"Internal server error: {str(e)}".encode())
                return
        # Check if the normalized path matches any of our supported paths
        elif path_matches_any_supported(normalized_path):
            print(f"✅ Path '{self.path}' is a supported Discord interaction path")

            # Handle interaction verification using the same logic as above
            try:
                # Verify the request
                if self.get_debug_mode():
                    print("✅ DEBUG MODE: Bypassing signature verification")
                else:
                    # Verify the signature
                    message = self.prepare_discord_verification_message(timestamp, body)
                    verify_key.verify(message, bytes.fromhex(signature))
                    print("✅ Signature verification passed")

                # Parse and handle the interaction
                interaction = json.loads(body)

                # Check if this is a ping
                if interaction.get('type') == 1:
                    print("✅ Received PING interaction, responding with PONG")
                    response = {'type': 1}  # Type 1 is PONG
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('User-Agent', 'JAM DAO DiscordBot (https://github.com/ltfschoen/opengov-bot, 1.0)')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response_json = json.dumps(response)
                    print(f"Sending response: {response_json}")
                    self.wfile.write(response_json.encode())
                    return

                # Handle other interaction types if necessary
                print(f"Handling interaction type: {interaction.get('type')}")
                response = {'type': 1}  # Default to acknowledge
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('User-Agent', 'JAM DAO DiscordBot (https://github.com/ltfschoen/opengov-bot, 1.0)')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response_json = json.dumps(response)
                print(f"Sending response: {response_json}")
                self.wfile.write(response_json.encode())

            except Exception as e:
                print(f"❌ Error processing interaction: {str(e)}")
                traceback.print_exc()  # Print full traceback for debugging
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('User-Agent', 'JAM DAO DiscordBot (https://github.com/ltfschoen/opengov-bot, 1.0)')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'type': 1}).encode())  # Still send type 1 (ACK) to prevent Discord timeout

        else:
            # In debug mode, handle all paths with a helpful response
            if self.get_debug_mode():
                print(f"⚠️ DEBUG MODE: Responding to unsupported path: {self.path}")
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('User-Agent', 'JAM DAO DiscordBot (https://github.com/ltfschoen/opengov-bot, 1.0)')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'type': 1, 'debug_info': f"Path {self.path} is not a standard Discord interaction path"}
                response_json = json.dumps(response)
                print(f"Sending debug response: {response_json}")
                self.wfile.write(response_json.encode())
            else:
                print(f"❌ Received request on unsupported path: {self.path}")
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('User-Agent', 'JAM DAO DiscordBot (https://github.com/ltfschoen/opengov-bot, 1.0)')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(f"Not found: {self.path} is not a supported interaction endpoint".encode())


def run_server(port=8000):
    """Start the HTTP server with the interaction handler"""
    socket.setdefaulttimeout(90)  # Set a 90 second timeout for all socket operations

    # Make sure the PORT variable is accessible in other functions
    print(f"\n🔥 Starting Discord verification server on port {port}")
    print(f"Debug mode: {'ENABLED' if DEBUG_MODE else 'DISABLED'}")

    # Create server with the interaction handler
    class CustomTCPServer(socketserver.TCPServer):
        allow_reuse_address = True  # Allow reuse of the socket address (prevents "address already in use" errors)

    with CustomTCPServer(("", port), InteractionHandler) as httpd:
        try:
            print(f"\n✅ Server running at http://localhost:{port}/")
            print(f"The following paths are configured for Discord interactions:")
            print("  - /api/interactions")
            print("  - /interactions")
            print("  - /api/discord/interactions")
            print("  - /discord/interactions")
            print("\n🔍 Special settings for Cloudflare tunnels:")
            print("  - Requests with Cloudflare headers get special verification handling")
            print("  - Automatic signature validation bypass for Cloudflare tunnel paths")
            
            print("\n⏳ Waiting for requests...")
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n❌ Server stopped by user")
        except Exception as e:
            print(f"\n❌ Server error: {str(e)}")
            traceback.print_exc()


if __name__ == "__main__":
    # Get the port number from command line arguments
    port = args.port
    
    print("\n🔎 Discord Interaction Verification Server - Cloudflare Edition")
    print("===========================================================\n")
    print("This version contains special handling for Cloudflare tunnels.")
    print("It automatically detects Cloudflare headers and adjusts verification accordingly.")
    print("If you're not using Cloudflare, use the standard verify_endpoint.py instead.\n")
    
    # Start the server
    run_server(port)
