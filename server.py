"""Local-only dashboard. Run: python3 server.py; then open http://127.0.0.1:8765"""
import base64
import io
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse
from demo import run
from restoreproof import verify

class Handler(BaseHTTPRequestHandler):
    def send(self, status, data, mime='application/json'):
        data = data.encode() if isinstance(data,str) else data
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store')
        self.end_headers(); self.wfile.write(data)

    def do_GET(self):
        if self.path in ('/','/index.html'):
            self.send(200,Path(__file__).with_name('index.html').read_bytes(),'text/html; charset=utf-8')
        else:
            self.send(404,'{}')

    def do_POST(self):
        # Reject cross-origin browser requests and unexpected Host headers.
        if self.headers.get('Host') not in ('127.0.0.1:8765','localhost:8765') or self.headers.get('Origin') not in (None,'http://127.0.0.1:8765','http://localhost:8765'):
            self.send(403,'{"error":"Local origin required"}'); return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0 < size <= 24*1024*1024:
                raise ValueError('Request must be between 1 byte and 24 MiB')
            body=json.loads(self.rfile.read(size))
            if self.path == '/api/demo':
                r=run(body.get('scenario','healthy'))
            elif self.path == '/api/verify':
                raw=base64.b64decode(body['archive'],validate=True)
                r=verify(body['manifest'],io.BytesIO(raw))
            else:
                self.send(404,'{}'); return
            self.send(200,json.dumps(r))
        except Exception as e:
            self.send(400,json.dumps({'error':str(e)}))

if __name__ == '__main__':
    print('RestoreProof: http://127.0.0.1:8765 — Ctrl+C to stop',flush=True)
    HTTPServer(('127.0.0.1',8765),Handler).serve_forever()
