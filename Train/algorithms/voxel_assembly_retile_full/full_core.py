"""Run fresh retiling before considering a verified successful fallback."""
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'voxel_assembly_retile'))
import retile_core as retile

VERSION='fresh_local_monochrome_bridge_retile_v2'

def fresh_search(original,seconds):
    return retile.optimize(original,seconds=seconds,baseline=None)

def optimize(original,seconds=8.,baseline=None):
    started=time.monotonic()
    fresh=fresh_search(original,seconds)
    passed=retile.base.audit(fresh['bricks'],fresh['targetCells'])['passed']
    decision=dict(stage='fresh_retile_before_success_fallback',freshSearchAttempted=True,freshGeometryPassed=passed)
    selected=fresh
    if not passed and baseline is not None and retile.base.audit(baseline['bricks'],baseline['targetCells'])['passed']:
        # This call rechecks repair eligibility and actual additions-only failure
        # evidence before retaining a layout containing protected deletions.
        selected=retile.optimize(original,seconds=seconds,baseline=baseline)
        decision['freshSearchAttempts']=fresh['searchAttempts']
    selected['searchAttempts']=[decision]+selected['searchAttempts']
    selected['elapsedSeconds']=time.monotonic()-started
    selected['algorithmVersion']=VERSION
    return selected
