"""Record regression tests, committed LF hashes and observed runtime hashes."""
import unittest
import package_assembly as p


def main():
    suite=unittest.defaultTestLoader.loadTestsFromNames(['test_package_assembly','test_merge_tools'])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    names=('package_assembly.py','download_assembly.py','run_shard_assembly.py',
           'github_release.py','download_dataset.py','test_package_assembly.py',
           'test_merge_tools.py','verify_assembly_tools.py','verify_assembly_kernel.py')
    report={'passed':result.wasSuccessful(),'testCount':result.testsRun,
            'failureCount':len(result.failures),'errorCount':len(result.errors),
            'sourceFileSha256':{name:p.a.sha((p.ROOT/'tools'/name).read_bytes().replace(b'\r\n',b'\n')) for name in names},
            'observedLocalSourceFileSha256':{name:p.digest(p.ROOT/'tools'/name) for name in names},
            'sourceHashConvention':'sourceFileSha256 uses committed LF; observedLocalSourceFileSha256 records actual runtime bytes',
            'scope':'Portable archive, original prompt binding, safe extraction, parallel metadata ordering, draft reuse; not full physics',
            'fullPhysics':False}
    p.a.dump(p.ROOT/'datasets'/'assembly_80000'/'tool_tests.json',report)
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
