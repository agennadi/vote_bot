#!/usr/bin/env python3
"""
Simple development server for the Web App.
For production, use a proper web server like nginx or deploy to Vercel/Netlify.
"""

import http.server
import socketserver
import os
from pathlib import Path

PORT = 8000
DIRECTORY = Path(__file__).parent


class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)
    
    def end_headers(self):
        # Add CORS headers for development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()


def run_server():
    os.chdir(DIRECTORY)
    
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"Web App server running at http://localhost:{PORT}")
        print(f"Serving files from: {DIRECTORY}")
        print("\n⚠️  For Telegram Web App, you need HTTPS!")
        print("Use ngrok or similar to create a tunnel:")
        print(f"  ngrok http {PORT}")
        print("\nThen set WEBAPP_URL in your .env file to the ngrok HTTPS URL")
        print("Press Ctrl+C to stop the server")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nServer stopped.")


if __name__ == "__main__":
    run_server()


