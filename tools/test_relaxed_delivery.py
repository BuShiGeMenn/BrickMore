"""Actual relaxed exports/ZIPs and unchanged physical witness regressions."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import copy
from unittest.mock import patch
from concurrent.futures import ProcessPoolExecutor

import package_quality as pack
sys.path.insert(0,str(pack.ROOT/'algorithms/voxel_assembly_relaxed'))
import relaxed_pipeline as p
import test_relaxed
import recover_relaxed_full as recovery


class DeliveryTests(unittest.TestCase):
    def rejected_candidate(self,raw,cells):
        value=p.physics.screen(raw,cells,3.)
        self.assertTrue(value['gravityEquilibriumPassed'])
        value['equilibriumWitness']['signedForcesUnitWeights'][0]+=4e-6
        contacts,_=p.physics.g.expected_contacts(raw)
        value['maximumBalanceResidualUnitWeights']=p.physics.g.witness_residual(raw,contacts,value['equilibriumWitness']['signedForcesUnitWeights'],[b['h']*b['w'] for b in raw])
        value.update(status='solver_witness_rejected',gravityEquilibriumPassed=False,minimumRequiredClutchNewtonsPerStud=None,
                     layerPrefixGravityPassed=False,layerPrefixReports=[])
        return value

    def fixture(self,root,floating=False):
        cells={(x,y,z):0 for offset in (0,4) for x in range(offset,offset+2) for y in range(8) for z in range(6)}
        if floating:cells[(10,10,10)]=0x123456
        source=dict(modelId='relaxed_fixture',actualVoxelCount=len(cells),canonicalGeometryHash='fixture',
                    voxels=[dict(x=x,y=z,z=y,color=[c>>16,(c>>8)&255,c&255]) for (x,y,z),c in sorted(cells.items())])
        dataset=root/'dataset';folder=dataset/'models/fixture/relaxed_fixture';folder.mkdir(parents=True)
        p.q.a.dump(folder/'model.json',source)
        job=dict(modelId=source['modelId'],category='fixture',modelPath='models/fixture/relaxed_fixture',datasetPath=str(dataset),shardId='A',
                 baselineStatus='search_failed',priorStrictFolder=str(root/'missing_prior'),canonicalGeometryHash='fixture',
                 exactOccupancyHash=p.q.a.exact_hash({(x,z,y):c for (x,y,z),c in cells.items()}))
        prompts=[dict(modelId=job['modelId'],recordId='relaxed_l'+str(i),promptLevel=i,targetOccupancyHash=job['exactOccupancyHash'],targetCanonicalGeometryHash='fixture') for i in range(1,6)]
        p.q.a.dump(folder/'prompts.json',prompts)
        job.update(originalModelFileSha256=p.q.a.file_sha(folder/'model.json'),originalPromptFileSha256=p.q.a.file_sha(folder/'prompts.json'))
        out=root/'run';report=p.worker((job,str(dataset),str(out),dict(ratio=.02,seconds=8.,physicsSeconds=5.)))
        result=out/'models'/job['category']/job['modelId']
        pack.atomic_json(result/'workflow.json',dict(planSha256='relaxed-plan',origin=report['origin'],actualOptions=report['options'],reportSha256=p.q.a.file_sha(result/'report.json')))
        return dataset,job,out,result,report

    def test_actual_modular_export_two_auditors_and_original_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset,job,out,folder,report=self.fixture(Path(tmp))
            self.assertEqual(report['status'],'success');self.assertEqual(report['geometryValidation']['studComponentCount'],2)
            self.assertFalse(report['fullPhysics']);self.assertIsNone(report['staticVerified'])
            self.assertEqual((folder/'source.model.json').read_bytes(),(dataset/job['modelPath']/'model.json').read_bytes())
            self.assertEqual(p.verify(folder)['geometryValidation'],report['geometryValidation'])

    def test_different_source_byte_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset,job,out,folder,_=self.fixture(Path(tmp));source=dataset/job['modelPath']/'model.json'
            source.write_bytes(source.read_bytes()+b' ')
            with self.assertRaises(ValueError):p.verify(folder,source)

    def test_force_tampering_rejected_even_after_sha_updates(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,_,_,folder,_=self.fixture(Path(tmp))
            force=json.loads((folder/'physics.json').read_bytes());force['equilibriumWitness']['signedForcesUnitWeights'][0]+=1
            p.q.a.dump(folder/'physics.json',force)
            report=json.loads((folder/'report.json').read_bytes());report['physics']=p.strict.physics_summary(force)
            report['outputFileSha256']['physics.json']=p.q.a.file_sha(folder/'physics.json');p.q.a.dump(folder/'report.json',report)
            with self.assertRaises(ValueError):p.verify(folder)

    def test_actual_parallel_zip_all_layers_repair_and_five_prompts(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,job,out,_,report=self.fixture(Path(tmp),True)
            with ProcessPoolExecutor(max_workers=2) as pool:
                proof=pack.make_package(out,'A',1,[job],'relaxed-test','relaxed-plan',audit_pool=pool,auditor_name='relaxed_pipeline')
            self.assertTrue(proof['allPublicZipCrcShaGeometryRepairGateAndPhysicsReadbackPassed'])
            self.assertEqual(proof['promptRecordCount'],5);self.assertEqual(proof['rows'][0]['removedVoxelCount'],1)
            self.assertEqual(proof['rows'][0]['geometryTier'],'relaxed_modular_grounded_not_physical_certification')
            self.assertFalse(proof['rows'][0]['fullPhysics'])

    def test_unknown_auditor_rejected(self):
        with self.assertRaises(ValueError):pack.auditor('arbitrary_module')

    def test_upper_attachment_force_not_uncalibrated_physical_pass(self):
        b=test_relaxed.brick
        raw=[b(0,0,0),b(0,0,1),b(0,0,2),b(1,0,2),b(0,0,3,h=2)]
        cells=test_relaxed.cells_for(raw);value=p.physics.screen(raw,cells,3.)
        self.assertEqual(value['status'],'requires_uncalibrated_clutch')
        self.assertFalse(value['gravityEquilibriumPassed']);self.assertFalse(value['fullPhysics'])
        self.assertIsNone(value['staticVerified']);self.assertTrue(p.physics.verify(raw,cells,value))

    def test_rejected_solver_candidate_is_diagnostic_not_equilibrium(self):
        raw=[test_relaxed.brick(0,0,0),test_relaxed.brick(0,0,1)];cells=test_relaxed.cells_for(raw)
        value=self.rejected_candidate(raw,cells)
        with patch.object(p.physics.g,'screen',return_value=copy.deepcopy(value)):
            normalized=p.physics.screen(raw,cells,3.)
        self.assertNotIn('equilibriumWitness',normalized);self.assertIn('rejectedEquilibriumWitness',normalized)
        self.assertFalse(normalized['gravityEquilibriumPassed']);self.assertFalse(normalized['layerPrefixGravityPassed'])
        self.assertGreater(normalized['solverRejectionDiagnostic']['maximumBalanceResidualUnitWeights'],1e-6)
        self.assertTrue(p.physics.verify(raw,cells,normalized))
        normalized['rejectedEquilibriumWitness']['signedForcesUnitWeights'][0]+=1
        with self.assertRaises(ValueError):p.physics.verify(raw,cells,normalized)

    def test_valid_witness_cannot_be_disguised_as_rejected(self):
        raw=[test_relaxed.brick(0,0,0)];cells=test_relaxed.cells_for(raw);value=p.physics.screen(raw,cells,3.)
        value.update(status='solver_witness_rejected',gravityEquilibriumPassed=False,minimumRequiredClutchNewtonsPerStud=None,layerPrefixGravityPassed=False)
        with self.assertRaises(ValueError):p.physics.separate_rejected_witness(value,raw)

    def test_numpy_solver_scalar_has_same_strict_rejection_bound(self):
        import numpy as np
        raw=[test_relaxed.brick(0,0,0)];cells=test_relaxed.cells_for(raw);value=self.rejected_candidate(raw,cells)
        value['maximumBalanceResidualUnitWeights']=np.float64(value['maximumBalanceResidualUnitWeights'])
        p.physics.separate_rejected_witness(value,raw)
        self.assertTrue(p.physics.verify(raw,cells,value));self.assertFalse(value['gravityEquilibriumPassed'])

    def test_rejected_prefix_remains_failed_and_is_checked(self):
        raw=[test_relaxed.brick(0,0,0),test_relaxed.brick(0,0,1)];cells=test_relaxed.cells_for(raw)
        value=p.physics.screen(raw,cells,3.);prefix=value['layerPrefixReports'][0]
        prefix['physics']=self.rejected_candidate(raw[:1],test_relaxed.cells_for(raw[:1]))
        value['layerPrefixGravityPassed']=False;p.physics.separate_rejected_witness(value,raw)
        self.assertTrue(p.physics.verify(raw,cells,value));self.assertFalse(value['layerPrefixGravityPassed'])
        prefix['physics']['solverRejectionDiagnostic']['balanceResidualLimitUnitWeights']=1e-5
        with self.assertRaises(ValueError):p.physics.verify(raw,cells,value)

    def test_rejected_physics_export_is_not_quality_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset,job,out,folder,report=self.fixture(Path(tmp))
            raw=json.loads((folder/'assembly.json').read_bytes())['bricks'];cells=p.q.a.dataset_model(json.loads((folder/'target.model.json').read_bytes()))[0].cells
            physical=self.rejected_candidate(raw,cells);p.physics.separate_rejected_witness(physical,raw)
            p.q.a.dump(folder/'physics.json',physical);report.update(physics=p.strict.physics_summary(physical),qualityScreenedSuccess=False)
            report['outputFileSha256']['physics.json']=p.q.a.file_sha(folder/'physics.json');p.q.a.dump(folder/'report.json',report)
            checked=p.verify(folder);self.assertEqual(checked['status'],'success');self.assertFalse(checked['qualityScreenedSuccess'])

    def test_sealed_archive_reuse_preserves_bytes_and_rechecks_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);_,job,out,_,_=self.fixture(root)
            proof=pack.make_package(out,'A',1,[job],'relaxed-test','relaxed-plan',auditor_name='relaxed_pipeline')
            parent=out/'delivery/checkpoints/A/01.json';digest=p.q.a.file_sha(parent);target=root/'recovery'
            copied=pack.reuse_sealed_package(target,out,'A',1,[job],'relaxed-test','recovery-plan','relaxed-plan',p.q.a.file_sha(pack.__file__),digest,p.hashes())
            old_zip=out/'delivery'/proof['asset']['sourceRelativePath'];new_zip=target/'delivery'/copied['asset']['sourceRelativePath']
            self.assertEqual(p.q.a.file_sha(old_zip),p.q.a.file_sha(new_zip));self.assertTrue(copied['freshActualZipReadbackPassed'])
            self.assertEqual(copied['rows'][0]['generationPlanSha256'],'relaxed-plan');self.assertEqual(p.q.a.file_sha(parent),digest)
            with self.assertRaises(ValueError):pack.reuse_sealed_package(root/'wrong',out,'A',1,[job],'relaxed-test','recovery-plan','wrong-plan',p.q.a.file_sha(pack.__file__),digest,p.hashes())

    def test_recovery_rejects_unknown_generation_and_wrong_lineage(self):
        current=p.hashes();previous={**current,'old_revision':'a'*64}
        light=dict(algorithmSourceCodeSha256=current,previousModularAlgorithmSourceCodeSha256=previous,previousModularPlanSha256='old-plan')
        recovery.generation(dict(sourceCodeSha256=current),dict(generationPlanSha256='new-plan'),light,'new-plan')
        recovery.generation(dict(sourceCodeSha256=previous),dict(generationPlanSha256='old-plan'),light,'new-plan')
        with self.assertRaises(ValueError):recovery.generation(dict(sourceCodeSha256=previous),dict(generationPlanSha256='new-plan'),light,'new-plan')
        with self.assertRaises(ValueError):recovery.generation(dict(sourceCodeSha256={}),dict(generationPlanSha256='new-plan'),light,'new-plan')


def main():
    suite=unittest.TestSuite((unittest.defaultTestLoader.loadTestsFromTestCase(test_relaxed.RelaxedTests),unittest.defaultTestLoader.loadTestsFromTestCase(DeliveryTests)))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    pack.atomic_json(pack.ROOT/'datasets/relaxed_assembly_80000/tests.json',dict(passed=result.wasSuccessful(),testCount=result.testsRun,
                     failures=len(result.failures),errors=len(result.errors),algorithmVersion=p.VERSION,algorithmSourceCodeSha256=p.hashes(),
                     workflowSourceCodeSha256={name:p.q.a.file_sha(pack.ROOT/name) for name in ('tools/package_quality.py','tools/run_relaxed_full.py','tools/recover_relaxed_full.py','tools/test_relaxed_delivery.py')}))
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
