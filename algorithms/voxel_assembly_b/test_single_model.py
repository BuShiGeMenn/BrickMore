import json
from pathlib import Path
import tempfile
import unittest
from assemble_one import run_model


class SingleModelTests(unittest.TestCase):
    def test_demo_exports_and_readback(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'result'
            result=run_model(Path(__file__).parent/'examples'/'bridge_y_up.json',out)
            self.assertEqual(result['status'],'success')
            self.assertTrue(result['validation']['ldrReadbackMatches'])
            self.assertEqual(result['validation']['studComponentCount'],1)
            self.assertEqual(result['validation']['inputVoxelCount'],6)
            self.assertIsNone(result['staticVerified'])

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                run_model(Path(__file__).parent/'examples'/'bridge_y_up.json',Path(folder))

    def test_unconnected_colors_stay_failed(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'input.json'
            source.write_text(json.dumps({'voxels':[dict(x=0,y=0,z=0,color=[0,0,0]),
                 dict(x=1,y=0,z=0,color=[255,0,0])]}),encoding='utf8')
            out=Path(folder)/'result'
            result=run_model(source,out)
            self.assertEqual(result['status'],'draft')
            self.assertFalse(result['validation']['passed'])
            self.assertTrue((out/'model.draft.ldr').exists())
            self.assertFalse((out/'model.ldr').exists())


if __name__=='__main__':
    unittest.main()
