"""Independent mixed repair audit; original-ground/core/color are protected."""
from collections import defaultdict
import math
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'voxel_assembly_q3'))
import joint_cover as prior
q=prior.q
VERSION='mixed_local_repair_audit_q4_v1'


def deletion_eligibility(original,ratio=.02):
    """Complete original-only catalog test, not a truncated solver inference.

    Permit only unsupported original voxels, or a whole small component with no
    possible original stud path to ground. Possible components over-approximate
    real bricks, so absence of a path is conservative. Ground is always protected.
    This is a structural filter, not a claim of semantic insignificance.
    """
    cap=q.budget_for(len(original),ratio)
    if not cap:return {}
    supported=set()
    for x,y,z in sorted(original):
        for h,w in q.a.dimensions_for_library(q.POLICY['brick_library']):
            footprint=tuple(q.a.Placement(h,w,x,y,z).cells())
            if not all(original.get(p)==original[(x,y,z)] for p in footprint):continue
            lower=[(p[0],p[1],z-1) for p in footprint if (p[0],p[1],z-1) in original]
            if z and len(lower)<math.ceil(h*w*q.POLICY['min_support_fraction']):continue
            if z and any(not any(abs(p[0]-s[0])+abs(p[1]-s[1])<=q.POLICY['max_cantilever_distance'] for s in lower) for p in footprint):continue
            supported.update(footprint)
    eligible={p:'no_supported_original_catalog_rectangle' for p in original if p[2]>0 and p not in supported}
    labels,_=q.possible_components(original);groups=defaultdict(list)
    for p,label in labels.items():groups[label].append(p)
    for points in groups.values():
        if len(points)<=cap and all(p[2]>0 for p in points):
            for p in points:eligible[p]='small_original_component_without_ground_stud_path'
    return eligible


def repair_audit(original,target,ratio=.02):
    # Q2 independently validates coordinate/color/local-addition rules and counts;
    # only its "no removal" rule is replaced below, never its budget/palette rules.
    value=q.repair_audit(original,target,ratio)
    if 'changedVoxelCount' not in value:return value
    removed=set(original)-set(target);eligible=deletion_eligibility(original,ratio) if removed else {}
    deletion_ok=all(p in eligible for p in removed)
    value.update(auditorVersion=VERSION,
                 allDeletionsEligibleUnsupportedDetail=deletion_ok,
                 groundVoxelCountPreserved=sum(p[2]==0 for p in original)==sum(p[2]==0 for p in set(original)&set(target)),
                 removedVoxelsInternalXYZRGB=[{'xyz':list(p),'rgb':[(original[p]>>16)&255,(original[p]>>8)&255,original[p]&255],
                                              'reason':eligible.get(p,'protected_original_voxel')} for p in sorted(removed)])
    value['passed']=bool(original) and bool(target) and not value['recoloredOriginalVoxelCount'] and deletion_ok and value['groundVoxelCountPreserved'] and value['allAdditionsWithinOneManhattanStepOfOriginal'] and value['addedColorsFromOriginalPalette'] and value['changedVoxelCount']<=value['maximumChangedVoxelCount']
    return value
