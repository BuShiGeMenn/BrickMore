"""Record new and legacy regression gates plus an independent-auditor benchmark."""
from pathlib import Path
import sys
import time
import unittest

import quality_core as q
import quality_pipeline as p


def main():
    sys.path.insert(0,str(p.HERE.parent.parent/'tools'))
    names=['test_quality','test_assembly_pipeline','test_single_model','test_package_assembly','test_merge_tools']
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    cells={(x,y,z):0 for z in range(10) for x in range(10) for y in range(10)}
    raw=[dict(h=1,w=1,x=x,y=y,z=z,color=0) for x,y,z in sorted(cells,key=lambda r:(r[2],r[0],r[1]))]
    expected=q.a.independent_audit(raw,cells,q.POLICY)
    actual=q.independent_audit(raw,cells)
    if expected!=actual:raise ValueError('auditor performance fixture parity failure')
    timing={}
    for name,fn in [('legacy_recount_roots',q.a.independent_audit),('incremental_independent_dsu',q.independent_audit)]:
        started=time.perf_counter()
        for _ in range(10):fn(raw,cells,q.POLICY)
        timing[name]=(time.perf_counter()-started)/10
    report={'passed':result.wasSuccessful(),'testCount':result.testsRun,
            'failureCount':len(result.failures),'errorCount':len(result.errors),
            'sourceCodeSha256':p.source_hashes(),
            'auditorBenchmark':{'brickCount':1000,'repetitions':10,'identicalResults':True,
                'fixtureIsSuccessfulAssembly':False,
                'fixtureScope':'fragmented complete draft; no false physical/stud success',
                'meanSeconds':timing,'observedSpeedup':timing['legacy_recount_roots']/timing['incremental_independent_dsu']},
            'exhaustiveTinyOccupancyCases':255,'randomAuditParityCases':150,
            'originalPublishedAlgorithmsModified':False,'fullPhysics':False,'semanticVerified':False}
    q.a.dump(p.HERE/'reports'/'tests.json',report)
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
