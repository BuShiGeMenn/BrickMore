"""Unchanged force/moment/witness model, with explicit modular geometry guard."""
import threading
import math
from pathlib import Path

import relaxed_core as r
g=r.strict.g;q=r.q
VERSION='modular_geometry_guard_rejected_solver_diagnostics_v2'
# Only the exact previously sealed adapter is accepted for preserved results.
PREVIOUS_ADAPTER=('modular_geometry_guard_same_gravity_witness_v1',
                  'f9bc91cd8fba781414ff160f3184ed5543ef0d647929b8d9eb6860fbef6d0d18')
_LOCK=threading.RLock()


def _call(fn,*args):
    # Isolated process workers only. Restore the existing strict checker even on
    # exceptions; changing geometry eligibility never changes force equations,
    # floor/contact geometry, masses, clutch calibration or witness tolerance.
    with _LOCK:
        old=q.independent_audit
        q.independent_audit=lambda bricks,target,*ignored,**kw:r.audit(bricks,target)
        try:return fn(*args)
        finally:q.independent_audit=old


def screen(bricks,cells,seconds=5.):
    if not r.audit(bricks,cells)['passed']:raise ValueError('modular physics requires actual grounded geometry')
    value=_call(g.screen,bricks,cells,seconds)
    separate_rejected_witness(value,bricks)
    value.update(geometryPolicyVersion=r.VERSION,geometryGuardAdapterVersion=VERSION,
                 geometryGuardAdapterSha256=q.a.file_sha(__file__))
    return value


def rejection_diagnostic(bricks,value,witness):
    """Rebuild a rejected solver candidate, never call it a valid witness."""
    contacts,_=g.expected_contacts(bricks);forces=witness['signedForcesUnitWeights']
    if witness['contacts']!=[list(c) for c in contacts] or len(forces)!=len(contacts) or not forces or any(not isinstance(f,(int,float)) or isinstance(f,bool) or not math.isfinite(f) for f in forces):
        raise ValueError('invalid rejected solver candidate')
    residual=g.witness_residual(bricks,contacts,forces,[b['h']*b['w'] for b in bricks])
    reported=value.get('maximumBalanceResidualUnitWeights')
    if not isinstance(reported,(int,float)) or isinstance(reported,bool) or not math.isfinite(reported) or abs(residual-reported)>1e-9:
        raise ValueError('rejected solver residual differs')
    # Keep the original 1e-6 residual and -1e-7 force bounds unchanged.
    residual_failed=residual>1e-6
    compression_failed=value.get('compressionSolverStatus')==0 and min(forces)<-1e-7
    if not (residual_failed or compression_failed) or value['status']!='solver_witness_rejected' or value['gravityEquilibriumPassed'] or value.get('minimumRequiredClutchNewtonsPerStud') is not None:
        raise ValueError('candidate is not an actual rejected solver result')
    return dict(maximumBalanceResidualUnitWeights=residual,balanceResidualLimitUnitWeights=1e-6,
                minimumSignedForceUnitWeights=min(forces),compressionForceLimitUnitWeights=-1e-7,
                residualFailed=residual_failed,compressionForceBoundFailed=compression_failed,
                acceptedAsEquilibriumWitness=False)


def prefix_subsets(bricks):
    for z in sorted({b['z'] for b in bricks})[:-1]:
        raw=[b for b in bricks if b['z']<=z];labels=q.brick_component_labels(raw);groups={}
        for b in raw:groups.setdefault(labels[(b['x'],b['y'],b['z'])],[]).append(b)
        for group,subset in sorted(groups.items()):yield z,group,subset


def separate_rejected_witness(value,bricks):
    if value.get('status')=='solver_witness_rejected' and value.get('equilibriumWitness'):
        witness=value['equilibriumWitness']
        value['solverRejectionDiagnostic']=rejection_diagnostic(bricks,value,witness)
        value['rejectedEquilibriumWitness']=value.pop('equilibriumWitness')
    for row,(z,group,subset) in zip(value.get('layerPrefixReports',[]),prefix_subsets(bricks)):
        if (row['throughLayer'],row['componentLabel'])!=(z,group):raise ValueError('rejected prefix order differs')
        separate_rejected_witness(row['physics'],subset)


def verify_rejections(value,bricks):
    if 'rejectedEquilibriumWitness' in value:
        if value.get('equilibriumWitness') or value.get('layerPrefixGravityPassed'):raise ValueError('rejected candidate counted as physical pass')
        actual=rejection_diagnostic(bricks,value,value['rejectedEquilibriumWitness'])
        if value.get('solverRejectionDiagnostic')!=actual:raise ValueError('rejected solver diagnostic differs')
    elif 'solverRejectionDiagnostic' in value or value.get('status')=='solver_witness_rejected':
        raise ValueError('missing rejected solver diagnostic')
    for row,(z,group,subset) in zip(value.get('layerPrefixReports',[]),prefix_subsets(bricks)):
        if (row['throughLayer'],row['componentLabel'])!=(z,group):raise ValueError('rejected prefix order differs')
        verify_rejections(row['physics'],subset)


def verify(bricks,cells,value):
    adapter=(value.get('geometryGuardAdapterVersion'),value.get('geometryGuardAdapterSha256'))
    if value.get('geometryPolicyVersion')!=r.VERSION or adapter not in (PREVIOUS_ADAPTER,(VERSION,q.a.file_sha(__file__))):
        raise ValueError('modular physical geometry adapter differs')
    if value['assumptions']!=g.ASSUMPTIONS or value.get('fullPhysics') is not False or value.get('staticVerified') is not None or value.get('calibratedPhysicalVerified') is not None:
        raise ValueError('physical assumptions or unsupported certification changed')
    if value.get('layerPrefixGravityPassed') and not value.get('gravityEquilibriumPassed'):raise ValueError('prefix physical pass without final equilibrium')
    if (value.get('status')=='gravity_equilibrium_passed')!=bool(value.get('gravityEquilibriumPassed')):raise ValueError('physical status and equilibrium flag differ')
    if not value.get('equilibriumWitness') and value.get('gravityEquilibriumPassed'):raise ValueError('missing actual force witness')
    verify_rejections(value,bricks)
    # Prefix order, completeness and all accepted force witnesses are still
    # independently checked even when the final screen did not pass.
    _call(g.verify_screen,bricks,cells,value)
    return True
