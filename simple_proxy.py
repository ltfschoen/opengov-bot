#!/usr/bin/env python
"""
Simple HTTP proxy server that forwards requests to the verification server.
This acts as an intermediary between Cloudflare and your verification server.
"""

import http.server
import socketserver
import requests
import json
import sys
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description='Simple proxy server for Discord verification')
parser.add_argument('--port', type=int, default=8002, help='Port to run the proxy server on')
parser.add_argument('--target', type=str, default='http://localhost:8001', help='Target server to proxy to')
parser.add_argument('--debug', action='store_true', help='Enable debug mode')
args = parser.parse_args()

PROXY_PORT = args.port
TARGET_SERVER = args.target
DEBUG = args.debug

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self):
        """Handle HEAD requests by forwarding them to the target server"""
        print(f"\n🔍 Received HEAD request for path: {self.path}")

        try:
            # Forward the request to the verification server
            target_url = f"{TARGET_SERVER}{self.path}"
            print(f"⏩ Forwarding to: {target_url}")

            # Copy headers from the original request
            headers = {}
            for header in self.headers:
                headers[header] = self.headers[header]
                if DEBUG:
                    print(f"📝 Header: {header}: {self.headers[header]}")

            # Make the request to the target server
            response = requests.head(target_url, headers=headers, timeout=10)

            # Send the response status code
            self.send_response(response.status_code)

            # Copy all headers from the target response
            for header, value in response.headers.items():
                self.send_header(header, value)
                if DEBUG:
                    print(f"📤 Response header: {header}: {value}")

            self.end_headers()
            print(f"✅ Successfully proxied HEAD request, status: {response.status_code}")

        except Exception as e:
            print(f"❌ Error proxying HEAD request: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

    def do_GET(self):
        """Handle GET requests by forwarding them to the target server"""
        print(f"\n🔍 Received GET request for path: {self.path}")

        try:
            # Forward the request to the verification server
            target_url = f"{TARGET_SERVER}{self.path}"
            print(f"⏩ Forwarding to: {target_url}")

            # Copy headers from the original request
            headers = {}
            for header in self.headers:
                headers[header] = self.headers[header]

            # Make the request to the target server
            response = requests.get(target_url, headers=headers, timeout=10)

            # Send the response status code
            self.send_response(response.status_code)

            # Copy all headers from the target response
            for header, value in response.headers.items():
                self.send_header(header, value)

            self.end_headers()

            # Send the response content
            self.wfile.write(response.content)
            print(f"✅ Successfully proxied GET request, status: {response.status_code}")

        except Exception as e:
            print(f"❌ Error proxying GET request: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = json.dumps({"error": str(e)}).encode('utf-8')
            self.wfile.write(error_response)

    def do_POST(self):
        """Handle POST requests by forwarding them to the target server"""
        print(f"\n🔍 Received POST request for path: {self.path}")

        try:
            # Get the content length
            content_length = int(self.headers.get('Content-Length', 0))

            # Read the request body
            body = self.rfile.read(content_length) if content_length > 0 else b''

            # Forward the request to the verification server
            target_url = f"{TARGET_SERVER}{self.path}"
            print(f"⏩ Forwarding to: {target_url}")

            # Copy headers from the original request
            headers = {}
            for header in self.headers:
                headers[header] = self.headers[header]

            # Make the request to the target server
            response = requests.post(target_url, headers=headers, data=body, timeout=10)

            # Send the response status code
            self.send_response(response.status_code)

            # Copy all headers from the target response
            for header, value in response.headers.items():
                self.send_header(header, value)

            self.end_headers()

            # Send the response content
            self.wfile.write(response.content)
            print(f"✅ Successfully proxied POST request, status: {response.status_code}")

        except Exception as e:
            print(f"❌ Error proxying POST request: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = json.dumps({"error": str(e)}).encode('utf-8')
            self.wfile.write(error_response)

    def do_OPTIONS(self):
        """Handle OPTIONS requests by forwarding them to the target server"""
        print(f"\n🔍 Received OPTIONS request for path: {self.path}")

        try:
            # Forward the request to the verification server
            target_url = f"{TARGET_SERVER}{self.path}"
            print(f"⏩ Forwarding to: {target_url}")

            # Copy headers from the original request
            headers = {}
            for header in self.headers:
                headers[header] = self.headers[header]

            # Make the request to the target server
            response = requests.options(target_url, headers=headers, timeout=10)

            # Send the response status code
            self.send_response(response.status_code)

            # Copy all headers from the target response
            for header, value in response.headers.items():
                self.send_header(header, value)

            # Add CORS headers if they're missing
            if 'Access-Control-Allow-Origin' not in response.headers:
                self.send_header('Access-Control-Allow-Origin', '*')

            if 'Access-Control-Allow-Methods' not in response.headers:
                self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, HEAD')

            if 'Access-Control-Allow-Headers' not in response.headers:
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Signature-Ed25519, X-Signature-Timestamp')

            self.end_headers()
            print(f"✅ Successfully proxied OPTIONS request, status: {response.status_code}")

        except Exception as e:
            print(f"❌ Error proxying OPTIONS request: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

def run_server():
    """Run the proxy server"""
    handler = ProxyHandler

    # Reuse address to avoid "Address already in use" errors
    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer(("", PROXY_PORT), handler) as httpd:
        print(f"🚀 Starting proxy server on port {PROXY_PORT}")
        print(f"⏩ Forwarding requests to {TARGET_SERVER}")
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
