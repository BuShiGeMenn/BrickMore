"""Numerical/protocol regression tests; optional backend tests run in the paper environment."""
import argparse
import importlib.util
import io
import json
import math
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from paper_common import Journal, fingerprint, normalize_ids, pooled, read_jsonl, write_jsonl
from evaluate_structure import aggregate
from evaluate_paper_images import build_question, single_yes_id, yes_probability
from evaluate_perplexity import sliding_nll
from generate_paper_samples import retry_sample
from prepare_paper_inputs import join_captions, pack, validated_views
from report_paper_eval import matched_pairs

HAS_TORCH = importlib.util.find_spec('torch') is not None
HAS_BRICKNET = importlib.util.find_spec('bricknet') is not None


class ProtocolTests(unittest.TestCase):
    def test_full_vocab_yes_probability(self):
        if not HAS_TORCH:
            self.skipTest('torch not installed in CPU-only collision environment')
        import torch
        logits = torch.tensor([[0.,0.,math.log(8)]],dtype=torch.float64)
        self.assertAlmostEqual(yes_probability(logits,0).item(),0.1,places=6)
        self.assertNotAlmostEqual(yes_probability(logits,0).item(),0.5)

    def test_question_and_single_yes_validation(self):
        self.assertEqual(build_question('  A  red chair...  '),'Is this LEGO set a red chair?')
        class Tokenizer:
            def encode(self,*args,**kwargs): return [1,2]
            def decode(self,*args): return 'Yes'
        with self.assertRaises(ValueError): single_yes_id(Tokenizer())

    def test_pooling_requires_complete_eight(self):
        self.assertEqual(pooled([0.,1.,2.,3.,4.,5.,6.,7.])['max_score'],7)
        self.assertEqual(pooled([0.,1.,2.,3.,4.,5.,6.,7.])['mean_score'],3.5)
        for values in [[1.]*7,[float('nan')]*8]:
            with self.assertRaises(ValueError): pooled(values)

    def test_pinv_macro_micro_and_censoring(self):
        def row(n,bad,ok=True):
            return {'parse_ok':ok,'parsed_parts':n,'attempted_actions':n,
                    'first_invalid':None if ok else n,'collisions':bad,'status':'ok'}
        rows = [row(2,[1]),row(8,[2]),row(3,None),row(1,[0],False)]
        stats = aggregate(rows)
        self.assertAlmostEqual(stats['pinv_macro'],0.3125)
        self.assertAlmostEqual(stats['pinv_micro'],0.2)
        self.assertEqual(stats['pinv_eligible_samples'],2)
        self.assertEqual(stats['pinv'],None)
        self.assertEqual(stats['collision_coverage'],0.75)
        self.assertEqual(stats['parseable_rate'],0.75)
        self.assertEqual(stats['mean_steps_before_collision_or_parse_failure_observed'],1.0)

    def test_journal_rejects_changed_config_inputs_and_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'scores.jsonl'
            journal = Journal(path,{'metric':'vqa'})
            journal.append({'sample_id':'a','value':1},'hash1')
            again = Journal(path,{'metric':'vqa'})
            self.assertEqual(again.cached('a','hash1')['value'],1)
            with self.assertRaises(ValueError): again.cached('a','hash2')
            with self.assertRaises(ValueError): Journal(path,{'metric':'pe'})
            with self.assertRaises(ValueError): again.append({'sample_id':'a'},'hash1')
        with self.assertRaises(ValueError): normalize_ids([{'id':1},{'id':1}])

    def test_retry_preserves_failed_attempts_and_resumes_without_generation(self):
        with tempfile.TemporaryDirectory() as folder:
            config = {'seed':1}
            attempts = Journal(Path(folder)/'attempts.jsonl',config)
            accepted = Journal(Path(folder)/'accepted.jsonl',config)
            calls = []
            def generate(row,attempt):
                calls.append(attempt); return 'bad' if attempt==0 else 'valid_but_colliding'
            def parse(text):
                return {'parse_ok':text!='bad','parts':2 if text!='bad' else 0,
                        'parse_error':'bad syntax' if text=='bad' else None}
            row = {'sample_id':'one','caption':'a chair'}
            result = retry_sample(row,generate,parse,attempts,accepted,config,3,True)
            self.assertEqual(result['attempts_used'],2)
            self.assertEqual(len(attempts.done),2)
            self.assertEqual(result['text'],'valid_but_colliding')
            retry_sample(row,generate,parse,attempts,accepted,config,3,True)
            self.assertEqual(calls,[0,1])

    def test_retry_exhaustion_is_not_counted_as_success(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg = {'seed':1}
            attempts = Journal(Path(folder)/'a.jsonl',cfg)
            accepted = Journal(Path(folder)/'s.jsonl',cfg)
            result = retry_sample({'sample_id':'x'},lambda *a:'bad',
                lambda text:{'parse_ok':False,'parts':0,'parse_error':'bad'},
                attempts,accepted,cfg,2,True)
            self.assertIsNone(result)
            self.assertEqual(len(accepted.done),0)
            self.assertEqual(len(attempts.done),2)

    def test_pack_indexes_match_caption_order_across_shards_and_detect_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            rows = []
            for sid in ['b','a']:
                paths = []
                for i in range(8):
                    path = base/f'{sid}_{i}.png'; path.write_bytes(bytes([i]))
                    paths.append(path.name)
                rows.append({'sample_id':sid,'caption':sid,'view_paths':paths})
            source = base/'renders.jsonl'; write_jsonl(source,rows)
            out = base/'tar'
            pack(argparse.Namespace(renders=source,out=out,shard_size=1))
            self.assertEqual([r['id'] for r in read_jsonl(out/'captions.jsonl')],['b','a'])
            for index,archive in enumerate(sorted(out.glob('*.tar'))):
                with tarfile.open(archive) as stream:
                    self.assertEqual(len(stream.getmembers()),8)
                    self.assertTrue(all(m.name.startswith(f'prompt_{index:04d}/') for m in stream))
            paths,hashes = validated_views(rows[0],base)
            rows[0]['view_sha256'] = hashes
            paths[0].write_bytes(b'changed')
            with self.assertRaises(ValueError): validated_views(rows[0],base)

    def test_pairs_exclude_missing_and_require_same_caption(self):
        rows = [{'candidate_id':'a','variant':'raw','caption':'same','vqa':0.2},
                {'candidate_id':'a','variant':'stitched','caption':'same','vqa':0.4},
                {'candidate_id':'b','variant':'raw','caption':'different','vqa':1}]
        pairs = matched_pairs(rows,['vqa'])
        self.assertEqual(len(pairs),1)
        self.assertAlmostEqual(pairs[0]['vqa'],0.2)
        rows[1]['caption'] = 'changed'
        with self.assertRaises(ValueError): matched_pairs(rows,['vqa'])

    def test_join_official_compressed_paths_keeps_all_records(self):
        import lzma
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            captions = base/'captions.jsonl'
            write_jsonl(captions,[{'id':'model_a','caption':'A chair.'}])
            paths = base/'paths.jsonl.xz'
            records = [{'source':'model_a.npz','round':1,'component_index':0,
                        'sample_index':i,'path':'a brick 2x4 | red\n'} for i in range(2)]
            with lzma.open(paths,'wt',encoding='utf-8') as stream:
                stream.write(''.join(json.dumps(r)+'\n' for r in records))
            out = base/'joined.jsonl'
            join_captions(argparse.Namespace(paths=paths,captions=captions,out=out))
            rows = read_jsonl(out)
            self.assertEqual(len(rows),2)
            self.assertNotEqual(rows[0]['sample_id'],rows[1]['sample_id'])
            self.assertTrue(all(r['caption']=='A chair.' for r in rows))

    @unittest.skipUnless(HAS_TORCH,'torch required')
    def test_sliding_ppl_counts_target_tokens_once_and_masks_caption(self):
        import torch
        class Output:
            pass
        class UniformModel:
            def __call__(self,input_ids,**kwargs):
                out = Output()
                out.logits = torch.zeros((*input_ids.shape,5))
                return out
        ids = [0,1,2,3,4]*5
        mask = [False]*7+[True]*18
        for window,stride in [(6,2),(8,7),(30,10)]:
            nll,count = sliding_nll(UniformModel(),ids,mask,window,stride,'cpu')
            self.assertEqual(count,18)
            self.assertAlmostEqual(nll/count,math.log(5),places=6)
        nll,count = sliding_nll(UniformModel(),ids,[True]*25,6,3,'cpu')
        self.assertEqual(count,24)  # token zero has no preceding context


@unittest.skipUnless(HAS_BRICKNET,'run with the separate CPU paper environment')
class LegacyBackendTests(unittest.TestCase):
    def test_real_legacy_collision_kernel_on_synthetic_cubes(self):
        import os
        import numpy as np
        import bricknet
        from bricknet.collision import _mesh, check_placements
        part = bricknet.parse_sample('a brick 2x4 | red\n').tree.parts[0].part_id
        stem = bricknet.load_catalog().id_to_stem[part]
        vertices = [(0,0,0),(10,0,0),(10,10,0),(0,10,0),
                    (0,0,10),(10,0,10),(10,10,10),(0,10,10)]
        faces = [(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),
                 (1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
        with tempfile.TemporaryDirectory() as folder:
            old = os.environ.get('BRICKNET_DATA')
            os.environ['BRICKNET_DATA'] = folder
            try:
                path = Path(folder)/'inset'/f'{stem}.ply'
                path.parent.mkdir()
                path.write_text('ply\nformat ascii 1.0\nelement vertex 8\nproperty float x\nproperty float y\nproperty float z\nelement face 12\nproperty list uchar int vertex_indices\nend_header\n'+
                    ''.join(f'{x} {y} {z}\n' for x,y,z in vertices)+
                    ''.join(f'3 {a} {b} {c}\n' for a,b,c in faces),encoding='ascii')
                _mesh.cache_clear()
                a = np.eye(4); b = np.eye(4); b[:3,3] = [5,1,1]
                self.assertEqual(check_placements([part,part],[a,b]),[1])
                b[:3,3] = [50,0,0]
                self.assertEqual(check_placements([part,part],[a,b]),[])
                self.assertEqual(check_placements([part,part],[a,a]),[1])
            finally:
                _mesh.cache_clear()
                if old is None: os.environ.pop('BRICKNET_DATA',None)
                else: os.environ['BRICKNET_DATA'] = old

    def test_legacy_real_parser_and_missing_mesh_are_not_success(self):
        import os
        import bricknet
        from evaluate_structure import score_one
        self.assertEqual(bricknet.__version__,'0.1.0')
        with tempfile.TemporaryDirectory() as folder:
            old = os.environ.get('BRICKNET_DATA')
            os.environ['BRICKNET_DATA'] = folder
            try:
                row = {'sample_id':'one','path':'a brick 2x4 | red\n'}
                parsed = score_one(row,bricknet,collision=False)
                self.assertTrue(parsed['parse_ok'],parsed['parse_error'])
                self.assertEqual(parsed['parsed_parts'],1)
                missing = score_one(row,bricknet,collision=True)
                self.assertEqual(missing['status'],'collision_unknown')
                self.assertIsNone(missing['pinv'])
                bad = score_one({'sample_id':'bad','text':'not valid syntax'},bricknet,False)
                self.assertFalse(bad['parse_ok'])
            finally:
                if old is None: os.environ.pop('BRICKNET_DATA',None)
                else: os.environ['BRICKNET_DATA'] = old


if __name__ == '__main__':
    unittest.main()
