# -*- coding: utf-8 -*-
"""人工判决工具(分包版)— 本地 HTTP 服务:静态页面 + GLB 模型 + 判决保存 API。
每次保存判决时自动更新包根目录的 best.md。
用法: python server.py [端口]  → 浏览器打开 http://127.0.0.1:8123/
"""
import json
import os
import sys
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent
PKG = ROOT.parent                     # 包根(data/、judge_tool/、best.md 所在)
ANN_FILE = ROOT / 'annotations.json'
BEST_FILE = PKG / 'best.md'
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8123
PKG_ID = PKG.name                     # 包名即标识,回传 best.md 时可追溯来源


def load_items():
    items = json.loads((ROOT / 'static' / 'items.json').read_text(encoding='utf-8'))
    meta = {}
    for cat in items:
        for lvl in items[cat]:
            for it in items[cat][lvl]:
                meta[it['id']] = it
    return items, meta


def build_best_md():
    """从 annotations.json 重建 best.md(判决表 + 统计)。"""
    _, meta = load_items()
    data = json.loads(ANN_FILE.read_text(encoding='utf-8')) if ANN_FILE.exists() else []
    items, _ = load_items()
    cats = list(items.keys())
    total = len(cats) * 5
    none_count = sum(1 for d in data if d['choice_id'] == 'NONE')
    lines = [
        f'# BrickMore-48 人工判决结果 · {PKG_ID}',
        '',
        f'- 包内类别({len(cats)}): {", ".join(cats)}',
        f'- 判决进度: {len(data)}/{total} 组 · 其中「全部不合格」{none_count} 组',
        f'- 最后更新: {datetime.now():%Y-%m-%d %H:%M:%S}',
        '',
        '> 本文件由判决工具自动更新,请勿手工编辑。判完(或放弃)所有组后,把本文件发回即可。',
        '',
        '| 类别 | 等级 | 最佳模型ID | 标签 | 提示词(原文) | 提示词(中文) | 备注 |',
        '|---|---|---|---|---|---|---|',
    ]
    for d in sorted(data, key=lambda d: (d['category'], d['level'])):
        if d['choice_id'] == 'NONE':
            lines.append(f"| {d['category']} | L{d['level']} | NONE | 全部不合格 | — | — | {d.get('note','') or ''} |")
        else:
            it = meta.get(d['choice_id'], {})
            prompt = (d.get('choice_prompt') or it.get('prompt') or '').replace('|', '\\|')
            zh = (it.get('zh') or '').replace('|', '\\|')
            note = (d.get('note') or '').replace('|', '\\|')
            lines.append(f"| {d['category']} | L{d['level']} | {d['choice_id']} | {d.get('choice_label','')} | {prompt} | {zh} | {note} |")
    BEST_FILE.write_text('\n'.join(lines) + '\n', encoding='utf-8')


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT / 'static'), **kw)

    def log_message(self, fmt, *args):
        sys.stdout.write(f'[{datetime.now():%H:%M:%S}] {fmt % args}\n')

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith('/obj/'):
            rel = unquote(self.path[5:])
            f = (PKG / rel).resolve()
            if not str(f).startswith(str(PKG.resolve())) or not f.is_file():
                return self._json(404, {'error': 'not found'})
            self.send_response(200)
            self.send_header('Content-Type', 'model/gltf-binary' if rel.endswith('.glb') else 'text/plain')
            self.send_header('Content-Length', str(f.stat().st_size))
            self.end_headers()
            self.wfile.write(f.read_bytes())
            return
        if self.path.startswith('/api/annotations'):
            data = json.loads(ANN_FILE.read_text(encoding='utf-8')) if ANN_FILE.exists() else []
            return self._json(200, data)
        return super().do_GET()

    def do_POST(self):
        if self.path == '/api/save':
            length = int(self.headers.get('Content-Length', 0))
            try:
                raw = self.rfile.read(length)
                try:
                    rec = json.loads(raw.decode('utf-8'))
                except UnicodeDecodeError:
                    rec = json.loads(raw.decode('gbk'))
                for k in ('category', 'level', 'choice_id', 'choice_label'):
                    if k not in rec:
                        return self._json(400, {'error': f'missing {k}'})
                rec['saved_at'] = datetime.now().isoformat(timespec='seconds')
                data = json.loads(ANN_FILE.read_text(encoding='utf-8')) if ANN_FILE.exists() else []
                data = [d for d in data
                        if not (d['category'] == rec['category'] and d['level'] == rec['level'])]
                data.append(rec)
                tmp = ANN_FILE.with_suffix('.tmp')
                tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
                tmp.replace(ANN_FILE)
                build_best_md()      # 每次保存同步刷新 best.md
                return self._json(200, {'ok': True, 'total': len(data)})
            except Exception as e:
                return self._json(400, {'error': str(e)})
        return self._json(404, {'error': 'unknown'})


def main():
    os.chdir(ROOT)
    if not ANN_FILE.exists():
        ANN_FILE.write_text('[]', encoding='utf-8')
    build_best_md()
    print(f'人工判决工具({PKG_ID}) → http://127.0.0.1:{PORT}/  (Ctrl+C 停止)')
    print(f'模型根: {PKG / "data"}')
    print(f'判决落盘: {ANN_FILE} + {BEST_FILE}')
    HTTPServer(('127.0.0.1', PORT), Handler).serve_forever()


if __name__ == '__main__':
    main()
