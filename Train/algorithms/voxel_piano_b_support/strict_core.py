"""Exact occupancy/RGB retiling: never repair a keyboard with exterior voxels."""
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'voxel_assembly_retile'))
import retile_core as retile
VERSION='piano_supported_keyboard_exact_retile_v1'

def optimize(original,seconds=8.,baseline=None):
    started=time.monotonic();attempts=[];candidates=[]
    for variant in (0,1):
        raw=retile.ordered(retile.connectors.cover(original,variant))
        candidates.append((retile.objective(raw,original,original),raw))
    _,raw=min(candidates,key=lambda q:q[0])
    if not retile.base.audit(raw,original)['passed']:
        raw,cells,info=retile.search(original,raw,original.copy(),started+seconds,allow_additions=False)
        if cells!=original:raise ValueError('Exact-only search changed geometry')
        attempts.append(info)
    attempts.insert(0,dict(stage='exact_source_cover_only',additionsAllowed=False,deletionsAllowed=False,originalRgbPreserved=True))
    passed=retile.base.audit(raw,original)['passed']
    return retile.result(original,raw,original.copy(),attempts,started,retainedBaseline=False,
                         additionsOnlyFailure=not passed,additionsOnlyEvidence=None if passed else dict(bricks=raw,targetCells=original.copy(),passed=False))
