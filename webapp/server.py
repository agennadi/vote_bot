#!/usr/bin/env python3
import http.server
import socketserver
import os
from pathlib import Path

PORT = 8000
DIR = Path(__file__).parent

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIR), **kwargs)
    
    def send_head(self):
        """Override to fix Content-Type."""
        path = self.translate_path(self.path)
        
        if os.path.isdir(path):
            parts = self.path.rstrip('/').split('/')
            if parts[-1] == '' or '.' not in parts[-1]:
                for index in "index.html", "index.htm":
                    index = os.path.join(path, index)
                    if os.path.exists(index):
                        path = index
                        break
        
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(404, "File not found")
            return None
        
        try:
            self.send_response(200)
            if path.endswith('.html'):
                self.send_header("Content-type", "text/html; charset=utf-8")
            elif path.endswith('.js'):
                self.send_header("Content-type", "application/javascript")
            elif path.endswith('.css'):
                self.send_header("Content-type", "text/css")
            else:
                self.send_header("Content-type", "application/octet-stream")
            
            fs = os.fstat(f.fileno())
            self.send_header("Content-Length", str(fs[6]))
            self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            return f
        except:
            f.close()
            raise

os.chdir(DIR)
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Server at http://localhost:{PORT}")
    httpd.serve_forever()
