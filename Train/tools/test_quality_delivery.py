"""Actual Q4 portable archives, safe recovery and publication guard regressions."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile

import package_quality as p
import run_quality_full as runner
import download_quality as download
e=p.e;q=e.q


class DeliveryTests(unittest.TestCase):
    def fixture(self,root,floating=True):
        cells={(x,y,z):0 for x in range(2) for y in range(8) for z in range(6)}
        if floating:cells[(7,7,7)]=0x123456
        value={'modelId':'delivery_fixture','canonicalGeometryHash':'canonical','actualVoxelCount':len(cells),
               'voxels':[dict(x=x,y=z,z=y,color=[(c>>16)&255,(c>>8)&255,c&255]) for (x,y,z),c in sorted(cells.items())]}
        dataset=root/'dataset';source=dataset/'models'/'fixture'/'delivery_fixture';source.mkdir(parents=True)
        q.a.dump(source/'model.json',value)
        job=dict(modelId=value['modelId'],modelPath='models/fixture/delivery_fixture',category='fixture',modelSeed=1,
                 exactOccupancyHash=q.a.exact_hash({(x,z,y):c for (x,y,z),c in cells.items()}),
                 canonicalGeometryHash='canonical',datasetPath=str(dataset),shardId='A',baselineStatus='search_failed')
        prompts=[dict(modelId=job['modelId'],recordId='fixture_l'+str(n),promptLevel=n,
                      targetOccupancyHash=job['exactOccupancyHash'],targetCanonicalGeometryHash='canonical') for n in range(1,6)]
        q.a.dump(source/'prompts.json',prompts)
        job.update(originalModelFileSha256=q.a.file_sha(source/'model.json'),originalPromptFileSha256=q.a.file_sha(source/'prompts.json'))
        baseline=root/'baseline';q.a.dump(baseline/'report.json',{'status':'search_failed'})
        job.update(baselinePath=str(baseline),baselineReportSha256=q.a.file_sha(baseline/'report.json'))
        options=dict(ratio=.02,seconds=5.,additionsSeconds=2.,physicsSeconds=3.,candidateLimit=40000,cutRounds=8)
        plan=dict(options=options,algorithmSourceCodeSha256=e.hashes())
        out=root/'run';out.mkdir();runner.initialize_worker(plan,str(out),'sealed-plan-test')
        row=runner.compute(job)
        return dataset,job,out,row

    def package(self,root,floating=True):
        dataset,job,out,row=self.fixture(root,floating)
        proof=p.make_package(out,'A',1,[job],'test-q4-tag','sealed-plan-test')
        archive=out/'delivery'/proof['asset']['sourceRelativePath']
        with zipfile.ZipFile(archive) as z:
            prefix=proof['rows'][0]['resultPath']+'/'
            files={Path(name).name:z.read(name) for name in z.namelist() if name.startswith(prefix)}
        return dataset,job,out,row,proof,files

    def test_zip_actual_source_derived_deletions_physics_and_prompts(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset,job,out,row,proof,files=self.package(Path(tmp))
            checked,records=p.audit_payload(files,job)
            self.assertEqual(checked['status'],'success');self.assertEqual(checked['repairAudit']['removedVoxelCount'],1)
            self.assertTrue(checked['qualityScreenedSuccess']);self.assertFalse(checked['additionsOnlyGate']['geometryPassed'])
            self.assertEqual(len(records),5);self.assertFalse(p.legacy.private_paths(checked))
            self.assertEqual(files['source.model.json'],(dataset/job['modelPath']/'model.json').read_bytes())
            self.assertEqual(files['source.prompts.json'],(dataset/job['modelPath']/'prompts.json').read_bytes())
            self.assertEqual(p.make_package(out,'A',1,[job],'test-q4-tag','sealed-plan-test'),proof)

    def test_recomputed_sha_cannot_hide_force_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            *_,files=self.package(Path(tmp),False)
            physics=json.loads(files['physics.json']);physics['equilibriumWitness']['signedForcesUnitWeights'][0]+=1
            files['physics.json']=p.legacy.encode(physics)
            report=json.loads(files['report.json']);report['physics']=e.physics_summary(physics)
            report['outputFileSha256']['physics.json']=q.a.sha(files['physics.json'])
            files['report.json']=p.legacy.encode(report)
            with self.assertRaises(ValueError):p.audit_payload(files)

    def test_original_prompt_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            *_,files=self.package(Path(tmp))
            prompts=json.loads(files['source.prompts.json']);prompts[0]['targetOccupancyHash']='wrong'
            files['source.prompts.json']=p.legacy.encode(prompts)
            report=json.loads(files['report.json']);report['outputFileSha256']['source.prompts.json']=q.a.sha(files['source.prompts.json'])
            files['report.json']=p.legacy.encode(report)
            with self.assertRaises(ValueError):p.audit_payload(files)

    def test_incomplete_census_never_publishes(self):
        with patch.object(runner.subprocess,'run') as mutation:
            with self.assertRaises(ValueError):runner.publish(Path('.'),{},dict(processedModelCount=1,remainingModelCount=79999),dict(assetCount=1))
            mutation.assert_not_called()

    def test_changed_remote_never_publishes_or_writes_metadata(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(runner.subprocess,'check_output',return_value='https://github.com/unrequested/repository.git'),patch.object(runner.subprocess,'run') as mutation:
            root=Path(tmp)
            summary=dict(processedModelCount=80000,remainingModelCount=0,allPublicZipCrcShaGeometryRepairGateAndPhysicsReadbackPassed=True)
            with self.assertRaises(ValueError):runner.publish(root,{'workspace':str(root)},summary,{'assetCount':81})
            mutation.assert_not_called();self.assertFalse((root/'datasets').exists())

    def test_package_mutation_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,job,out,_,proof,_=self.package(Path(tmp))
            archive=out/'delivery'/proof['asset']['sourceRelativePath'];original=archive.read_bytes()
            archive.write_bytes(original+b'changed')
            with self.assertRaises(ValueError):p.make_package(out,'A',1,[job],'test-q4-tag','sealed-plan-test')
            self.assertEqual(archive.read_bytes(),original+b'changed')

    def test_interrupted_stage_is_recoverable_not_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);_,job,out,_=self.fixture(root)
            previous=out/'models'/'fixture'/job['modelId'];saved=root/'retained'
            previous.rename(saved)
            stage=out/'staging'/job['modelId'];stage.mkdir(parents=True,exist_ok=True)
            (stage/'interrupted.txt').write_text('recover me',encoding='utf8')
            row=runner.compute(job)
            self.assertEqual(row['status'],'success')
            matches=list((out/'interrupted_staging').glob('*/interrupted.txt'))
            self.assertEqual(len(matches),1);self.assertEqual(matches[0].read_text(),'recover me')

    def test_existing_checkpoint_source_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset,job,out,row=self.fixture(Path(tmp))
            self.assertEqual(runner.compute(job),row)
            source=dataset/job['modelPath']/'model.json';value=json.loads(source.read_bytes());value['changed']=True;q.a.dump(source,value)
            with self.assertRaises(ValueError):runner.compute(job)

    def test_archive_rename_crash_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,job,out,_,proof,_=self.package(Path(tmp))
            archive=out/'delivery'/proof['asset']['sourceRelativePath'];partial=archive.with_suffix('.zip.part');archive.rename(partial)
            self.assertEqual(p.make_package(out,'A',1,[job],'test-q4-tag','sealed-plan-test'),proof)
            self.assertTrue(archive.exists());self.assertFalse(partial.exists())

    def test_public_traversal_and_private_metadata_rejected(self):
        for name in ('../escape','C:/escape','/escape','AI_A/../../escape','..\\escape'):
            with self.assertRaises(ValueError):download.inside(Path('.').resolve(),name)
        with tempfile.TemporaryDirectory() as tmp:
            *_,files=self.package(Path(tmp))
            report=json.loads(files['report.json']);report['secretPath']='C:/Users/private';files['report.json']=p.legacy.encode(report)
            with self.assertRaises(ValueError):p.audit_payload(files)

    def test_double_execution_lock_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            handle=runner.lock_run(Path(tmp))
            try:
                with self.assertRaises((RuntimeError,BlockingIOError)):runner.lock_run(Path(tmp))
            finally:handle.close()


def main():
    started=time.monotonic();loader=unittest.TestLoader();suite=unittest.TestSuite()
    for folder,pattern in ((p.ROOT/'algorithms'/'voxel_assembly_q4','test_q4.py'),
                           (p.ROOT/'algorithms'/'voxel_assembly_q3','test_q3.py'),
                           (p.ROOT/'algorithms'/'voxel_assembly_q2','test_quality.py'),
                           (p.ROOT/'algorithms'/'voxel_assembly_relaxed','test_relaxed.py'),
                           (q.LEGACY,'test_*.py'),(p.ROOT/'tools','test_*.py')):
        sys.path.insert(0,str(folder));suite.addTests(loader.discover(str(folder),pattern=pattern,top_level_dir=str(folder)))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    runtime={p_.relative_to(p.ROOT).as_posix():q.a.file_sha(p_) for p_ in (Path(__file__),p.ROOT/'tools'/'package_quality.py',p.ROOT/'tools'/'run_quality_full.py',p.ROOT/'tools'/'download_quality.py')}
    p.atomic_json(p.ROOT/'datasets'/'q4_assembly_80000'/'delivery_tests.json',
                  {'passed':result.wasSuccessful(),'testCount':result.testsRun,'failures':len(result.failures),
                   'errors':len(result.errors),'algorithmSourceCodeSha256':e.hashes(),
                   'workflowSourceCodeSha256':runtime,'elapsedSeconds':time.monotonic()-started})
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
