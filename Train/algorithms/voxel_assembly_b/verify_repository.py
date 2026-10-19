"""Run the repository tests and record source SHA-256 for reproducibility."""
import json
from pathlib import Path
import unittest

import assembly_pipeline as a


def main():
    suite = unittest.defaultTestLoader.loadTestsFromNames(
        ['test_assembly_pipeline', 'test_single_model'])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    root = Path(__file__).resolve().parent
    sources = sorted(root.glob('*.py')) + sorted((root/'toolkit_snapshot').glob('*.py'))
    report = {
        'passed': result.wasSuccessful(),
        'testCount': result.testsRun,
        'failureCount': len(result.failures),
        'errorCount': len(result.errors),
        'skippedCount': len(result.skipped),
        'sourceFileSha256': {
            path.relative_to(root).as_posix(): a.file_sha(path) for path in sources
        },
        'scope': 'Repository unit tests and synthetic single-model readback; not full physics',
        'fullPhysics': False,
    }
    a.dump(root/'reports'/'repository_tests.json', report)
    print(json.dumps({k: report[k] for k in ('passed', 'testCount', 'failureCount', 'errorCount')}))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
