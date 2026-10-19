"""Show all base models, replacing only the 1905 regenerated B pianos."""
import argparse
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote,urlsplit

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--replacement',type=Path,required=True);parser.add_argument('--base',type=Path,required=True);parser.add_argument('--port',type=int,default=8727);args=parser.parse_args()
    replacement=args.replacement.resolve();base=args.base.resolve()
    if not (replacement/'current_preview/index.html').is_file() or not (base/'assembly_index.jsonl').is_file():parser.error('Extract both deliveries before starting the combined preview')
    class Preview(SimpleHTTPRequestHandler):
        def translate_path(self,path):
            relative=unquote(urlsplit(path).path).lstrip('/') or 'index.html'
            root=replacement/'current_preview' if relative in ('index.html','preview_index.json','summary.json','results.csv') else replacement
            target=(root/relative).resolve()
            if not target.is_relative_to(root):return str(replacement/'__invalid_path__')
            if target.exists():return str(target)
            target=(base/relative).resolve()
            return str(target) if target.is_relative_to(base) else str(replacement/'__invalid_path__')
        def send_head(self):
            for name in ('If-Modified-Since','If-None-Match'):
                if name in self.headers:del self.headers[name]
            return super().send_head()
        def end_headers(self):self.send_header('Cache-Control','no-store, no-cache, must-revalidate, max-age=0');super().end_headers()
        def log_message(self,*args):pass
    print(f'Combined preview: http://127.0.0.1:{args.port}/index.html',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Preview).serve_forever()

if __name__=='__main__':main()
