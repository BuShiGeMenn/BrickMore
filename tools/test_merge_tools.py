import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import download_dataset as d
from github_release import matches
from merge_shards import combined_index, safe_relative, verify_prompt_stream


class MergeToolTests(unittest.TestCase):
    def test_joined_manifest_prefixes_npz_and_preview_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'dataset_catalog.json').write_text(json.dumps({'modelCount':2}),encoding='utf8')
            shards={'A':{'promptRecordCount':5,'models':[{'modelId':'A',
                'modelJsonPath':'models/a/model.json','modelNpzPath':'models/a/model.npz',
                'previewPath':'models/a/preview.png'}]},
                'B':{'promptRecordCount':5,'models':[{'modelId':'B','modelPath':'models/b'}]}}
            with patch.object(d,'ROOT',root):
                d.join_extracted(root,shards)
                d.join_extracted(root,shards)
            result=json.loads((root/'manifest.json').read_text())
            self.assertEqual(result['modelCount'],2)
            self.assertEqual(result['promptRecordCount'],10)
            self.assertEqual(result['models'][0]['modelNpzPath'],'AI_A/models/a/model.npz')
            self.assertEqual(result['models'][0]['previewPath'],'AI_A/models/a/preview.png')
            self.assertEqual(result['models'][1]['modelPath'],'AI_B/models/b')

    def prompt_fixture(self):
        model = {'modelId': 'model_A', 'modelSeed': 7, 'exactOccupancyHash': 'a',
                 'canonicalGeometryHash': 'b', 'modelJsonPath': 'models/test/model.json'}
        records = [{'modelId': 'model_A', 'recordId': 'model_A_l'+str(level),
                    'shardId': 'A', 'modelSeed': 7, 'promptLevel': level,
                    'targetOccupancyHash': 'a', 'targetCanonicalGeometryHash': 'b',
                    'modelJsonPath': 'models/test/model.json', 'sharesGeometryAcrossLevels': True,
                    'expectedIndependentGeometryAcrossLevels': False,
                    'captionZh': '模型', 'captionEn': 'model'} for level in range(1,6)]
        return model, records

    def record_stream(self, records):
        return io.BytesIO((''.join(json.dumps(r)+'\n' for r in records)).encode())

    def test_complete_five_level_prompt_group(self):
        model, records = self.prompt_fixture()
        seen = set()
        result = verify_prompt_stream(self.record_stream(records), 'A', [model], seen)
        self.assertEqual(result['recordCount'], 5)
        self.assertEqual(len(seen), 5)
        self.assertTrue(result['allSourceGeometryAssociationsPassed'])

    def test_prompt_wrong_target_geometry_rejected(self):
        model, records = self.prompt_fixture()
        records[2]['targetOccupancyHash'] = 'wrong'
        with self.assertRaises(ValueError):
            verify_prompt_stream(self.record_stream(records), 'A', [model], set())

    def test_prompt_missing_level_rejected(self):
        model, records = self.prompt_fixture()
        with self.assertRaises(ValueError):
            verify_prompt_stream(self.record_stream(records[:-1]), 'A', [model], set())

    def test_prompt_record_id_collision_across_shards_rejected(self):
        model, records = self.prompt_fixture()
        with self.assertRaises(ValueError):
            verify_prompt_stream(self.record_stream(records), 'A', [model], {'model_A_l1'})

    def make_zip(self, path, files):
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, value in files.items():
                archive.writestr(name, value)

    def test_b_indexes_are_namespaced_and_metadata_remains_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root/'B_models_00001_01000.zip'
            self.make_zip(archive, {'manifest.json': '{"modelCount":1000}',
                'all_prompts.jsonl': 'package records', 'models/basket/B/model.json': '{}'})
            output = root/'dataset'
            output.mkdir()
            (output/'manifest.json').write_text('{"modelCount":40000}', encoding='utf8')
            d.extract(archive, output, 'model_package', 'B')
            self.assertEqual(json.loads((output/'manifest.json').read_text())['modelCount'], 40000)
            self.assertTrue((output/'package_indexes'/archive.stem/'manifest.json').is_file())
            self.assertTrue((output/'models/basket/B/model.json').is_file())

    def test_archive_traversal_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root/'bad.zip'
            self.make_zip(archive, {'good.json': '{}', '../escape.json': '{}'})
            with self.assertRaises(ValueError):
                d.extract(archive, root/'output')
            self.assertFalse((root/'output/good.json').exists())
            self.assertFalse((root/'escape.json').exists())

    def test_windows_absolute_path_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root/'bad.zip'
            self.make_zip(archive, {'C:/escape.json': '{}'})
            with self.assertRaises(ValueError):
                d.extract(archive, root/'output')

    def test_archive_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root/'bad.zip'
            info = zipfile.ZipInfo('link')
            info.external_attr = 0o120777 << 16
            with zipfile.ZipFile(archive, 'w') as output:
                output.writestr(info, 'elsewhere')
            with self.assertRaises(ValueError):
                d.extract(archive, root/'output')

    def test_existing_file_conflict_never_overwrites(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root/'test.zip'
            self.make_zip(archive, {'first.json': '{}', 'model.json': 'original'})
            output = root/'output'
            output.mkdir()
            (output/'model.json').write_text('modified', encoding='utf8')
            with self.assertRaises(ValueError):
                d.extract(archive, output)
            self.assertEqual((output/'model.json').read_text(), 'modified')
            self.assertFalse((output/'first.json').exists())

    def test_repeated_extraction_is_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root/'test.zip'
            self.make_zip(archive, {'model.json': '{}'})
            d.extract(archive, root/'output')
            d.extract(archive, root/'output')
            self.assertEqual((root/'output/model.json').read_text(), '{}')

    def test_combined_index_uses_separate_shard_roots(self):
        a = {'modelId': 'vx80k5p_20261010_A_basket_m0001', 'category': 'basket',
             'globalOrdinal': 1, 'modelSeed': 800000001, 'actualVoxelCount': 800,
             'exactOccupancyHash': 'a', 'canonicalGeometryHash': 'b',
             'modelJsonPath': 'models/basket/A/model.json'}
        b = {**a, 'modelId': 'vx80k5p_20261010_B_basket_m0001', 'modelJsonPath': None,
             'modelPath': 'models/basket/B', 'globalOrdinal': 40001}
        rows = combined_index([a], [b])
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[0]['modelJsonPath'].startswith('AI_A/'))
        self.assertTrue(rows[1]['pairedPromptsPath'].startswith('AI_B/'))
        self.assertEqual(rows[1]['promptRecordCount'], 5)

    def test_invalid_index_path_rejected(self):
        for path in ('../models/A', 'C:/models/A', '/models/A'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                safe_relative(path)

    def test_remote_asset_needs_uploaded_state_size_and_sha(self):
        asset = {'bytes': 12, 'sha256': 'abc'}
        row = {'state': 'uploaded', 'size': 12, 'digest': 'sha256:abc'}
        self.assertTrue(matches(row, asset))
        self.assertFalse(matches({**row, 'digest': 'sha256:wrong'}, asset))
        self.assertFalse(matches({**row, 'state': 'starter'}, asset))

    def test_b_modelpath_inventory_is_supported(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            model = root/'models/basket/B'
            model.mkdir(parents=True)
            for name in ('model.json','model.npz','model.obj','model.mtl','model.vox','preview.png','validation.json','prompts.json'):
                (model/name).write_bytes(b'')
            data = {'modelCount': 1, 'promptRecordCount': 5,
                    'models': [{'modelId': 'B', 'modelPath': 'models/basket/B'}]}
            (root/'manifest.json').write_text(json.dumps(data), encoding='utf8')
            self.assertEqual(d.verify_extracted(root, data)['modelCount'], 1)


if __name__ == '__main__':
    unittest.main()
