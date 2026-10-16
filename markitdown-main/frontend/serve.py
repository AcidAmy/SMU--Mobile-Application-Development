#!/usr/bin/env python3
"""
Lightweight Static HTTP Server for MarkItDown Frontend (Section 5.4).
Enables instant zero-dependency preview of Vue3 + Axios frontend without requiring Node.js.
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path

PORT = int(os.getenv("PORT", "5173"))
DIRECTORY = Path(__file__).resolve().parent

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def end_headers(self):
        # Enable CORS and caching headers for development
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
            print("\n" + "=" * 60)
            print("🚀 MarkItDown Vue3 + Axios Frontend Server is Running!")
            print(f"👉 Local Access:   http://localhost:{PORT}")
            print(f"👉 Local IP:       http://127.0.0.1:{PORT}")
            print("🔗 Target Backend: http://127.0.0.1:8000/api")
            print("=" * 60 + "\n")
            httpd.serve_forever()
    except OSError as e:
        if e.errno == 48: # Address already in use
            alt_port = PORT + 1
            print(f"⚠️ Port {PORT} is in use. Trying port {alt_port}...")
            with socketserver.TCPServer(("", alt_port), CustomHandler) as httpd:
                print(f"👉 Running on: http://localhost:{alt_port}")
                httpd.serve_forever()
        else:
            raise

if __name__ == "__main__":
    run_server()
