import copy
import itertools
import json
from pathlib import Path
import tempfile
import unittest

import joint_cover as j
import gravity_audit as g
import experiment as e
q=j.q


def cells_of(bricks):
    return {p:b['color'] for b in bricks for p in q.a.Placement(**{k:b[k] for k in ('h','w','x','y','z')}).cells()}


def brick(h,w,x,y,z,color=0):return dict(h=h,w=w,x=x,y=y,z=z,color=color)


class JointTests(unittest.TestCase):
    def test_old_first_layer_trap_connectivity_cuts(self):
        cells={(x,y,0):0 for x in range(3) for y in range(3)}
        cells.update({(x,0,1):0xFF0000 for x in range(3)})
        raw,target,details=j.solve(cells,seconds=3)
        self.assertTrue(q.independent_audit(raw,target)['passed'])
        self.assertEqual(cells,target)
        self.assertGreater(details['connectivityCuts'],0)

    def test_joint_repair_limit_and_source_immutability(self):
        cells={(x,y,z):0 for x in range(2) for y in range(8) for z in range(6)}
        cells[(2,0,5)]=0xFF0000;original=cells.copy()
        raw,target,details=j.solve(cells,seconds=8)
        self.assertEqual(cells,original)
        self.assertTrue(q.independent_audit(raw,target)['passed'])
        check=q.repair_audit(cells,target)
        self.assertTrue(check['passed']);self.assertEqual(check['addedVoxelCount'],1)

    def test_small_budget_cannot_fake_optional_support(self):
        cells={(0,0,0):0,(1,0,0):1,(0,0,1):0}
        raw,target,details=j.solve(cells,seconds=2)
        self.assertFalse(q.independent_audit(raw,target)['passed'])
        self.assertTrue(q.repair_audit(cells,target)['passed'])
        self.assertEqual(target,cells)

    def test_candidate_truncation_never_implies_impossibility(self):
        cells={(x,y,z):0 for x in range(3) for y in range(3) for z in range(3)}
        raw,target,details=j.solve(cells,seconds=1,candidate_limit=1)
        self.assertTrue(details['candidateEnumerationTruncated'])
        self.assertFalse(details['completeSearch'])


class GravityTests(unittest.TestCase):
    def test_stable_tower_and_real_force_witness(self):
        raw=[brick(2,2,0,0,z) for z in range(6)];cells=cells_of(raw)
        result=g.audit(raw,cells)
        self.assertTrue(result['gravityEquilibriumPassed'])
        self.assertIsNone(result['staticVerified']);self.assertFalse(result['fullPhysics'])
        self.assertTrue(g.verify_witness(raw,cells,result))
        self.assertGreater(result['groundTippingMarginMeters'],0)

    def test_supported_bridge_transmits_load_to_both_legs(self):
        raw=[brick(1,1,0,0,0),brick(1,1,3,0,0),brick(4,1,0,0,1)]
        cells=cells_of(raw);result=g.audit(raw,cells)
        self.assertTrue(result['gravityEquilibriumPassed'])
        self.assertTrue(g.verify_witness(raw,cells,result))

    def test_global_tipping_not_saved_by_virtual_ground_anchor(self):
        raw=[brick(1,1,0,0,0),brick(3,1,0,0,1)]
        result=g.audit(raw,cells_of(raw))
        self.assertEqual(result['status'],'global_tipping_or_zero_margin')
        self.assertFalse(result['gravityEquilibriumPassed'])

    def test_stable_global_com_but_local_overhang_needs_clutch(self):
        # A heavy solid core keeps global COM inside the ground hull; the red
        # arm is supported at its end and cannot balance by compression alone.
        raw=[brick(2,4,0,0,z) for z in range(6)]+[brick(3,1,1,0,6,1)]
        cells=cells_of(raw);result=g.audit(raw,cells)
        self.assertEqual(result['status'],'requires_uncalibrated_clutch')
        self.assertFalse(result['gravityEquilibriumPassed'])
        self.assertGreater(result['minimumRequiredClutchNewtonsPerStud'],0)
        self.assertTrue(g.verify_witness(raw,cells,result))

    def test_loaded_support_not_just_own_brick_center(self):
        raw=[brick(1,1,0,0,0),brick(3,1,0,0,1),brick(1,1,2,0,2)]
        result=g.audit(raw,cells_of(raw))
        self.assertFalse(result['gravityEquilibriumPassed'])

    def test_tampered_force_contact_pass_flag_rejected(self):
        raw=[brick(2,2,0,0,z) for z in range(2)];cells=cells_of(raw);result=g.audit(raw,cells)
        for kind in ('force','contact','flag','fullPhysics','center','ground','margin'):
            changed=copy.deepcopy(result)
            if kind=='force':changed['equilibriumWitness']['signedForcesUnitWeights'][0]+=1
            elif kind=='contact':changed['equilibriumWitness']['contacts'][0][2]+=1
            elif kind=='flag':changed['gravityEquilibriumPassed']=False
            elif kind=='center':changed['centerOfMassInternalStudBrick'][0]+=1
            elif kind=='ground':changed['groundSupportPolygonStuds'][0][0]-=1
            elif kind=='margin':changed['groundTippingMarginMeters']+=1
            else:changed['fullPhysics']=True
            with self.assertRaises(ValueError):g.verify_witness(raw,cells,changed)

    def test_invalid_geometry_not_physically_certified(self):
        raw=[brick(1,1,0,0,0),brick(1,1,2,0,0)]
        result=g.audit(raw,cells_of(raw))
        self.assertEqual(result['status'],'not_evaluated_geometry_failed')

    def test_completed_layers_checked_and_missing_prefix_rejected(self):
        raw=[brick(2,2,0,0,z) for z in range(5)];cells=cells_of(raw)
        result=g.screen(raw,cells)
        self.assertTrue(result['layerPrefixGravityPassed'])
        self.assertEqual(len(result['layerPrefixReports']),4)
        self.assertTrue(g.verify_screen(raw,cells,result))
        changed=copy.deepcopy(result);changed['layerPrefixReports'].pop()
        with self.assertRaises(ValueError):g.verify_screen(raw,cells,changed)

    def test_bridge_prefix_separate_grounded_components_not_fake_connections(self):
        raw=[brick(1,1,0,0,0),brick(1,1,3,0,0),brick(4,1,0,0,1)]
        cells=cells_of(raw);result=g.screen(raw,cells)
        self.assertTrue(result['layerPrefixGravityPassed'])
        self.assertEqual(len(result['layerPrefixReports']),2)
        self.assertTrue(g.verify_screen(raw,cells,result))

    def test_complete_export_reread_and_forged_physics_rejected(self):
        raw=[brick(2,2,0,0,z) for z in range(2)];cells=cells_of(raw)
        value={'modelId':'q3_tower','actualVoxelCount':len(cells),
               'voxels':[dict(x=x,y=z,z=y,color=[0,0,0]) for x,y,z in sorted(cells)]}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'data'/'models'/'tower'/'q3_tower'/'model.json'
            source.parent.mkdir(parents=True);q.a.dump(source,value)
            job={'modelId':'q3_tower','modelPath':'models/tower/q3_tower','category':'tower',
                 'exactOccupancyHash':q.a.exact_hash({(x,z,y):c for (x,y,z),c in cells.items()})}
            options=dict(ratio=.02,seconds=2,physicsSeconds=2,candidateLimit=40000,cutRounds=8)
            report=e.worker((job,str(root/'data'),str(root/'out'),options))
            self.assertTrue(report['qualityScreenedSuccess'])
            folder=root/'out'/'models'/'tower'/'q3_tower'
            self.assertEqual(e.verify(folder,source),report)
            changed=json.loads((folder/'report.json').read_text());changed['fullPhysics']=True
            q.a.dump(folder/'report.json',changed)
            with self.assertRaises(ValueError):e.verify(folder,source)


if __name__=='__main__':unittest.main()
