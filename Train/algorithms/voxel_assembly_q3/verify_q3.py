"""Run Q3 + sealed Q2/legacy/tool regression suites and save evidence."""
from pathlib import Path
import sys
import time
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import experiment as e


def main():
    started=time.monotonic();loader=unittest.TestLoader();suite=unittest.TestSuite()
    for folder,pattern in ((HERE,'test_q3.py'),(HERE.parent/'voxel_assembly_q2','test_quality.py'),
                           (e.q.LEGACY,'test_*.py'),(e.REPO/'tools','test_*.py')):
        sys.path.insert(0,str(folder));suite.addTests(loader.discover(str(folder),pattern=pattern,top_level_dir=str(folder)))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    value={'algorithmVersion':e.VERSION,'testCount':result.testsRun,'passed':result.wasSuccessful(),
           'failures':len(result.failures),'errors':len(result.errors),'sourceCodeSha256':e.hashes(),
           'elapsedSeconds':time.monotonic()-started}
    e.q.a.dump(HERE/'reports'/'tests.json',value)
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
