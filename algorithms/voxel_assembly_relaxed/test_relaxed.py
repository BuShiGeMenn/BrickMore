import unittest
import grounded_flow as flow
import relaxed_core as r


def brick(x,y,z,h=1,w=1,color=0):return dict(x=x,y=y,z=z,h=h,w=w,color=color)
def cells_for(raw):return {p:b['color'] for b in raw for p in r.q.a.Placement(**{k:b[k] for k in ('h','w','x','y','z')}).cells()}


class RelaxedTests(unittest.TestCase):
    def test_multiple_grounded_modules_not_virtual_union(self):
        raw=[brick(0,0,0),brick(4,0,0),brick(0,0,1),brick(4,0,1)]
        result=r.audit(raw,cells_for(raw))
        self.assertTrue(result['passed']);self.assertEqual(result['studComponentCount'],2)
        self.assertEqual(result['groundedComponentCount'],2)
        self.assertFalse(r.q.independent_audit(raw,cells_for(raw))['passed'])
    def test_upper_stud_path_is_real_not_physical_certification(self):
        raw=[brick(0,0,0),brick(0,0,1),brick(0,0,2),brick(1,0,2),brick(0,0,3,h=2)]
        result=r.audit(raw,cells_for(raw));self.assertTrue(result['passed'])
        self.assertEqual(result['upperAttachedBrickCount'],1)
        self.assertFalse(result['fullPhysics']);self.assertIsNone(result['staticVerified'])
        self.assertFalse(result['installationSequenceVerified'])
    def test_actual_isolated_floating_component_rejected(self):
        raw=[brick(0,0,0),brick(0,0,1),brick(4,0,4)]
        result=r.audit(raw,cells_for(raw));self.assertFalse(result['passed'])
        self.assertFalse(result['allComponentsGrounded'])
    def test_collision_missing_recolor_bounds_and_wrong_catalog_rejected(self):
        raw=[brick(0,0,0),brick(0,0,1)];target=cells_for(raw)
        for bad in (raw+[raw[0]],raw[:1],[brick(0,0,0,color=1),raw[1]],[brick(48,0,0),raw[1]],
                    [brick(0,0,0,h=3,w=3),raw[1]]):self.assertFalse(r.audit(bad,target)['passed'])
    def test_ground_flow_exact_real_cover_and_separate_floor_roots(self):
        target={(0,0,0):0,(0,0,1):1,(4,0,0):0,(4,0,1):1}
        raw,report=flow.solve(target,2.)
        self.assertTrue(r.audit(raw,target)['passed']);self.assertEqual(r.audit(raw,target)['studComponentCount'],2)
        self.assertTrue(report['floorSourcesAreReachabilityOnlyNotPhysicalConnections'])
    def test_ground_flow_cannot_connect_across_empty_space(self):
        target={(0,0,0):0,(0,0,1):0,(5,0,5):0,(5,0,6):0}
        raw,_=flow.solve(target,2.)
        self.assertFalse(r.audit(raw,target)['passed'])
    def test_small_delete_after_real_additions_failure_stays_within_two_percent(self):
        target={(x,y,z):0 for x in range(2) for y in range(8) for z in range(6)}
        target[(7,7,7)]=0x123456
        result=r.optimize(target,3.)
        self.assertTrue(r.audit(result['bricks'],result['targetCells'])['passed'])
        self.assertTrue(result['additionsOnlyFailure']);self.assertFalse(result['additionsOnlyEvidence']['passed'])
        self.assertEqual(result['repairAudit']['removedVoxelCount'],1)
        self.assertLessEqual(result['repairAudit']['changeRatio'],.02)


if __name__=='__main__':unittest.main()
