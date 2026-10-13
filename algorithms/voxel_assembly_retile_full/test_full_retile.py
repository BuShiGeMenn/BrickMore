import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import full_core
import full_pipeline as pipeline

DATA=Path(__file__).resolve().parents[2]/'preview/piano_table_retile/results/B/piano/vx80k5p_20261010_B_piano_m0001'

class FreshRunTests(unittest.TestCase):
    def setUp(self):
        self.source=DATA/'source.model.json'
        self.original=pipeline.base.q.a.dataset_model(json.loads(self.source.read_bytes()))[0].cells
        self.baseline=pipeline.read_baseline(DATA,self.source)

    def test_successful_baseline_does_not_skip_fresh_search(self):
        result=full_core.optimize(self.original,2,self.baseline)
        self.assertTrue(pipeline.base.audit(result['bricks'],result['targetCells'])['passed'])
        self.assertTrue(result['searchAttempts'][0]['freshSearchAttempted'])
        self.assertTrue(result['searchAttempts'][0]['freshGeometryPassed'])
        self.assertFalse(result['retainedBaseline'])

    def test_failed_fresh_layout_keeps_real_verified_success(self):
        raw=full_core.retile.connectors.cover(self.original,0)
        self.assertFalse(pipeline.base.audit(raw,self.original)['passed'])
        draft=full_core.retile.result(self.original,raw,self.original,[],0,retainedBaseline=False)
        with patch.object(full_core,'fresh_search',return_value=draft):result=full_core.optimize(self.original,2,self.baseline)
        self.assertTrue(result['retainedBaseline'])
        self.assertFalse(result['searchAttempts'][0]['freshGeometryPassed'])
        self.assertTrue(pipeline.base.audit(result['bricks'],result['targetCells'])['passed'])

    def test_actual_exports_verify_and_reject_tampered_layout(self):
        before=pipeline.digest(self.source)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'result';report=pipeline.run_one(self.source,out,2,0,DATA)
            self.assertEqual(report['algorithmVersion'],pipeline.VERSION)
            self.assertTrue(report['searchAttempts'][0]['freshSearchAttempted'])
            self.assertEqual(pipeline.verify(out)['sourceFileSha256'],before)
            self.assertEqual(pipeline.digest(self.source),before)
            ldr=out/'model.ldr';ldr.write_text(ldr.read_text().replace('0 STEP','0 TAMPER',1),encoding='utf-8')
            with self.assertRaises(ValueError):pipeline.verify(out)

if __name__=='__main__':unittest.main()
