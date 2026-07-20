#!/usr/bin/env python3
import http.server
import socketserver
import os
import webbrowser
from datetime import datetime

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def log_message(self, format, *args):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f'[{timestamp}] {format % args}')

if __name__ == "__main__":
    handler = MyHTTPRequestHandler

    with socketserver.TCPServer(("", PORT), handler) as httpd:
        url = f"http://localhost:{PORT}"
        print(f"\n{'='*60}")
        print(f"Servidor iniciado: {url}")
        print(f"{'='*60}")
        print(f"Presiona Ctrl+C para detener el servidor\n")

        try:
            # Abrir navegador automáticamente
            webbrowser.open(url)
        except:
            pass

        httpd.serve_forever()
