import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import mixed_quality as m
import mixed_cover as j
import q4_experiment as e
q=m.q


def core(layers=6):return {(x,y,z):0 for x in range(2) for y in range(8) for z in range(layers)}
def failure():return {'geometryPassed':False,'kind':'test_additions_only_failure'}


class MixedAuditTests(unittest.TestCase):
    def test_total_budget_original_denominator_and_recorded_rgb(self):
        original=core();original[(7,7,7)]=0x123456
        target=original.copy();del target[(7,7,7)]
        check=m.repair_audit(original,target)
        self.assertTrue(check['passed']);self.assertEqual(check['changedVoxelCount'],1)
        self.assertEqual(check['changeRatio'],1/97)
        self.assertEqual(check['removedVoxelsInternalXYZRGB'][0]['rgb'],[18,52,86])
        target[(2,0,5)]=0
        self.assertFalse(m.repair_audit(original,target)['passed'])

    def test_ground_core_recolor_remote_and_unknown_palette_protected(self):
        original=core()
        for p in ((0,0,0),(0,0,4)):
            target=original.copy();del target[p]
            self.assertFalse(m.repair_audit(original,target)['passed'])
        for p,c in (((0,0,3),1),((7,7,7),0),((2,0,4),1)):
            target=original.copy();target[p]=c
            self.assertFalse(m.repair_audit(original,target)['passed'])

    def test_no_deletions_when_floor_budget_zero(self):
        original={(0,0,0):0,(5,5,5):0};target={(0,0,0):0}
        self.assertEqual(m.deletion_eligibility(original),{})
        self.assertFalse(m.repair_audit(original,target)['passed'])

    def test_small_floating_upper_component_but_not_large_component(self):
        original=core(7);original.update({(7,7,7):0,(7,7,8):0})
        eligible=m.deletion_eligibility(original)
        self.assertIn((7,7,8),eligible)
        original[(7,7,9)]=0
        self.assertNotIn((7,7,8),m.deletion_eligibility(original))

    def test_invalid_ratio_and_coordinate_fail_closed(self):
        with self.assertRaises(ValueError):m.repair_audit(core(),core(),.021)
        target=core();target[(48,0,0)]=0
        self.assertFalse(m.repair_audit(core(),target)['passed'])


class MixedSolverTests(unittest.TestCase):
    def test_gate_required_and_prior_success_disallows_fallback(self):
        for gate in (None,{'geometryPassed':True}):
            with self.assertRaises(ValueError):j.solve(core(),seconds=2,additions_only_failure=gate)

    def test_floating_detail_deletion_after_additions_failure(self):
        original=core();original[(7,7,7)]=0x123456;saved=original.copy()
        raw,target,stats=m.prior.solve(original,seconds=2)
        self.assertFalse(q.independent_audit(raw,target)['passed'])
        raw,target,stats=j.solve(original,seconds=5,additions_only_failure=failure())
        self.assertTrue(q.independent_audit(raw,target)['passed'])
        self.assertEqual(target,core());self.assertEqual(original,saved)
        self.assertEqual(m.repair_audit(original,target)['removedVoxelCount'],1)

    def test_combined_add_delete_budget(self):
        original=core(7);original[(7,7,7)]=0;original[(2,0,6)]=0xFF0000
        raw,target,stats=j.solve(original,seconds=8,additions_only_failure=failure())
        self.assertTrue(q.independent_audit(raw,target)['passed'])
        repair=m.repair_audit(original,target)
        self.assertTrue(repair['passed']);self.assertLessEqual(repair['changedVoxelCount'],2)
        self.assertEqual(repair['addedVoxelCount'],1);self.assertEqual(repair['removedVoxelCount'],1)

    def test_deleted_lower_voxel_is_not_fixed_phantom_support(self):
        original=core();original[(7,7,7)]=0;original[(7,7,8)]=0
        with patch.object(q,'allowed_additions',return_value=set()):
            raw,target,stats=j.solve(original,seconds=3,additions_only_failure=failure())
        self.assertFalse(q.independent_audit(raw,target)['passed'])
        self.assertTrue(m.repair_audit(original,target)['passed'])

    def test_truncation_not_impossibility(self):
        raw,target,stats=j.solve(core(),seconds=1,candidate_limit=1,additions_only_failure=failure())
        self.assertTrue(stats['candidateEnumerationTruncated']);self.assertFalse(stats['completeSearch'])


class MixedExportTests(unittest.TestCase):
    def run_fixture(self,root,floating):
        cells=core()
        if floating:cells[(7,7,7)]=0x123456
        value={'modelId':'q4_fixture','actualVoxelCount':len(cells),
               'voxels':[dict(x=x,y=z,z=y,color=[(c>>16)&255,(c>>8)&255,c&255]) for (x,y,z),c in sorted(cells.items())]}
        source=root/'data'/'models'/'fixture'/'q4_fixture'/'model.json';source.parent.mkdir(parents=True)
        q.a.dump(source,value)
        job={'modelId':'q4_fixture','modelPath':'models/fixture/q4_fixture','category':'fixture',
             'exactOccupancyHash':q.a.exact_hash({(x,z,y):c for (x,y,z),c in cells.items()})}
        options=dict(ratio=.02,seconds=5,additionsSeconds=2,physicsSeconds=3,candidateLimit=40000,cutRounds=8)
        row=e.worker((job,str(root/'data'),str(root/'out'),options))
        return source,root/'out'/'models'/'fixture'/'q4_fixture',row

    def test_actual_exports_source_and_deletion_evidence_reread(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,folder,row=self.run_fixture(Path(tmp),True)
            self.assertEqual(row['status'],'success');self.assertEqual(row['repairAudit']['removedVoxelCount'],1)
            self.assertTrue(row['qualityScreenedSuccess']);self.assertFalse(row['additionsOnlyGate']['geometryPassed'])
            self.assertEqual(e.verify(folder,source),row)
            saved=copy.deepcopy(row)
            for key,value in (('removedInternalXYZ',[]),('fullPhysics',True),('semanticVerified',True)):
                changed=copy.deepcopy(saved);changed[key]=value;q.a.dump(folder/'report.json',changed)
                with self.assertRaises(ValueError):e.verify(folder,source)

    def test_additions_success_is_never_deleted_or_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,folder,row=self.run_fixture(Path(tmp),False)
            self.assertEqual(row['status'],'success');self.assertEqual(row['repairAudit']['removedVoxelCount'],0)
            self.assertTrue(row['additionsOnlyGate']['geometryPassed'])
            self.assertEqual(row['outcome'],'geometry_additions_only')

    def test_previous_mixed_success_is_retained_with_original_failure_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,folder,row=self.run_fixture(root,True)
            cells=q.a.dataset_model(json.loads(source.read_text(encoding='utf8')))[0].cells
            job={'modelId':'q4_fixture','modelPath':'models/fixture/q4_fixture','category':'fixture',
                 'exactOccupancyHash':q.a.exact_hash({(x,z,y):c for (x,y,z),c in cells.items()}),
                 'priorQ4Path':str(folder),'priorQ4ReportSha256':q.a.file_sha(folder/'report.json'),'priorQ4Status':'success'}
            retained=e.worker((job,str(root/'data'),str(root/'retry'),row['options']))
            self.assertEqual(retained['outcome'],'geometry_retained_q4')
            self.assertEqual(retained['repairAudit'],row['repairAudit'])
            self.assertEqual(retained['additionsOnlyGate'],row['additionsOnlyGate'])


if __name__=='__main__':unittest.main()
