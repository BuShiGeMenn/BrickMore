"""Fast existing Q2 additions-only cover, then unchanged Q4 mixed fallback/audits."""
import json
from pathlib import Path
import shutil
import time

import package_quality as p
e=p.e;q=e.q
VERSION='balanced_q2_seed_q4_mixed_v1'


def worker(task):
    job,dataset,out,options=task
    if job.get('cachedQ4Path') or job.get('priorQ3Status')=='success' or job.get('baselineStatus')=='success':
        return e.worker(task)
    source_path=Path(dataset)/job['modelPath']/'model.json'
    folder=Path(out)/'models'/job['category']/job['modelId']
    if folder.exists():return e.verify(folder,source_path)
    source=json.loads(source_path.read_text(encoding='utf-8-sig'));model,coords=q.a.dataset_model(source)
    if source['modelId']!=job['modelId'] or q.a.exact_hash(coords)!=job['exactOccupancyHash']:
        raise ValueError('balanced seed source identity/geometry mismatch')
    started=time.monotonic()
    seed=q.optimize(model,max_ratio=options['ratio'],max_seconds=options['additionsSeconds'],
                    max_nodes=6000,repair_variants=1)
    seed_passed=q.independent_audit(seed['bricks'],seed['targetCells'])['passed']
    gate=dict(sourceFileSha256=q.a.file_sha(source_path),kind='balanced_q2_additions_only_search',
              geometryPassed=seed_passed,boundedFailureNotImpossibility=True,bricks=seed['bricks'],
              target=e.old.target_value(source,seed['targetCells'],q.repair_audit(model.cells,seed['targetCells'],options['ratio'])),
              searchAttempts=seed['searchAttempts'],sourceCodeSha256=e.hashes())
    attempts=[dict(stage='fast_q2_additions_only',algorithmVersion=q.VERSION,
                   elapsedSeconds=seed['elapsedSeconds'],completeSearch=False,details=seed['searchAttempts'])]
    if seed_passed:
        raw,cells=seed['bricks'],seed['targetCells'];outcome='balanced_fast_q2_additions'
    else:
        def physics_accept(raw,target):
            return e.g.screen(raw,target,min(2.,options['physicsSeconds']))['layerPrefixGravityPassed']
        raw,cells,stats=e.j.solve(model.cells,options['ratio'],options['seconds'],options['candidateLimit'],
                                options['cutRounds'],physics_accept=physics_accept,
                                additions_only_failure={k:gate[k] for k in ('kind','geometryPassed','sourceFileSha256')})
        attempts.append(dict(stage='mixed_fallback',**stats));outcome='balanced_mixed_fallback'
    repair=e.m.repair_audit(model.cells,cells,options['ratio'])
    if not repair['passed']:raise ValueError('balanced seed repair bound failed')
    passed=q.independent_audit(raw,cells)['passed'];status='success' if passed else 'draft'
    target=e.old.target_value(source,cells,repair)
    if target['derivedGeometry']:target['modelId']=target['modelId'].replace('_q2_','_q4_')
    physics=e.g.screen(raw,cells,options['physicsSeconds'])
    folder.mkdir(parents=True);shutil.copyfile(source_path,folder/'source.model.json')
    q.a.dump(folder/'target.model.json',target)
    q.a.dump(folder/'assembly.json',dict(algorithmVersion=e.VERSION,modelId=target['modelId'],sourceModelId=source['modelId'],
             status=status,bricks=raw,policy=q.POLICY,sourceToInternal='[x,y,z] -> [x,z,y]',ldrUnitScales=[20,20,24],
             fullPhysics=False,staticVerified=None))
    geometry=[{k:b[k] for k in ('h','w','x','y','z')} for b in raw];suffix='' if passed else '.draft'
    (folder/f'model{suffix}.txt').write_text(''.join(q.a.Placement(**b).to_txt() for b in geometry),encoding='utf8')
    (folder/f'model{suffix}.ldr').write_text(q.a.to_ldr({'status':status,'bricks':geometry},cells),encoding='utf8')
    validation=q.a.exported_audit(folder,target,q.POLICY)
    if validation['passed']!=passed:raise ValueError('balanced exported audit disagrees')
    q.a.dump(folder/'physics.json',physics);q.a.dump(folder/'validation.json',validation)
    q.a.dump(folder/'additions_only_evidence.json',gate)
    report=dict(algorithmVersion=e.VERSION,generationDriverVersion=VERSION,
                generationDriverSha256=q.a.file_sha(__file__),modelId=source['modelId'],targetModelId=target['modelId'],
                category=job['category'],status=status,outcome=outcome if passed else 'bounded_balanced_search_not_passed',
                options=options,baselineStatus=job.get('baselineStatus'),repairAudit=repair,
                addedInternalXYZ=[list(c) for c in sorted(set(cells)-set(model.cells))],
                removedInternalXYZ=[list(c) for c in sorted(set(model.cells)-set(cells))],
                additionsOnlyGate=gate,geometryValidation=validation,physics=e.physics_summary(physics),
                qualityScreenedSuccess=passed and physics['layerPrefixGravityPassed'],searchAttempts=attempts,
                elapsedSeconds=time.monotonic()-started,sourceFileSha256=q.a.file_sha(source_path),sourceCodeSha256=e.hashes(),
                originalModelBytesPreserved=True,promptBindingStatus='original_only_not_revalidated' if cells!=model.cells else 'original_geometry_preserved',
                fullPhysics=False,staticVerified=None,semanticVerified=False,
                outputFileSha256={path.name:q.a.file_sha(path) for path in sorted(folder.iterdir())})
    q.a.dump(folder/'report.json',report)
    return e.verify(folder,source_path)
