import copy
import json
from pathlib import Path
import tempfile
import unittest

import retile_core as core
import retile_pipeline as pipeline
import relaxed_pipeline as independent

REPO=Path(__file__).resolve().parent.parent.parent


def interface_fixture():
    # A brown grounded cabinet and a black keyboard touch only at their sides.
    # One added brown stud at the layer below the keyboard admits a real 1xN
    # bridge that overlaps the existing cabinet; an append-only connector cannot.
    result={(x,y,z):0x8c562b for x in range(4) for y in range(4) for z in range(4)}
    result.update({(x,y,z):0 for x in range(4,6) for y in range(2) for z in range(3,5)})
    return result


def as_model(cells,identity='fixture'):
    return dict(modelId=identity,actualVoxelCount=len(cells),voxels=[dict(x=x,y=z,z=y,color=[c>>16&255,c>>8&255,c&255]) for (x,y,z),c in sorted(cells.items())])


class RetileTests(unittest.TestCase):
    def check(self,original,result):
        actual=core.base.audit(result['bricks'],result['targetCells'])
        other=independent.graph_readback(result['bricks'],result['targetCells'])
        self.assertTrue(actual['passed'])
        self.assertTrue(all(actual[k]==other[k] for k in other))
        self.assertTrue(core.base.strict.m.repair_audit(original,result['targetCells'],.02)['passed'])
        self.assertTrue(all(result['targetCells'][p]==c for p,c in original.items()))
        return actual

    def test_rebuild_existing_brick_and_local_added_cell(self):
        original=interface_fixture();saved=original.copy()
        result=core.optimize(original,seconds=2.)
        self.check(original,result)
        self.assertEqual(original,saved)
        self.assertEqual(result['repairAudit']['addedVoxelCount'],1)
        self.assertEqual(result['repairAudit']['removedVoxelCount'],0)
        self.assertGreater(sum(a.get('affectedBrickCount',0) for stage in result['searchAttempts'] for a in stage.get('actions',[])),0)

    def test_side_contact_is_not_a_stud_connection(self):
        original=interface_fixture()
        raw=core.ordered(core.connectors.cover(original))
        result=core.base.audit(raw,original)
        self.assertFalse(result['passed'])
        self.assertEqual(result['missingVoxelCount'],0)

    def test_additions_cannot_exceed_floor_budget(self):
        original={(0,0,z):0 for z in range(3)}
        original.update({(3,0,z):1 for z in (2,3)})
        result=core.optimize(original,seconds=.3)
        self.assertFalse(core.base.audit(result['bricks'],result['targetCells'])['passed'])
        self.assertEqual(result['targetCells'],original)
        self.assertEqual(result['repairAudit']['changedVoxelCount'],0)

    def test_failure_draft_still_covers_every_target_cell(self):
        original={(x,y,z):0 for x in range(3) for y in range(3) for z in range(4)}
        original[(20,20,20)]=0
        result=core.optimize(original,seconds=.1)
        actual=core.base.audit(result['bricks'],result['targetCells'])
        self.assertFalse(actual['passed'])
        self.assertTrue(actual['exactCoverage'])
        self.assertEqual(actual['missingVoxelCount'],0)

    def test_black_rgb_and_world_boundaries_are_preserved(self):
        original={(x+42,y+44,z):c for (x,y,z),c in interface_fixture().items()}
        result=core.optimize(original,seconds=2.)
        self.check(original,result)
        self.assertTrue(any(c==0 for c in result['targetCells'].values()))
        self.assertTrue(all(0<=v<48 for p in result['targetCells'] for v in p))

    def test_multiple_floor_modules_are_not_virtually_unioned(self):
        original={(x,0,z):0 for x in (0,4) for z in (0,1)}
        result=core.optimize(original,seconds=.2)
        actual=self.check(original,result)
        self.assertEqual(actual['studComponentCount'],2)
        self.assertEqual(actual['groundedComponentCount'],2)
        self.assertFalse(actual['fullPhysics'])
        self.assertIsNone(actual['staticVerified'])

    def test_independently_verified_success_is_retained(self):
        original={(x,0,z):0 for x in (0,4) for z in (0,1)}
        raw=core.ordered(core.connectors.cover(original))
        result=core.optimize(original,seconds=.1,baseline=dict(bricks=raw,targetCells=original.copy()))
        self.assertTrue(result['retainedBaseline'])
        self.assertEqual(result['bricks'],raw)
        self.assertEqual(result['targetCells'],original)

    def test_retained_deletion_requires_actual_failure_evidence(self):
        original={(x,y,z):0 for x in range(4) for y in range(4) for z in range(4)}
        original[(10,10,10)]=0
        target={p:c for p,c in original.items() if p!=(10,10,10)}
        raw=core.ordered(core.connectors.cover(target))
        with self.assertRaises(ValueError):
            core.optimize(original,seconds=.2,baseline=dict(bricks=raw,targetCells=target))

    def test_invalid_inputs_and_nonfinite_time_are_rejected(self):
        for bad in ({}, {(48,0,0):0},{(0,0,0):True},{(0,0,1):0}):
            with self.assertRaises(ValueError):core.optimize(bad)
        for seconds in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):core.optimize(interface_fixture(),seconds=seconds)

    def test_real_b_piano_color_interface_regression(self):
        path=REPO/'datasets/AI_B/samples/models/piano/vx80k5p_20261010_B_piano_m0001/model.json'
        source=json.loads(path.read_bytes());model,_=core.base.q.a.dataset_model(source)
        result=core.optimize(model.cells,seconds=3.)
        self.check(model.cells,result)
        self.assertLessEqual(result['repairAudit']['addedVoxelCount'],2)

    def test_real_a_table_can_retile_without_new_voxels(self):
        path=REPO/'samples/models/table/vx80k5p_20261010_A_table_m0001/model.json'
        source=json.loads(path.read_bytes());model,_=core.base.q.a.dataset_model(source)
        result=core.optimize(model.cells,seconds=3.)
        self.check(model.cells,result)
        self.assertEqual(result['repairAudit']['addedVoxelCount'],0)

    def test_export_readback_preserves_source_and_prompts(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'model.json';prompts=root/'prompts.json'
            source.write_text(json.dumps(as_model(interface_fixture())),encoding='utf-8')
            prompts.write_bytes(b'{"records":[{"caption":"original geometry"}]}\n')
            original_source=source.read_bytes();original_prompts=prompts.read_bytes()
            report=pipeline.run_one(source,root/'out',seconds=2.,physics_seconds=0)
            self.assertEqual(report['status'],'success')
            self.assertEqual(report['physics']['status'],'not_attempted_geometry_only')
            self.assertFalse(report['qualityScreenedSuccess'])
            self.assertEqual(source.read_bytes(),original_source)
            self.assertEqual(prompts.read_bytes(),original_prompts)
            self.assertEqual((root/'out/source.prompts.json').read_bytes(),original_prompts)
            self.assertEqual(pipeline.verify(root/'out',source),report)
            self.assertEqual(report['promptBindingStatus'],'original_only_not_revalidated')
            self.assertEqual(pipeline.run_one(source,root/'out',seconds=2.,physics_seconds=0),report)

    def test_actual_ldr_tampering_is_rejected_even_with_updated_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'model.json';out=root/'out'
            source.write_text(json.dumps(as_model(interface_fixture())),encoding='utf-8')
            pipeline.run_one(source,out,seconds=2.,physics_seconds=0)
            path=out/'model.ldr';path.write_text(path.read_text()+path.read_text(),encoding='utf-8')
            report=json.loads((out/'report.json').read_bytes());report['outputFileSha256']['model.ldr']=pipeline.digest(path)
            pipeline.dump(out/'report.json',report)
            with self.assertRaises(ValueError):pipeline.verify(out)

    def test_original_color_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'model.json';out=root/'out'
            source.write_text(json.dumps(as_model(interface_fixture())),encoding='utf-8')
            pipeline.run_one(source,out,seconds=2.,physics_seconds=0)
            target=json.loads((out/'target.model.json').read_bytes());target['voxels'][0]['color']=[1,2,3]
            pipeline.dump(out/'target.model.json',target)
            report=json.loads((out/'report.json').read_bytes());report['outputFileSha256']['target.model.json']=pipeline.digest(out/'target.model.json')
            pipeline.dump(out/'report.json',report)
            with self.assertRaises(ValueError):pipeline.verify(out)


if __name__=='__main__':unittest.main()
