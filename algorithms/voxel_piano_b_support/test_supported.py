import json
from pathlib import Path
import tempfile
import unittest
import strict_core
import pipeline

class ExactAssemblyTests(unittest.TestCase):
    def test_unsupported_color_plane_stays_a_complete_failure(self):
        original={(0,0,0):0x111111,(0,0,1):0x111111,(1,0,1):0xffffff,(2,0,1):0xffffff}
        before=original.copy();result=strict_core.optimize(original,.15)
        self.assertFalse(strict_core.retile.base.audit(result['bricks'],result['targetCells'])['passed'])
        self.assertEqual(result['targetCells'],before);self.assertEqual(original,before)
        self.assertEqual(result['repairAudit']['addedVoxelCount'],0)
        self.assertEqual(result['repairAudit']['removedVoxelCount'],0)
        self.assertEqual({p:b['color'] for b in result['bricks'] for p in strict_core.retile.footprint(b)},before)

    def test_supported_actual_source_export_is_exact_and_detects_tampering(self):
        source=Path(__file__).resolve().parent/'fixtures/B_piano_m0039/model.json'
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'result';report=pipeline.run_one(source,out,8.,0.)
            self.assertTrue(report['geometryValidation']['passed'])
            self.assertEqual(report['repairAudit']['changeRatio'],0)
            self.assertTrue(pipeline.verify(out)['geometryValidation']['passed'])
            body=json.loads((out/'source.model.json').read_bytes());target=json.loads((out/'target.model.json').read_bytes())
            self.assertEqual({(v['x'],v['y'],v['z']):tuple(v['color']) for v in body['voxels']},{(v['x'],v['y'],v['z']):tuple(v['color']) for v in target['voxels']})
            ldr=out/'model.ldr';ldr.write_bytes(ldr.read_bytes()+b'0 changed\n')
            with self.assertRaises(ValueError):pipeline.verify(out)

if __name__=='__main__':unittest.main()
