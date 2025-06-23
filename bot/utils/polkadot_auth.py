from flask import Flask, jsonify, render_template_string, make_response, request, redirect
from flask_cors import CORS
import os
import json
import webbrowser
import threading
import time

class PolkadotAuth:
    def __init__(self, config, port=5000):
        self.app = Flask(__name__)
        CORS(self.app, resources={
            r"/*": {
                "origins": "*",
                "methods": ["GET", "POST", "OPTIONS"],
                "allow_headers": ["Content-Type"]
            }
        })
        self.config = config
        self.port = port
        self.connected_account = None
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/')
        def index():
            """Root route that redirects to the authentication page"""
            return redirect('/polkadot-connect')

        @self.app.route('/polkadot-connect')
        def polkadot_connect():
            """Main authentication page with Polkadot.js integration"""
            response = make_response(render_template_string('''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>OpenGov Bot - Polkadot.js Auth</title>
                    <script src="https://cdn.jsdelivr.net/npm/@polkadot/util@13.5.2/bundle-polkadot-util.js"></script>
                    <script src="https://cdn.jsdelivr.net/npm/@polkadot/util-crypto@13.5.2/bundle-polkadot-util-crypto.js"></script>
                    <script src="https://cdn.jsdelivr.net/npm/@polkadot/extension-dapp@0.60.1/bundle-polkadot-extension-dapp.js"></script>
                    <style>
                        body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
                        button { padding: 10px 15px; background: #E6007A; color: white; border: none; border-radius: 4px; cursor: pointer; }
                        #status { margin-top: 15px; }
                    </style>
                </head>
                <body>
                    <h2>Connect with Polkadot.js</h2>
                    <p>Please connect your wallet to sign transactions securely:</p>
                    <button id="connectButton">Connect Wallet</button>
                    <p id="status"></p>
                    <script>
                        document.addEventListener('DOMContentLoaded', () => {
                            const connectButton = document.getElementById('connectButton');
                            if (connectButton) {
                                connectButton.addEventListener('click', async () => {
                                    try {
                                        const { web3Enable, web3Accounts, web3FromAddress } = window.polkadotExtensionDapp;
                                        const extensions = await web3Enable('OpenGov Bot');
                                        
                                        if (extensions.length === 0) {
                                            throw new Error('No extension found. Please install the Polkadot.js extension.');
                                        }

                                        const allAccounts = await web3Accounts();
                                        if (allAccounts.length === 0) {
                                            throw new Error('No accounts found. Please create or import an account in the extension.');
                                        }

                                        const account = allAccounts[0];
                                        const injector = await web3FromAddress(account.address);
                                        
                                        const accountData = {
                                            address: account.address,
                                            publicKey: account.publicKey,
                                            name: account.meta.name
                                        };

                                        // Store in localStorage
                                        localStorage.setItem('polkadotAccount', JSON.stringify(accountData));

                                        // Send to server
                                        try {
                                            const response = await fetch('/set-account', {
                                                method: 'POST',
                                                headers: {
                                                    'Content-Type': 'application/json',
                                                },
                                                body: JSON.stringify(accountData)
                                            });
                                            
                                            if (!response.ok) {
                                                throw new Error('Failed to save account to server');
                                            }
                                        } catch (error) {
                                            console.error('Failed to save account to server:', error);
                                            throw error;
                                        }

                                        // Update UI
                                        const status = document.getElementById('status');
                                        status.textContent = 'Successfully connected! You can close this window.';
                                        status.style.color = 'green';

                                        // Notify parent window if this is a popup
                                        if (window.opener) {
                                            window.opener.postMessage({
                                                type: 'polkadot_connected',
                                                ...accountData
                                            }, '*');
                                            setTimeout(() => window.close(), 1000);
                                        }
                                    } catch (error) {
                                        console.error('Error:', error);
                                        const status = document.getElementById('status');
                                        status.textContent = `Error: ${error.message}`;
                                        status.style.color = 'red';
                                    }
                                });
                            }
                        });
                    </script>
                </body>
                </html>
            '''))
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            return response

        @self.app.route('/set-account', methods=['POST'])
        def set_account():
            """Handle saving the connected account to the server"""
            try:
                account_data = request.get_json()
                if account_data and 'address' in account_data:
                    self.connected_account = account_data
                    return jsonify({"status": "success"})
                return jsonify({"error": "Invalid account data"}), 400
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route('/health')
        def health_check():
            """Health check endpoint"""
            return jsonify({"status": "ok"})

        @self.app.route('/check-auth')
        def check_auth():
            """Check authentication status"""
            return jsonify({
                'is_authenticated': self.connected_account is not None,
                'account': self.connected_account
            })

        @self.app.after_request
        def after_request(response):
            """Add CORS headers to all responses"""
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
            return response

    def run(self):
        """Start the authentication server"""
        # Add auto-browser opening
        def open_browser():
            time.sleep(1)
            webbrowser.open_new(f'http://localhost:{self.port}')
        
        threading.Thread(target=open_browser).start()
        
        # Start the Flask server
        self.app.run(
            host='0.0.0.0',
            port=self.port,
            debug=True,
            use_reloader=False,
            threaded=True
        )

    def get_auth_url(self):
        """Get the URL for authentication"""
        return f"http://localhost:{self.port}"

if __name__ == '__main__':
    auth = PolkadotAuth({})
    auth.run()
