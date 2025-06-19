#!/usr/bin/env python
"""
Simple test server for Discord interaction endpoint verification.
This server will accept any request and respond with the expected PONG response.
"""

import os
import sys
import json
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler

# Parse command line arguments
parser = argparse.ArgumentParser(description='Simple test server for Discord interaction verification')
parser.add_argument('--port', type=int, default=8000, help='Port to run the server on (default: 8000)')
parser.add_argument('--debug', action='store_true', help='Enable verbose debug output')
args = parser.parse_args()

# Global variables for configuration
DEBUG_MODE = args.debug
SERVER_PORT = args.port

# Create a custom handler with fixed logging
class SimpleHandler(BaseHTTPRequestHandler):
    # Override both logging methods to avoid the args parameter issue
    def log_message(self, format, *message_args):
        # Only log if debug mode is enabled
        if DEBUG_MODE:
            sys.stderr.write("%s - - [%s] %s\n" %
                             (self.address_string(),
                              self.log_date_time_string(),
                              format % message_args))

    def log_request(self, code='-', size='-'):
        # Only log if debug mode is enabled
        if DEBUG_MODE:
            self.log_message('"%s" %s %s',
                            self.requestline, str(code), str(size))

    def do_POST(self):
        print("\n==== RECEIVED POST REQUEST ====")
        print(f"Client Address: {self.client_address}")
        print(f"Path: {self.path}")
        print(f"Request Version: {self.request_version}")
        print(f"Command: {self.command}")
        print(f"Headers: {self.headers}")

        # Get request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else ''
        print(f"Body: {body}")

        # Check for Discord signature headers
        signature = self.headers.get('X-Signature-Ed25519')
        timestamp = self.headers.get('X-Signature-Timestamp')

        if signature and timestamp:
            print("✅ Discord signature headers found - this appears to be a Discord verification request")
            print(f"Signature: {signature}")
            print(f"Timestamp: {timestamp}")
        else:
            print("⚠️ Discord signature headers NOT found - this might not be a Discord verification request")

        # Try to parse body as JSON if it exists
        try:
            if body:
                body_json = json.loads(body)
                print(f"JSON body: {json.dumps(body_json, indent=2)}")
                # If this is a Discord ping (type 1), log it
                if body_json.get('type') == 1:
                    print("✅ Received Discord PING (type 1) - responding with PONG")
        except json.JSONDecodeError:
            print("Body is not valid JSON")

        # Always respond with the PONG response for type 1 (PING) requests
        response = {"type": 1}
        response_json = json.dumps(response)
        response_bytes = response_json.encode()

        print(f"Responding with: {response_json}")
        print(f"Response bytes: {response_bytes}")
        print(f"Response hex: {response_bytes.hex()}")

        # Send response with CORS headers
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS, GET')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Signature-Ed25519, X-Signature-Timestamp')
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_GET(self):
        print("\n==== RECEIVED GET REQUEST ====")
        print(f"Client Address: {self.client_address}")
        print(f"Path: {self.path}")
        print(f"Request Version: {self.request_version}")
        print(f"Command: {self.command}")
        print(f"Headers: {self.headers}")

        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        response = "Discord verification test server is running\n"
        response += f"Port: {SERVER_PORT}\n"
        response += f"Debug Mode: {'ENABLED' if DEBUG_MODE else 'DISABLED'}\n"
        response += f"Requested Path: {self.path}\n"
        response += "\nThis server will respond to all POST requests with {\"type\": 1} for Discord verification.\n"
        response += "Supported paths: / (root), /api/interactions, or any other path\n"
        response += "\nIf you're seeing this message, the server is working correctly!"
        self.wfile.write(response.encode())
        print(f"Response sent: {response}")

    def do_OPTIONS(self):
        print("\n==== RECEIVED OPTIONS REQUEST ====")
        print(f"Client Address: {self.client_address}")
        print(f"Path: {self.path}")
        print(f"Request Version: {self.request_version}")
        print(f"Command: {self.command}")
        print(f"Headers: {self.headers}")

        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS, GET, HEAD')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Signature-Ed25519, X-Signature-Timestamp')
        self.end_headers()
        print(f"Sent OPTIONS response with CORS headers for path: {self.path}")
        print("✅ Added HEAD to allowed methods for Discord verification")

    def do_HEAD(self):
        print("\n==== RECEIVED HEAD REQUEST ====")
        print(f"Client Address: {self.client_address}")
        print(f"Path: {self.path}")
        print(f"Request Version: {self.request_version}")
        print(f"Command: {self.command}")
        print(f"Headers: {self.headers}")

        # Always respond with 200 OK for HEAD requests regardless of path
        # This is critical for Discord's endpoint verification
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS, GET, HEAD')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Signature-Ed25519, X-Signature-Timestamp')
        self.end_headers()
        print(f"Sent HEAD response with 200 OK for path: {self.path}")
        print("✅ Discord verification should now work with this endpoint")

if __name__ == "__main__":
    print(f"\n🧪 Starting test server for Discord interaction verification on port {SERVER_PORT}...")
    print("This server will accept ANY request and respond with {\"type\": 1} for Discord verification")
    print("This server is binding to ALL interfaces (0.0.0.0) to ensure it can receive requests from both IPv4 and IPv6")
    print("Press Ctrl+C to stop the server\n")

    # Enable logging for debugging
    if DEBUG_MODE:
        import http.server
        http.server.HTTPServer.allow_reuse_address = True
        http.server.BaseHTTPRequestHandler.protocol_version = 'HTTP/1.1'

    try:
        # Explicitly bind to all interfaces (0.0.0.0) instead of '' for clarity
        server = HTTPServer(('0.0.0.0', SERVER_PORT), SimpleHandler)
        print(f"Server bound to 0.0.0.0:{SERVER_PORT} (all interfaces)")
        print(f"Local URL: http://localhost:{SERVER_PORT}")
        print(f"Network URL: http://127.0.0.1:{SERVER_PORT}")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Stopping test server")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if "Address already in use" in str(e):
            print(f"Port {SERVER_PORT} is already in use. Try a different port with --port=<port_number>")
        sys.exit(1)
