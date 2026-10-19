"""Balanced scheduler, retained evidence and parallel actual-ZIP readback tests."""
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import unittest

import run_quality_balanced as b
import test_quality_delivery as delivery


class BalancedTests(unittest.TestCase):
    def test_budget_never_relaxes_quality_or_physics(self):
        for remaining in (1,1000,80000):
            for delta in (-1,3600,43200):
                value=b.profile(100,100+delta,remaining,8)
                self.assertEqual(value['ratio'],.02);self.assertEqual(value['physicsSeconds'],5.)
                self.assertEqual(value['candidateLimit'],80000);self.assertEqual(value['cutRounds'],16)
                self.assertGreater(value['seconds'],0);self.assertGreater(value['additionsSeconds'],0)
                self.assertLessEqual(value['seconds']+value['additionsSeconds'],5.0001)
        self.assertLess(b.profile(100,3700,80000,8)['seconds'],b.profile(100,43300,80000,8)['seconds'])

    def test_bounded_parallel_reader_preserves_order(self):
        with ThreadPoolExecutor(max_workers=3) as pool:
            self.assertEqual(list(b.pack.bounded_map(pool,abs,range(-20,0),window=4)),list(range(20,0,-1)))

    def test_reuse_keeps_prior_report_bytes_and_actual_options(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);_,job,previous,_=delivery.DeliveryTests().fixture(root)
            prior=previous/'models'/job['category']/job['modelId'];raw=(prior/'report.json').read_bytes()
            job.update(retainedQ4Path=str(prior),retainedQ4ReportSha256=b.q.a.sha(raw))
            out=root/'new';out.mkdir();options=b.profile(0,43200,80000,2)
            light=dict(options=options,algorithmSourceCodeSha256=b.e.hashes(),previousPlanSha256='prior-proof')
            b.initialize_worker(light,str(out),'new-plan');b.compute((job,options))
            target=out/'models'/job['category']/job['modelId']
            self.assertEqual((target/'report.json').read_bytes(),raw)
            workflow=json.loads((target/'workflow.json').read_bytes())
            self.assertEqual(workflow['retainedPlanSha256'],'prior-proof')
            self.assertEqual(workflow['actualOptions'],json.loads(raw)['options'])
            self.assertNotEqual(workflow['actualOptions'],options)
            self.assertEqual(b.compute((job,options))['status'],'success')

    def test_reuse_rejects_modified_prior_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);_,job,previous,_=delivery.DeliveryTests().fixture(root)
            prior=previous/'models'/job['category']/job['modelId']
            job.update(retainedQ4Path=str(prior),retainedQ4ReportSha256='changed')
            out=root/'new';out.mkdir();options=b.profile(0,43200,80000,2)
            b.initialize_worker(dict(options=options,algorithmSourceCodeSha256=b.e.hashes(),previousPlanSha256='old'),str(out),'new')
            with self.assertRaises(ValueError):b.compute((job,options))
            self.assertFalse((out/'models').exists())

    def test_actual_zip_parallel_prepare_and_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,job,out,_=delivery.DeliveryTests().fixture(Path(tmp))
            with ProcessPoolExecutor(max_workers=2) as pool:
                proof=b.pack.make_package(out,'A',1,[job],'balanced-test','sealed-plan-test',audit_pool=pool)
            self.assertTrue(proof['allPublicZipCrcShaGeometryRepairGateAndPhysicsReadbackPassed'])
            self.assertEqual(proof['rows'][0]['removedVoxelCount'],1)
            self.assertFalse(proof['rows'][0]['fullPhysics'])

    def test_fast_seed_actual_exports_and_deletion_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);dataset,job,_,_=delivery.DeliveryTests().fixture(root)
            options=dict(ratio=.02,additionsSeconds=1.,seconds=3.,physicsSeconds=5.,candidateLimit=80000,cutRounds=16)
            report=b.seed.worker((job,str(dataset),str(root/'seed'),options))
            self.assertEqual(report['status'],'success')
            self.assertEqual(report['generationDriverVersion'],b.seed.VERSION)
            self.assertEqual(report['generationDriverSha256'],b.q.a.file_sha(b.seed.__file__))
            self.assertEqual(report['repairAudit']['removedVoxelCount'],1)
            self.assertFalse(report['additionsOnlyGate']['geometryPassed'])
            self.assertFalse(report['fullPhysics']);self.assertIsNone(report['staticVerified'])


def main():
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BalancedTests))
    b.pack.atomic_json(b.ROOT/'datasets/q4_assembly_80000/balanced_tests.json',dict(passed=result.wasSuccessful(),
                      testCount=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                      schedulerVersion=b.VERSION,algorithmSourceCodeSha256=b.e.hashes(),
                      schedulerSha256=b.q.a.file_sha(b.ROOT/'tools/run_quality_balanced.py'),
                      packagerSha256=b.q.a.file_sha(b.ROOT/'tools/package_quality.py')))
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
