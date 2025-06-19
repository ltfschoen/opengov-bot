#!/usr/bin/env python
"""
Minimal Discord verification server using Python's built-in HTTP server.
This server only implements the bare minimum needed for Discord verification.
"""

import http.server
import socketserver
import argparse
import sys
import os

# Parse command line arguments
parser = argparse.ArgumentParser(description='Minimal Discord verification server')
parser.add_argument('--port', type=int, default=8001, help='Port to run the server on')
parser.add_argument('--debug', action='store_true', help='Enable debug mode')
args = parser.parse_args()

PORT = args.port
DEBUG = args.debug

class MinimalVerificationHandler(http.server.SimpleHTTPRequestHandler):
    """Minimal handler that only implements what Discord needs for verification"""

    def log_message(self, format, *message_args):
        """Override to add colored logging"""
        if DEBUG:
            sys.stderr.write("\033[92m[MinimalServer]\033[0m %s - - [%s] %s\n" %
                             (self.address_string(),
                              self.log_date_time_string(),
                              format % message_args))

    def do_HEAD(self):
        """Handle HEAD requests (what Discord uses for verification)"""
        print(f"\n🔍 Received HEAD request for path: {self.path}")

        # Only respond to the Discord verification endpoint
        if self.path == '/api/interactions' or self.path == '/api/interactions/':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, HEAD')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Signature-Ed25519, X-Signature-Timestamp')
            self.end_headers()
            print("✅ Responded with 200 OK to HEAD request")
        else:
            self.send_response(404)
            self.end_headers()
            print(f"❌ Path not found: {self.path}")

    def do_GET(self):
        """Handle GET requests"""
        print(f"\n🔍 Received GET request for path: {self.path}")

        # Only respond to the Discord verification endpoint
        if self.path == '/api/interactions' or self.path == '/api/interactions/':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, HEAD')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Signature-Ed25519, X-Signature-Timestamp')
            self.end_headers()
            self.wfile.write(b'{"message": "This is a minimal Discord verification server"}')
            print("✅ Responded with 200 OK to GET request")
        else:
            self.send_response(404)
            self.end_headers()
            print(f"❌ Path not found: {self.path}")

    def do_OPTIONS(self):
        """Handle OPTIONS requests"""
        print(f"\n🔍 Received OPTIONS request for path: {self.path}")

        # Always respond with CORS headers for OPTIONS
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, HEAD')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Signature-Ed25519, X-Signature-Timestamp')
        self.end_headers()
        print("✅ Responded with 200 OK to OPTIONS request")

    def do_POST(self):
        """Handle POST requests (what Discord uses for interactions)"""
        print(f"\n🔍 Received POST request for path: {self.path}")

        # Only respond to the Discord verification endpoint
        if self.path == '/api/interactions' or self.path == '/api/interactions/':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"type": 1}')  # Type 1 is PONG response
            print("✅ Responded with 200 OK to POST request")
        else:
            self.send_response(404)
            self.end_headers()
            print(f"❌ Path not found: {self.path}")

def run_server():
    """Run the minimal verification server"""
    handler = MinimalVerificationHandler

    # Reuse address to avoid "Address already in use" errors
    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"🚀 Starting minimal verification server on port {PORT}")
        print(f"🐛 Debug mode: {'ON' if DEBUG else 'OFF'}")
        print("\nPress Ctrl+C to stop the server")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped by user")
        finally:
            httpd.server_close()
            print("✅ Server closed")

if __name__ == "__main__":
    run_server()
