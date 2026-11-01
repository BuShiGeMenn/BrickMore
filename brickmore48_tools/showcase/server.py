# -*- coding: utf-8 -*-
"""BrickMore-48 模型展示站 — 每类一个人工精选模型。
用法: python server.py [端口]  → 浏览器打开 http://127.0.0.1:8126/
"""
import sys
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8126


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT / 'static'), **kw)

    def log_message(self, fmt, *args):
        sys.stdout.write(f'[{datetime.now():%H:%M:%S}] {fmt % args}\n')

    def do_GET(self):
        if self.path.startswith('/models/'):
            f = (ROOT / 'models' / unquote(self.path[len('/models/'):])).resolve()
            if not str(f).startswith(str(ROOT.resolve())) or not f.is_file():
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header('Content-Type', 'model/gltf-binary')
            self.send_header('Content-Length', str(f.stat().st_size))
            self.end_headers()
            self.wfile.write(f.read_bytes())
            return
        return super().do_GET()


if __name__ == '__main__':
    print(f'BrickMore-48 展示站 → http://127.0.0.1:{PORT}/  (Ctrl+C 停止)')
    HTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
