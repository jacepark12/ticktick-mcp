"""
TickTick OAuth authentication module.

This module handles the OAuth 2.0 flow for authenticating with TickTick,
allowing users to authorize the application and obtain access tokens
without manually copying and pasting tokens.
"""

import os
import webbrowser
import json
import time
import base64
import http.server
import socketserver
import urllib.parse
import requests
import threading
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
from dotenv import load_dotenv
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Default scopes for TickTick API
DEFAULT_SCOPES = ["tasks:read", "tasks:write"]

def is_running_in_docker():
    """Check if we're running inside a Docker container."""
    return os.path.exists('/.dockerenv')

class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """Handle OAuth callback requests."""
    
    # Class variable to store the authorization code
    auth_code = None
    
    def do_GET(self):
        """Handle GET requests to the callback URL."""
        # Parse query parameters
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        
        if 'code' in params:
            # Store the authorization code
            OAuthCallbackHandler.auth_code = params['code'][0]
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            # Return a nice HTML page
            response = """
            <html>
            <head>
                <title>TickTick MCP Server - Authentication Successful</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                        text-align: center;
                    }
                    h1 {
                        color: #4CAF50;
                    }
                    .box {
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        padding: 20px;
                        margin-top: 20px;
                        background-color: #f9f9f9;
                    }
                </style>
            </head>
            <body>
                <h1>Authentication Successful!</h1>
                <div class="box">
                    <p>You have successfully authenticated with TickTick.</p>
                    <p>You can now close this window and return to the terminal.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(response.encode())
        else:
            # Send error response
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            response = """
            <html>
            <head>
                <title>TickTick MCP Server - Authentication Failed</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                        text-align: center;
                    }
                    h1 {
                        color: #f44336;
                    }
                    .box {
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        padding: 20px;
                        margin-top: 20px;
                        background-color: #f9f9f9;
                    }
                </style>
            </head>
            <body>
                <h1>Authentication Failed</h1>
                <div class="box">
                    <p>Failed to receive authorization code from TickTick.</p>
                    <p>Please try again or check the error message in the terminal.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(response.encode())
    
    def log_message(self, format, *args):
        """Override to prevent noisy logging to stderr."""
        pass

class TickTickAuth:
    """TickTick OAuth authentication manager."""
    
    def __init__(self, client_id: str = None, client_secret: str = None, 
                 redirect_uri: str = "http://localhost:8000/callback",
                 port: int = 8000, env_file: str = None):
        """
        Initialize the TickTick authentication manager.
        
        Args:
            client_id: The TickTick client ID
            client_secret: The TickTick client secret
            redirect_uri: The redirect URI for OAuth callbacks
            port: The port to use for the callback server
            env_file: Path to .env file with credentials
        """
        # Try to load from environment variables or .env file
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        self.auth_url = os.getenv("TICKTICK_AUTH_URL") or "https://ticktick.com/oauth/authorize"
        self.token_url = os.getenv("TICKTICK_TOKEN_URL") or "https://ticktick.com/oauth/token"
        self.client_id = client_id or os.getenv("TICKTICK_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("TICKTICK_CLIENT_SECRET")
        self.redirect_uri = redirect_uri
        self.port = port
        self.auth_code = None
        self.tokens = None
        
        # Check if credentials are available
        if not self.client_id or not self.client_secret:
            logger.warning("TickTick client ID or client secret is missing. "
                          "Please set TICKTICK_CLIENT_ID and TICKTICK_CLIENT_SECRET "
                          "environment variables or provide them as parameters.")
    
    def get_authorization_url(self, scopes: list = None, state: str = None) -> str:
        """
        Generate the TickTick authorization URL.
        
        Args:
            scopes: List of OAuth scopes to request
            state: State parameter for CSRF protection
            
        Returns:
            The authorization URL
        """
        if not scopes:
            scopes = DEFAULT_SCOPES
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes)
        }
        
        if state:
            params["state"] = state
        
        # Build the URL with query parameters
        query_string = urllib.parse.urlencode(params)
        return f"{self.auth_url}?{query_string}"
    
    def start_auth_flow(self, scopes: list = None) -> str:
        """
        Start the OAuth flow by opening the browser and waiting for the callback.
        
        Args:
            scopes: List of OAuth scopes to request
            
        Returns:
            The obtained access token or an error message
        """
        if not self.client_id or not self.client_secret:
            return "TickTick client ID or client secret is missing. Please set up your credentials first."
        
        # Check if we're running in Docker
        if is_running_in_docker():
            return self._docker_auth_flow(scopes)
        else:
            return self._browser_auth_flow(scopes)
    
    def _browser_auth_flow(self, scopes: list = None) -> str:
        """Traditional OAuth flow with browser (for host environment)."""
        # Generate a random state parameter for CSRF protection
        state = base64.urlsafe_b64encode(os.urandom(30)).decode('utf-8')
        
        # Get the authorization URL
        auth_url = self.get_authorization_url(scopes, state)
        
        print(f"Opening browser for TickTick authorization...")
        print(f"If the browser doesn't open automatically, please visit this URL:")
        print(auth_url)
        
        # Open the browser for the user to authorize
        webbrowser.open(auth_url)
        
        # Start a local server to handle the OAuth callback
        httpd = None
        try:
            # Use a socket server to handle the callback
            OAuthCallbackHandler.auth_code = None
            httpd = socketserver.TCPServer(("", self.port), OAuthCallbackHandler)
            
            print(f"Waiting for authentication callback on port {self.port}...")
            
            # Run the server until we get the authorization code
            # Set a timeout for the server
            timeout = 300  # 5 minutes
            start_time = time.time()
            
            while not OAuthCallbackHandler.auth_code:
                # Handle one request with a short timeout
                httpd.timeout = 1.0
                httpd.handle_request()
                
                # Check if we've timed out
                if time.time() - start_time > timeout:
                    return "Authentication timed out. Please try again."
            
            # Store the auth code
            self.auth_code = OAuthCallbackHandler.auth_code
            
            # Exchange the code for tokens
            return self.exchange_code_for_token()
            
        except Exception as e:
            logger.error(f"Error during OAuth flow: {e}")
            return f"Error during OAuth flow: {str(e)}"
        finally:
            # Clean up the server
            if httpd:
                httpd.server_close()
    
    def _docker_auth_flow(self, scopes: list = None) -> str:
        """Container-friendly OAuth flow."""        
        try:
            # Use SO_REUSEADDR to allow port reuse
            class ReusableTCPServer(socketserver.TCPServer):
                allow_reuse_address = True
            
            with ReusableTCPServer(("", self.port), OAuthCallbackHandler) as httpd:
                OAuthCallbackHandler.auth_code = None
                
                server_thread = threading.Thread(target=httpd.serve_forever)
                server_thread.daemon = True
                server_thread.start()
                
                # Generate authorization URL with container callback
                auth_url = self.get_authorization_url(scopes)
                
                print("=" * 60)
                print("🐳 Docker container detected!")
                print(f"📱 Please open this URL in your browser:")
                print(f"   {auth_url}")
                print(f"🔗 Make sure port {self.port} is forwarded:")
                print(f"   docker run -p {self.port}:{self.port} your-image")
                print("=" * 60)
                
                # Wait for callback with timeout
                timeout = 300  # 5 minutes
                start_time = time.time()
                
                while OAuthCallbackHandler.auth_code is None:
                    if time.time() - start_time > timeout:
                        httpd.shutdown()
                        server_thread.join(timeout=2)
                        return "OAuth timeout - no response received after 5 minutes"
                    time.sleep(1)
                
                # Store the auth code
                self.auth_code = OAuthCallbackHandler.auth_code
                
                # Properly shutdown the server
                httpd.shutdown()
                server_thread.join(timeout=2)
                
                # Give the socket time to be released
                time.sleep(1)
                
                # Exchange the code for tokens
                return self.exchange_code_for_token()
                
        except Exception as e:
            logger.error(f"Error during Docker OAuth flow: {e}")
            return f"Error during Docker OAuth flow: {str(e)}"
    
    def exchange_code_for_token(self) -> str:
        """
        Exchange the authorization code for an access token.
        
        Returns:
            Success message or error message
        """
        if not self.auth_code:
            return "No authorization code available. Please start the authentication flow again."
        
        # Prepare the token request
        token_data = {
            "grant_type": "authorization_code",
            "code": self.auth_code,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(DEFAULT_SCOPES)
        }
        
        # Prepare Basic Auth credentials
        auth_str = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_str.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": None,
            "User-Agent": 'curl/8.7.1'
        }
        
        try:
            # Send the token request
            response = requests.post(self.token_url, data=token_data, headers=headers)
            response.raise_for_status()
            
            # Parse the response
            self.tokens = response.json()
            
            # Save the tokens to the .env file
            self._save_tokens_to_env()
            
            return "Authentication successful! Access token saved to .env file."
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error exchanging code for token: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    return f"Error exchanging code for token: {error_details}"
                except:
                    return f"Error exchanging code for token: {e.response.text}"
            return f"Error exchanging code for token: {str(e)}"
    
    def _save_tokens_to_env(self) -> None:
        """Save the tokens to the .env file."""
        if not self.tokens:
            return
        
        # Load existing .env file content
        env_path = Path('.env')
        env_content = {}
        
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_content[key] = value
        
        # Update with new tokens
        env_content["TICKTICK_ACCESS_TOKEN"] = self.tokens.get('access_token', '')
        if 'refresh_token' in self.tokens:
            env_content["TICKTICK_REFRESH_TOKEN"] = self.tokens.get('refresh_token', '')
        
        # Make sure client credentials are saved as well
        if self.client_id and "TICKTICK_CLIENT_ID" not in env_content:
            env_content["TICKTICK_CLIENT_ID"] = self.client_id
        if self.client_secret and "TICKTICK_CLIENT_SECRET" not in env_content:
            env_content["TICKTICK_CLIENT_SECRET"] = self.client_secret
        
        # Write back to .env file
        with open(env_path, 'w') as f:
            for key, value in env_content.items():
                f.write(f"{key}={value}\n")
        
        logger.info("Tokens saved to .env file")

def setup_auth_cli():
    """Run the authentication flow as a CLI utility."""
    import argparse
    
    parser = argparse.ArgumentParser(description='TickTick OAuth Authentication')
    parser.add_argument('--client-id', help='TickTick client ID')
    parser.add_argument('--client-secret', help='TickTick client secret')
    parser.add_argument('--redirect-uri', default='http://localhost:8000/callback',
                        help='OAuth redirect URI')
    parser.add_argument('--port', type=int, default=8000,
                        help='Port to use for OAuth callback server')
    parser.add_argument('--env-file', help='Path to .env file with credentials')
    
    args = parser.parse_args()
    
    auth = TickTickAuth(
        client_id=args.client_id,
        client_secret=args.client_secret,
        redirect_uri=args.redirect_uri,
        port=args.port,
        env_file=args.env_file
    )
    
    result = auth.start_auth_flow()
    print(result)

if __name__ == "__main__":
    setup_auth_cli()