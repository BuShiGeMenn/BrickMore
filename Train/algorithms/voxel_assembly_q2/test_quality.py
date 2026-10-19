import itertools
import json
from pathlib import Path
import random
import tempfile
import time
import unittest

import quality_core as q
import quality_pipeline as p


class QualityTests(unittest.TestCase):
    def source(self,cells):
        return {'modelId':'quality_test','actualVoxelCount':len(cells),
                'voxels':[dict(x=x,y=z,z=y,color=[(c>>16)&255,(c>>8)&255,c&255])
                          for (x,y,z),c in sorted(cells.items())]}

    def test_global_backtracks_instead_of_freezing_first_layer(self):
        import layer_cover
        cells={(x,y,0):0 for x in range(3) for y in range(3)}
        cells.update({(x,0,1):0xFF0000 for x in range(3)})
        cfg=q.a.GeometryConfig(**q.POLICY,min_bricks=1)
        old,_=layer_cover.solve(q.a.VoxelModel(cells),cfg)
        self.assertFalse(q.a.independent_audit(old,cells,q.POLICY)['passed'])
        raw,details=q.solve(q.a.VoxelModel(cells),cfg,future_pruning=False)
        self.assertTrue(q.a.independent_audit(raw,cells,q.POLICY)['passed'])
        self.assertGreater(details['stats'].get('rollback_bricks',0),0)
        self.assertGreater(details['stats'].get('orphan_frontier_pruned',0),0)
        pruned,_=q.solve(q.a.VoxelModel(cells),cfg)
        self.assertTrue(q.a.independent_audit(pruned,cells,q.POLICY)['passed'])

    def test_local_addition_fixes_color_tip_without_recolor(self):
        cells={(x,y,z):0 for x in range(2) for y in range(8) for z in range(6)}
        cells[(2,0,5)]=0xFF0000
        original=cells.copy(); result=q.optimize(q.a.VoxelModel(cells),max_seconds=3)
        self.assertEqual(cells,original)
        self.assertEqual(result['status'],'success')
        audit=result['repairAudit']
        self.assertEqual(audit['addedVoxelCount'],1)
        self.assertEqual(audit['removedVoxelCount'],0)
        self.assertEqual(audit['recoloredOriginalVoxelCount'],0)
        self.assertLessEqual(audit['changeRatio'],.02)
        self.assertTrue(q.a.independent_audit(result['bricks'],result['targetCells'],q.POLICY)['passed'])

    def test_zero_ratio_keeps_impossible_original_failed(self):
        cells={(0,0,0):0,(1,0,0):0xFF0000}
        result=q.optimize(q.a.VoxelModel(cells),max_ratio=0,max_seconds=.1)
        self.assertEqual(result['status'],'draft')
        self.assertEqual(result['targetCells'],cells)

    def test_sub_50_voxels_do_not_get_one_voxel_allowance(self):
        cells={(x,0,z):0 for x in range(2) for z in range(10)}
        cells[(2,0,9)]=0xFF0000
        result=q.optimize(q.a.VoxelModel(cells),max_seconds=.2)
        self.assertEqual(result['status'],'draft')
        self.assertEqual(result['repairAudit']['maximumChangedVoxelCount'],0)
        self.assertEqual(result['repairAudit']['changedVoxelCount'],0)

    def test_quality_rejects_removal_recolor_far_addition_and_new_palette(self):
        original={(x,y,z):0 for x in range(2) for y in range(5) for z in range(10)}
        cases=[]
        removed=original.copy(); removed.pop((0,0,0)); cases.append(removed)
        recolored=original.copy(); recolored[(0,0,0)]=1; cases.append(recolored)
        cases.append({**original,(20,20,20):0})
        cases.append({**original,(2,0,0):0xFFFFFF})
        cases.append({**original,(2,0,0):0,(2,1,0):0,(2,2,0):0})
        for target in cases:self.assertFalse(q.repair_audit(original,target)['passed'])

    def test_exact_integer_budget_and_invalid_options(self):
        self.assertEqual(q.budget_for(1250,.02),25)
        self.assertEqual(q.budget_for(99,.02),1)
        for ratio in (-.01,.020001,float('inf'),float('nan')):
            with self.assertRaises(ValueError):q.budget_for(100,ratio)
        for seconds,nodes in ((0,1),(1,0),(float('nan'),1)):
            with self.assertRaises(ValueError):q.optimize(q.a.VoxelModel({(0,0,0):0}),max_seconds=seconds,max_nodes=nodes)

    def test_invalid_target_coordinate_fails_closed(self):
        self.assertFalse(q.repair_audit({(0,0,0):0},{(0,0):0})['passed'])
        self.assertFalse(q.repair_audit({(0,0,0):0},{(0,0,0):False})['passed'])

    def test_incremental_independent_audit_parity_random_invalid_layouts(self):
        rng=random.Random(4729)
        points={(x,y,z):rng.choice((0,0xFF0000)) for x in range(4) for y in range(3) for z in range(3)}
        policy={**q.POLICY,'max_components':2}
        for _ in range(150):
            bricks=[]
            for i in range(rng.randrange(1,16)):
                h,w=rng.choice(q.a.dimensions_for_library('extended'))
                b=dict(h=h,w=w,x=rng.randrange(-1,5),y=rng.randrange(4),z=rng.randrange(4),color=rng.choice((0,0xFF0000)))
                if i%7==0 and rng.random()<.3:b['w']=False
                bricks.append(b)
            self.assertEqual(q.independent_audit(bricks,points,policy),q.a.independent_audit(bricks,points,policy))

    def test_rollback_union_find_restores_every_mutable_index(self):
        state=q.RollbackState(64)
        state.push(q.a.Placement(1,1,0,0,0)); state.push(q.a.Placement(1,1,2,0,0))
        before=(state.bricks.copy(),state.owner.copy(),state.parents.copy(),state.sizes.copy(),state.components)
        self.assertTrue(state.push(q.a.Placement(3,1,0,0,1)))
        self.assertEqual(state.components,1); state.pop()
        self.assertEqual(before,(state.bricks,state.owner,state.parents,state.sizes,state.components))

    def test_tiny_exact_solver_matches_exhaustive_tiling_oracle(self):
        # All nonempty subsets of a 2x2x2 black grid. An independent simple
        # tiling enumeration prevents generator/auditor bugs agreeing silently.
        points=[(x,y,z) for z in range(2) for x in range(2) for y in range(2)]
        dims=((1,1),(1,2),(2,1),(2,2))
        def oracle(cells,remaining,raw):
            if not remaining:return q.a.independent_audit(raw,cells,q.POLICY)['passed']
            x,y,z=min(remaining,key=lambda r:(r[2],r[0],r[1]))
            for h,w in dims:
                for dx in range(h):
                    for dy in range(w):
                        b=dict(h=h,w=w,x=x-dx,y=y-dy,z=z,color=0)
                        footprint={(xx,yy,z) for xx in range(x-dx,x-dx+h) for yy in range(y-dy,y-dy+w)}
                        if footprint<=remaining and oracle(cells,remaining-footprint,raw+[b]):return True
            return False
        for mask in range(1,1<<len(points)):
            cells={p:0 for i,p in enumerate(points) if mask&(1<<i)}
            expected=oracle(cells,set(cells),[])
            raw,_=q.solve(q.a.VoxelModel(cells),max_seconds=.5,max_nodes=20000)
            self.assertEqual(q.a.independent_audit(raw,cells,q.POLICY)['passed'],expected,str(mask))

    def test_repaired_export_identity_original_bytes_and_tamper(self):
        cells={(x,y,z):0 for x in range(2) for y in range(8) for z in range(6)}
        cells[(2,0,5)]=0xFF0000
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'input.json'; source.write_text(json.dumps(self.source(cells)),encoding='utf8')
            original=source.read_bytes(); out=Path(temp)/'out'
            row=p.run_model(source,out,seconds=3)
            self.assertEqual(row['status'],'success')
            self.assertNotEqual(row['modelId'],row['targetModelId'])
            self.assertEqual((out/'source.model.json').read_bytes(),original)
            self.assertEqual(source.read_bytes(),original)
            self.assertEqual(row['promptBindingStatus'],'original_source_only_not_revalidated_for_repaired_geometry')
            self.assertTrue(row['validation']['legacyAuditorParityPassed'])
            p.verify_output(out,source)
            (out/'model.ldr').write_text('0 forged\n',encoding='utf8')
            with self.assertRaises(ValueError):p.verify_output(out,source)

    def test_checkpoint_change_and_unsealed_directory_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'input.json'; source.write_text(json.dumps(self.source({(0,0,0):0})),encoding='utf8')
            out=Path(temp)/'out'; p.run_model(source,out,seconds=.5)
            p.run_model(source,out,seconds=.5)
            with self.assertRaises(ValueError):p.run_model(source,out,seconds=.7)
            with self.assertRaises(ValueError):p.run_model(source,Path(temp),seconds=.5)

    def test_forged_physics_and_action_history_are_rejected(self):
        cells={(x,y,z):0 for x in range(2) for y in range(8) for z in range(6)}
        cells[(2,0,5)]=0xFF0000
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'source.json'; source.write_text(json.dumps(self.source(cells)),encoding='utf8')
            out=Path(temp)/'out'; row=p.run_model(source,out,seconds=2)
            self.assertEqual(row['status'],'success')
            q.a.dump(out/'report.json',{**row,'fullPhysics':True})
            with self.assertRaises(ValueError):p.verify_output(out,source)
            q.a.dump(out/'report.json',{**row,'repairActions':[]})
            with self.assertRaises(ValueError):p.verify_output(out,source)

    def test_missing_baseline_is_unknown_not_zero_success(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'source.json'; source.write_text(json.dumps(self.source({(0,0,0):0})),encoding='utf8')
            out=Path(temp)/'run'
            p.run_model(source,out/'models'/'test'/'quality_test',seconds=.5,category='test')
            config={'algorithmVersion':q.VERSION,'action':'run','sampleDesign':'no baseline',
                    'split':'all','seed':1729,'perStratum':2,'options':{},'manifestSha256':'test',
                    'baselineIndexSha256':None,'selectionSha256':'test','sourceCodeSha256':p.source_hashes()}
            summary=p.summarize(out,[{'modelId':'quality_test','category':'test'}],config,time.monotonic())
            self.assertEqual(summary['optimizedPassedCount'],1)
            self.assertFalse(summary['baselineAvailable'])
            self.assertIsNone(summary['baselinePassedCount'])
            self.assertIsNone(summary['additionalPassedCount'])
            self.assertIsNone(summary['baselineSuccessRegressions'])


if __name__=='__main__':unittest.main()
