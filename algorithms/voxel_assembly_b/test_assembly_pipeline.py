import json
import itertools
from pathlib import Path
import tempfile
import unittest

import assembly_pipeline as a


POLICY = dict(world_dim=48,brick_library='extended',min_support_fraction=.1,
              max_cantilever_distance=2,max_components=64)


class AssemblyTests(unittest.TestCase):
    def source(self,points,color=(0,0,0)):
        return {'modelId':'test','actualVoxelCount':len(points),
                'voxels':[dict(x=x,y=y,z=z,color=list(color)) for x,y,z in points]}

    def test_rgb_and_axis_and_black(self):
        model,original=a.dataset_model(self.source([(1,0,3),(1,2,3)],(0,23,255)))
        self.assertEqual(model.cells,{(1,3,0):0x0017FF,(1,3,2):0x0017FF})
        self.assertIn((1,2,3),original)
        black,_=a.dataset_model(self.source([(0,0,0)]))
        self.assertEqual(black.cells[(0,0,0)],0)

    def test_invalid_color_and_duplicate_rejected(self):
        for source in (self.source([(0,0,0),(0,0,0)]),self.source([(0,0,0)],(0,0,256)),
                       self.source([(0,.5,0)])):
            with self.assertRaises(ValueError):
                a.dataset_model(source)

    def test_independent_ground_is_not_connection(self):
        bricks=[dict(h=1,w=1,x=x,y=0,z=0,color=0) for x in (0,1)]
        result=a.independent_audit(bricks,{(0,0,0):0,(1,0,0):0},POLICY)
        self.assertFalse(result['passed'])
        self.assertEqual(result['studComponentCount'],2)
        self.assertTrue(result['exactCoverage'])

    def test_two_legs_real_bridge_and_color_boundaries(self):
        bricks=[dict(h=1,w=1,x=x,y=0,z=0,color=0) for x in (0,3)]
        bricks.append(dict(h=4,w=1,x=0,y=0,z=1,color=0xFF0000))
        target={(0,0,0):0,(3,0,0):0,**{(x,0,1):0xFF0000 for x in range(4)}}
        result=a.independent_audit(bricks,target,POLICY)
        self.assertTrue(result['passed'])
        self.assertEqual(result['studComponentCount'],1)
        self.assertIsNone(result['staticVerified'])

    def test_collision_wrong_color_missing_voxel_rejected(self):
        brick=dict(h=1,w=1,x=0,y=0,z=0,color=0)
        for bricks,target in (([brick,brick],{(0,0,0):0}),([brick],{(0,0,0):1}),
                              ([brick],{(0,0,0):0,(1,0,0):0})):
            self.assertFalse(a.independent_audit(bricks,target,POLICY)['passed'])

    def test_side_color_seam_necessary_disconnection(self):
        model=a.VoxelModel({(0,0,0):0,(1,0,0):0xFF0000})
        result=a.feasibility(model,a.GeometryConfig(world_dim=48,min_bricks=1,brick_library='extended',max_cantilever_distance=2))
        self.assertFalse(result['passed'])
        self.assertEqual(result['reason'],'disconnected_possible_stud_graph')

    def test_impossible_unsupported_color_witness(self):
        # Sideways red tip touches source body, but no same-color brick can
        # reach the black column's support stud from the red-only cell.
        model=a.VoxelModel({(0,0,0):0,(0,0,1):0,(1,0,1):0xFF0000})
        self.assertFalse(a.feasibility(model,a.GeometryConfig(world_dim=48,min_bricks=1,brick_library='extended'))['passed'])

    def test_prefix_cantilever_and_order_rejected(self):
        bricks=[dict(h=1,w=1,x=0,y=0,z=0,color=0),dict(h=8,w=1,x=0,y=0,z=1,color=0)]
        target={(0,0,0):0,**{(x,0,1):0 for x in range(8)}}
        self.assertFalse(a.independent_audit(bricks,target,POLICY)['passed'])

    def test_ldr_all_parts_all_rotations_and_rgb(self):
        for h,w in a.dimensions_for_library('extended'):
            raw=dict(h=h,w=w,x=3,y=4,z=2)
            text=a.to_ldr({'status':'success','bricks':[raw]},{(3,4,2):0x0017FF})
            self.assertEqual(a.parse_ldr(text),[{**raw,'color':0x0017FF}])

    def test_export_readback_detects_tamper(self):
        source=self.source([(0,0,0),(1,0,0)])
        raw=dict(h=2,w=1,x=0,y=0,z=0,color=0)
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            a.dump(folder/'assembly.json',{'status':'success','bricks':[raw]})
            (folder/'model.txt').write_text('2x1 (0,0,0)\n',encoding='utf8')
            (folder/'model.ldr').write_text(a.to_ldr({'status':'success','bricks':[{k:v for k,v in raw.items() if k!='color'}]}, {(0,0,0):0}),encoding='utf8')
            self.assertTrue(a.exported_audit(folder,source,POLICY)['passed'])
            (folder/'model.txt').write_text('1x1 (0,0,0)\n',encoding='utf8')
            self.assertFalse(a.exported_audit(folder,source,POLICY)['passed'])

    def test_necessary_conditions_do_not_reject_tiny_solvable_inputs(self):
        # Exhaust all 3^4 absent/black/red configurations in a 2x1x2 grid.
        # Enumerate rectangular tilings independently of the production search.
        points=[(x,0,z) for z in range(2) for x in range(2)]
        cfg=a.GeometryConfig(world_dim=48,min_bricks=1,brick_library='extended',max_cantilever_distance=2)
        solved=0
        def has_tiling(cells,remaining,bricks):
            if not remaining:
                return a.independent_audit(bricks,cells,POLICY)['passed']
            anchor=min(remaining,key=lambda p:(p[2],p[0],p[1]))
            for h,w in cfg.dimensions:
                for dx in range(h):
                    for dy in range(w):
                        x,y,z=anchor[0]-dx,anchor[1]-dy,anchor[2]
                        footprint={(xx,yy,z) for xx in range(x,x+h) for yy in range(y,y+w)}
                        if footprint <= remaining and all(cells[p]==cells[anchor] for p in footprint):
                            raw=dict(h=h,w=w,x=x,y=y,z=z,color=cells[anchor])
                            if has_tiling(cells,remaining-footprint,bricks+[raw]):
                                return True
            return False
        for values in itertools.product((None,0,0xFF0000),repeat=4):
            cells={p:c for p,c in zip(points,values) if c is not None}
            if cells and has_tiling(cells,set(cells),[]):
                solved+=1
                self.assertTrue(a.feasibility(a.VoxelModel(cells),cfg)['passed'])
        self.assertGreater(solved,0)

    def test_mrv_layer_cover_keeps_actual_brick_policy(self):
        import layer_cover
        cfg=a.GeometryConfig(world_dim=48,min_bricks=1,brick_library='extended',max_cantilever_distance=2)
        targets=[{(x,y,z):0 for x in range(6) for y in range(4) for z in range(2)},
                 {(0,0,0):0,(3,0,0):0,**{(x,0,1):0xFF0000 for x in range(4)}}]
        for cells in targets:
            raw,_=layer_cover.solve(a.VoxelModel(cells),cfg)
            self.assertTrue(a.independent_audit(raw,cells,POLICY)['passed'])
        separate={(0,0,0):0,(1,0,0):0xFF0000}
        raw,_=layer_cover.solve(a.VoxelModel(separate),cfg)
        self.assertFalse(a.independent_audit(raw,separate,POLICY)['passed'])


if __name__=='__main__':
    unittest.main()
