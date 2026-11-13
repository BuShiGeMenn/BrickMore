"""Offline functional checks, including a real interrupted HTTP Range transfer."""
import hashlib,json,tempfile,threading,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from common import ROOT,Journal,rows
from download import fetch

class Checks(unittest.TestCase):
    def test_shell_scripts_posix_newlines_and_integrity(self):
        entries=dict((name,checksum) for checksum,name in (line.split('  ',1) for line in (ROOT/'CHECKSUMS.sha256').read_text(encoding='utf-8').splitlines()))
        for name in ['setup.sh','run.sh','Scripts/environment.sh']:
            payload=(ROOT/name).read_bytes()
            self.assertNotIn(b'\r',payload,name)
            self.assertTrue(payload.endswith(b'\n'),name)
            self.assertEqual(hashlib.sha256(payload).hexdigest(),entries[name],name)

    def test_matched_cohort(self):
        primary=rows(ROOT/'Data/primary_manifest.jsonl');self.assertEqual(len(primary),342)
        ids={r['prompt_id'] for r in primary};self.assertEqual(len(ids),114)
        for pid in ids:
            rs=[r for r in primary if r['prompt_id']==pid]
            self.assertEqual({r['system'] for r in rs},{'BrickMore','BrickGPT','BrickNet'})
            self.assertEqual(len({r['caption'] for r in rs}),1)

    def test_collision_kernel_and_mating(self):
        import os,numpy as np
        os.environ['BRICKNET_DATA']=str(ROOT/'Assets')
        import bricknet
        from bricknet.data import load_catalog
        from bricknet.collision import check_placements
        self.assertEqual(bricknet.__version__,'0.1.0');pid=load_catalog().stem_to_id['3001'];a=np.eye(4);b=np.eye(4)
        self.assertEqual(check_placements([pid,pid],[a,b]),[1])
        b[0,3]=160;self.assertEqual(check_placements([pid,pid],[a,b]),[])
        b=np.eye(4);b[1,3]=-24;self.assertEqual(check_placements([pid,pid],[a,b]),[])

    def test_journal_resume_and_changed_input(self):
        from paper_common import Journal as ImageJournal
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'run.jsonl';j=Journal(p,{'input':'same'});j.add({'sample_id':'a','value':.2},'hash')
            self.assertEqual(Journal(p,{'input':'same'}).cached('a','hash')['value'],.2)
            with self.assertRaises(ValueError):Journal(p,{'input':'different'})
            with p.open('a',encoding='utf-8') as f:f.write('{"sample_id":')
            self.assertEqual(len(rows(p)),1);self.assertTrue(list(Path(td).glob('*.interrupted-*')))
            q=Path(td)/'image_scores.jsonl';gpu=ImageJournal(q,{'model':'fixed'})
            gpu.append({'sample_id':'a','max_score':.3},'image-hash')
            with q.open('a',encoding='utf-8') as f:f.write('{"sample_id":')
            restored=ImageJournal(q,{'model':'fixed'})
            self.assertEqual(restored.cached('a','image-hash')['max_score'],.3)
            with self.assertRaises(ValueError):ImageJournal(q,{'model':'changed'})
            self.assertTrue(list(Path(td).glob('image_scores.jsonl.interrupted-*')))

    def test_download_resume_reconnect_and_checksum(self):
        data=bytes(range(256))*4096;seen=[];calls=[0]
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                offset=int(self.headers.get('Range','bytes=0-').split('=')[1].split('-')[0]);seen.append(offset);calls[0]+=1
                end=len(data)-1;self.send_response(206);self.send_header('Content-Range',f'bytes {offset}-{end}/{len(data)}');self.send_header('Content-Length',str(len(data)-offset));self.end_headers()
                payload=data[offset:]
                if calls[0]==1:payload=payload[:65536]
                self.wfile.write(payload);self.wfile.flush();self.close_connection=True
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as td:
                target=Path(td)/'asset.bin';target.with_name(target.name+'.part').write_bytes(data[:32768])
                fetch(f'http://127.0.0.1:{server.server_port}/asset',target,size=len(data),sha256=hashlib.sha256(data).hexdigest(),retries=4,timeout=2)
                self.assertEqual(target.read_bytes(),data);self.assertEqual(seen[0],32768);self.assertGreater(seen[1],seen[0])
                calls_before=calls[0];fetch(f'http://127.0.0.1:{server.server_port}/asset',target,size=len(data),sha256=hashlib.sha256(data).hexdigest());self.assertEqual(calls[0],calls_before)
        finally:server.shutdown();server.server_close()

if __name__=='__main__':unittest.main(verbosity=2)
