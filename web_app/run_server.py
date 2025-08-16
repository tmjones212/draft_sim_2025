#!/usr/bin/env python3
"""
Simple HTTP server for the Mock Draft Simulator web app.
This avoids CORS issues when loading JSON files.
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

# Change to the web_app directory
web_dir = Path(__file__).parent
os.chdir(web_dir)

PORT = 8080
Handler = http.server.SimpleHTTPRequestHandler

# Try to find an available port if 8080 is busy
def find_available_port(start_port=8080, max_attempts=10):
    for port in range(start_port, start_port + max_attempts):
        try:
            with socketserver.TCPServer(("", port), Handler) as test_server:
                return port
        except OSError:
            continue
    return None

# Find available port
available_port = find_available_port(PORT)
if not available_port:
    print("ERROR: Could not find an available port.")
    print("Try closing other applications or run kill_server.bat")
    input("Press Enter to exit...")
    exit(1)

PORT = available_port

print(f"Starting Mock Draft Simulator web server...")
print(f"Server will run at: http://localhost:{PORT}")
print(f"Press Ctrl+C to stop the server")
print()

# Start the server with SO_REUSEADDR to avoid "Address already in use" errors
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.allow_reuse_address = True
    # Open browser automatically
    webbrowser.open(f'http://localhost:{PORT}')
    print(f"Server running at http://localhost:{PORT}")
    print("The browser should open automatically. If not, open the URL manually.")
    httpd.serve_forever()