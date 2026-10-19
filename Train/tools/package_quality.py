"""Seal Q4 source/derived outcomes, including auditable drafts and physics witnesses."""
from collections import Counter
from collections import deque
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'algorithms'/'voxel_assembly_q4'))
import q4_experiment as e
import package_assembly as legacy
q=e.q
VERSION='portable_quality_archive_v2_parallel_readback'


def auditor(name):
    if name=='q4_experiment':return e
    if name=='relaxed_pipeline':
        sys.path.insert(0,str(ROOT/'algorithms/voxel_assembly_relaxed'))
        import relaxed_pipeline
        return relaxed_pipeline
    raise ValueError('unsupported portable auditor')


def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_bytes(legacy.encode(value));temporary.replace(path)


def audit_payload(files,job=None,auditor_name=None):
    """Use unchanged Q4 + legacy actual-file readers on actual ZIP member bytes."""
    if any(Path(name).name!=name or ':' in name or '\\' in name for name in files):raise ValueError('unsafe payload filename')
    report=json.loads(files['report.json'])
    if auditor_name is None:
        auditor_name='relaxed_pipeline' if report['algorithmVersion']=='quality_relaxed_modular_grounded_delivery_v1' else 'q4_experiment'
    if legacy.private_paths(report):raise ValueError('private path in public Q4 report')
    if any(q.a.sha(files[name])!=digest for name,digest in report['outputFileSha256'].items()):raise ValueError('public payload SHA mismatch')
    source=json.loads(files['source.model.json'])
    if job is None:
        job={'modelId':source['modelId'],'exactOccupancyHash':report['sourceExactOccupancyHash'],
             'canonicalGeometryHash':report['sourceCanonicalGeometryHash']}
    if source['modelId']!=job['modelId']:raise ValueError('public source identity changed')
    original,coords=q.a.dataset_model(source)
    if q.a.exact_hash(coords)!=job['exactOccupancyHash'] or source.get('canonicalGeometryHash')!=job['canonicalGeometryHash']:raise ValueError('public source geometry binding changed')
    records=legacy.check_prompts(files['source.prompts.json'],job)
    with tempfile.TemporaryDirectory(prefix='brickmore-q4-readback-') as temporary:
        folder=Path(temporary)
        for name,data in files.items():(folder/name).write_bytes(data)
        checked=auditor(auditor_name).verify(folder)
    if checked['promptBindingStatus'] not in ('original_only_not_revalidated','original_geometry_preserved'):raise ValueError('prompts rebound to unaudited derived model')
    return checked,records


def bounded_map(pool,fn,items,window=6):
    if pool is None:
        yield from map(fn,items);return
    iterator=iter(items);pending=deque()
    for _ in range(window):
        try:pending.append(pool.submit(fn,next(iterator)))
        except StopIteration:break
    while pending:
        future=pending.popleft();result=future.result()
        try:pending.append(pool.submit(fn,next(iterator)))
        except StopIteration:pass
        yield result


def prepare_payload(task):
    run,job,shard,name,plan_sha,auditor_name=task;run=Path(run)
    folder=run/'models'/job['category']/job['modelId'];source_folder=Path(job['datasetPath'])/job['modelPath']
    report=auditor(auditor_name).verify(folder,source_folder/'model.json')
    files={n:(folder/n).read_bytes() for n in report['outputFileSha256']}
    source=(source_folder/'model.json').read_bytes();prompts=(source_folder/'prompts.json').read_bytes()
    if q.a.sha(source)!=report['sourceFileSha256'] or source!=files['source.model.json']:raise ValueError('original bytes changed')
    if q.a.sha(source)!=job['originalModelFileSha256'] or q.a.sha(prompts)!=job['originalPromptFileSha256']:raise ValueError('publication source differs from original ZIP bytes')
    record_ids=legacy.check_prompts(prompts,job)
    files['source.prompts.json']=prompts;files['workflow.json']=(folder/'workflow.json').read_bytes()
    workflow=json.loads(files['workflow.json'])
    if workflow['planSha256']!=plan_sha or workflow['reportSha256']!=q.a.file_sha(folder/'report.json') or workflow['actualOptions']!=report['options']:
        raise ValueError('package workflow checkpoint differs')
    public={**report,'sourceExactOccupancyHash':job['exactOccupancyHash'],
            'sourceCanonicalGeometryHash':job['canonicalGeometryHash'],
            'sourceModelPath':'source.model.json','sourcePairedPromptsPath':'source.prompts.json',
            'sourcePromptFileSha256':q.a.sha(prompts),'originalRunReportSha256':q.a.file_sha(folder/'report.json'),
            'runPlanSha256':plan_sha,'outputFileSha256':{n:q.a.sha(data) for n,data in files.items()}}
    if legacy.private_paths(public):raise ValueError('private path in public Q4 report')
    files['report.json']=legacy.encode(public)
    prefix=f'AI_{shard}/models/{job["category"]}/{job["modelId"]}';suffix='' if report['status']=='success' else '.draft'
    row={'modelId':job['modelId'],'targetModelId':report['targetModelId'],'shardId':shard,'category':job['category'],
         'status':report['status'],'geometryPassed':report['status']=='success',
         'qualityScreenedSuccess':report['qualityScreenedSuccess'],'physicsStatus':report['physics']['status'],
         'finalGravityEquilibriumPassed':report['physics']['gravityEquilibriumPassed'],
         'addedVoxelCount':report['repairAudit']['addedVoxelCount'],'removedVoxelCount':report['repairAudit']['removedVoxelCount'],
         'recoloredOriginalVoxelCount':report['repairAudit']['recoloredOriginalVoxelCount'],
         'changeRatio':report['repairAudit']['changeRatio'],
         'sourceExactOccupancyHash':job['exactOccupancyHash'],'sourceCanonicalGeometryHash':job['canonicalGeometryHash'],
         'targetExactOccupancyHash':report['repairAudit']['targetExactOccupancyHash'],
         'sourceFileSha256':report['sourceFileSha256'],'sourcePromptFileSha256':q.a.sha(prompts),
         'sourcePromptRecordIds':record_ids,'promptRecordCount':5,'assetName':name,'resultPath':prefix,
         'sourceModelJsonPath':prefix+'/source.model.json','sourcePairedPromptsPath':prefix+'/source.prompts.json',
         'targetModelJsonPath':prefix+'/target.model.json','assemblyJsonPath':prefix+'/assembly.json',
         'modelTxtPath':prefix+f'/model{suffix}.txt','modelLdrPath':prefix+f'/model{suffix}.ldr',
         'reportPath':prefix+'/report.json','reportFileSha256':q.a.sha(files['report.json']),
         'actualSearchOptions':report['options'],'resultOrigin':workflow['origin'],
         'generationPlanSha256':workflow.get('generationPlanSha256',plan_sha),
         'sourceCodeGenerationSha256':q.a.sha(json.dumps(report['sourceCodeSha256'],sort_keys=True).encode()),
         'geometryTier':report.get('geometryTier','strict_q4_geometry'),
         'staticVerified':None,'fullPhysics':False,'promptBindingStatus':report['promptBindingStatus']}
    return files,row


def audit_payload_summary(task):
    files,job,auditor_name=task;checked,records=audit_payload(files,job,auditor_name)
    return checked['status'],checked['qualityScreenedSuccess'],records


def make_package(run,shard,number,jobs,tag,plan_sha,audit_pool=None,auditor_name='q4_experiment'):
    auditor(auditor_name)
    lane='relaxed' if auditor_name=='relaxed_pipeline' else 'q4'
    run=Path(run);out=run/'delivery';name=f'AI_{shard}_{lane}_assembly_{number:02d}_1000.zip'
    target=out/'packages'/name;partial=target.with_suffix('.zip.part')
    checkpoint=out/'checkpoints'/shard/f'{number:02d}.json'
    selection=[{'modelId':j['modelId'],'reportSha256':q.a.file_sha(run/'models'/j['category']/j['modelId']/'report.json')} for j in jobs]
    selection_sha=q.a.sha(json.dumps(selection,sort_keys=True).encode())
    if checkpoint.exists():
        proof=json.loads(checkpoint.read_bytes())
        if proof['selectionSha256']!=selection_sha or proof['packagerSha256']!=q.a.file_sha(__file__) or proof['runPlanSha256']!=plan_sha or proof.get('auditorName','q4_experiment')!=auditor_name:raise ValueError('sealed Q4 package configuration changed')
        if not target.exists() and partial.exists() and q.a.file_sha(partial)==proof['asset']['sha256']:
            partial.replace(target)
        if not target.exists() or target.stat().st_size!=proof['asset']['bytes'] or q.a.file_sha(target)!=proof['asset']['sha256']:raise ValueError('sealed Q4 package changed')
        return proof
    if target.exists() or partial.exists():raise ValueError('unsealed Q4 archive exists; inspect before retry')
    target.parent.mkdir(parents=True,exist_ok=True);rows=[];expected=set()
    tasks=((str(run),job,shard,name,plan_sha,auditor_name) for job in jobs)
    with zipfile.ZipFile(partial,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
        for files,row in bounded_map(audit_pool,prepare_payload,tasks):
            prefix=row['resultPath']
            for filename,data in files.items():
                path=prefix+'/'+filename
                if path in expected:raise ValueError('duplicate public Q4 member')
                expected.add(path);archive.writestr(path,data)
            rows.append(row)
    with zipfile.ZipFile(partial) as archive:
        if len(archive.namelist())!=len(expected) or set(archive.namelist())!=expected or archive.testzip() is not None:raise ValueError('public Q4 inventory/CRC mismatch')
        def payloads():
            for job,row in zip(jobs,rows):
                report_data=archive.read(row['reportPath'])
                if q.a.sha(report_data)!=row['reportFileSha256']:raise ValueError('public report digest mismatch')
                public=json.loads(report_data);prefix=row['resultPath']+'/'
                files={n:archive.read(prefix+n) for n in public['outputFileSha256']};files['report.json']=report_data
                yield files,job,auditor_name
        for row,(checked_status,quality_pass,records) in zip(rows,bounded_map(audit_pool,audit_payload_summary,payloads())):
            if checked_status!=row['status'] or quality_pass!=row['qualityScreenedSuccess'] or records!=row['sourcePromptRecordIds']:raise ValueError('ZIP Q4 independent readback disagreement')
    asset={'name':name,'bytes':partial.stat().st_size,'sha256':q.a.file_sha(partial),
           'kind':'assembly_package','shardId':shard,'modelCount':len(rows),'promptRecordCount':5*len(rows),
           'sourceRelativePath':'packages/'+name,'url':f'https://github.com/BuShiGeMenn/BrickMore/releases/download/{tag}/{name}'}
    if asset['bytes']>=2_000_000_000:raise ValueError('GitHub asset too large; use smaller sealed batches')
    proof={'runPlanSha256':plan_sha,'selectionSha256':selection_sha,'packagerSha256':q.a.file_sha(__file__),'auditorName':auditor_name,
           'allPublicZipCrcShaGeometryRepairGateAndPhysicsReadbackPassed':True,'modelCount':len(rows),
           'promptRecordCount':5*len(rows),'rows':rows,'asset':asset}
    # Proof first allows safe recovery if the process ends just before renaming.
    atomic_json(checkpoint,proof);partial.replace(target)
    return proof


def reuse_sealed_package(run,source_run,shard,number,jobs,tag,plan_sha,previous_plan_sha,
                        previous_packager_sha,previous_proof_sha,previous_algorithm_sources,audit_pool=None):
    """Copy unchanged ZIP bytes only after a fresh actual-member readback.

    The old plan/proof is a frozen explicit parent, not a wildcard exception to
    current-generation SHA checks. Old outputs and old checkpoints are untouched.
    """
    run=Path(run);source_run=Path(source_run)
    parent=source_run/'delivery/checkpoints'/shard/f'{number:02d}.json'
    if q.a.file_sha(parent)!=previous_proof_sha:raise ValueError('inherited proof changed')
    original=json.loads(parent.read_bytes());asset=original['asset']
    if original['runPlanSha256']!=previous_plan_sha or original['packagerSha256']!=previous_packager_sha or original.get('auditorName')!='relaxed_pipeline' or not original['allPublicZipCrcShaGeometryRepairGateAndPhysicsReadbackPassed']:
        raise ValueError('inherited package generation differs')
    name=f'AI_{shard}_relaxed_assembly_{number:02d}_1000.zip'
    if asset['name']!=name or asset['sourceRelativePath']!='packages/'+name or asset['url']!=f'https://github.com/BuShiGeMenn/BrickMore/releases/download/{tag}/{name}':raise ValueError('inherited package path/tag differs')
    source=source_run/'delivery/packages'/name;target=run/'delivery/packages'/name
    if source.stat().st_size!=asset['bytes'] or q.a.file_sha(source)!=asset['sha256']:raise ValueError('inherited ZIP changed')
    rows=original['rows']
    if original['modelCount']!=len(jobs) or [r['modelId'] for r in rows]!=[j['modelId'] for j in jobs]:raise ValueError('inherited model selection differs')
    selection=[dict(modelId=j['modelId'],reportSha256=q.a.file_sha(source_run/'models'/j['category']/j['modelId']/'report.json')) for j in jobs]
    if q.a.sha(json.dumps(selection,sort_keys=True).encode())!=original['selectionSha256']:raise ValueError('inherited private report binding differs')
    checkpoint=run/'delivery/checkpoints'/shard/f'{number:02d}.json'
    if checkpoint.exists():
        proof=json.loads(checkpoint.read_bytes())
        if proof['runPlanSha256']!=plan_sha or proof['packagerSha256']!=q.a.file_sha(__file__) or proof.get('inheritedPackageProofSha256')!=previous_proof_sha or proof['asset']!=asset:raise ValueError('inherited current checkpoint differs')
        partial=target.with_suffix('.zip.part')
        if not target.exists() and partial.exists() and q.a.file_sha(partial)==asset['sha256']:partial.replace(target)
        if target.stat().st_size!=asset['bytes'] or q.a.file_sha(target)!=asset['sha256']:raise ValueError('inherited copied ZIP changed')
        return proof
    if target.exists() or target.with_suffix('.zip.part').exists():raise ValueError('unsealed inherited copy requires inspection')
    with zipfile.ZipFile(source) as archive:
        names=archive.namelist();expected=set()
        if len(names)!=len(set(names)) or archive.testzip() is not None:raise ValueError('inherited CRC/inventory differs')
        def payloads():
            for job,row,selected in zip(jobs,rows,selection):
                report_data=archive.read(row['reportPath'])
                if q.a.sha(report_data)!=row['reportFileSha256']:raise ValueError('inherited public report digest differs')
                public=json.loads(report_data);prefix=row['resultPath']+'/'
                if public['sourceCodeSha256']!=previous_algorithm_sources or public['runPlanSha256']!=previous_plan_sha or public['originalRunReportSha256']!=selected['reportSha256']:raise ValueError('inherited report generation differs')
                files={n:archive.read(prefix+n) for n in public['outputFileSha256']};files['report.json']=report_data
                expected.update(prefix+n for n in files)
                if q.a.sha(files['source.model.json'])!=job['originalModelFileSha256'] or q.a.sha(files['source.prompts.json'])!=job['originalPromptFileSha256']:raise ValueError('inherited original model/prompt bytes differ')
                workflow=json.loads(files['workflow.json'])
                if workflow['planSha256']!=previous_plan_sha or workflow['reportSha256']!=selected['reportSha256'] or workflow['actualOptions']!=public['options']:raise ValueError('inherited workflow differs')
                yield files,job,'relaxed_pipeline'
        for row,(status,quality,records) in zip(rows,bounded_map(audit_pool,audit_payload_summary,payloads())):
            if (status,quality,records)!=(row['status'],row['qualityScreenedSuccess'],row['sourcePromptRecordIds']):raise ValueError('inherited actual readback differs')
        if set(names)!=expected:raise ValueError('inherited actual member inventory differs')
    generation_sha=q.a.sha(json.dumps(previous_algorithm_sources,sort_keys=True).encode())
    rows=[{**r,'generationPlanSha256':previous_plan_sha,'sourceCodeGenerationSha256':generation_sha} for r in rows]
    target.parent.mkdir(parents=True,exist_ok=True);partial=target.with_suffix('.zip.part');shutil.copyfile(source,partial)
    if partial.stat().st_size!=asset['bytes'] or q.a.file_sha(partial)!=asset['sha256']:raise ValueError('inherited byte-preserving copy differs')
    proof={**original,'rows':rows,'runPlanSha256':plan_sha,'packagerSha256':q.a.file_sha(__file__),
           'inheritedPackageProofSha256':previous_proof_sha,'inheritedRunPlanSha256':previous_plan_sha,
           'inheritedPackagerSha256':previous_packager_sha,'freshActualZipReadbackPassed':True}
    atomic_json(checkpoint,proof);partial.replace(target)
    return proof


def counts(rows):
    return {'processedModelCount':len(rows),'promptRecordCount':5*len(rows),
            'statusCounts':dict(Counter(r['status'] for r in rows)),
            'geometryPassed':sum(r['geometryPassed'] for r in rows),
            'gravityScreenedPassed':sum(r['qualityScreenedSuccess'] for r in rows),
            'finalGravityEquilibriumPassed':sum(r['finalGravityEquilibriumPassed'] for r in rows),
            'physicalStatusCounts':dict(Counter(r['physicsStatus'] for r in rows)),
            'maximumChangeRatio':max((r['changeRatio'] for r in rows),default=0),
            'addedVoxelCount':sum(r['addedVoxelCount'] for r in rows),
            'removedVoxelCount':sum(r['removedVoxelCount'] for r in rows),
            'recoloredOriginalVoxelCount':sum(r['recoloredOriginalVoxelCount'] for r in rows)}


def finalize(run,plan,plan_sha):
    run=Path(run);out=run/'delivery';meta=out/'metadata';rows=[];assets=[];shards={}
    for shard in ('A','B'):
        shard_rows=[]
        for number in range(1,41):
            proof=json.loads((out/'checkpoints'/shard/f'{number:02d}.json').read_bytes())
            if proof['runPlanSha256']!=plan_sha or proof['modelCount']!=1000 or not proof['allPublicZipCrcShaGeometryRepairGateAndPhysicsReadbackPassed']:raise ValueError('all 80 packages must be sealed before delivery')
            asset=proof['asset'];path=out/asset['sourceRelativePath']
            if path.stat().st_size!=asset['bytes'] or q.a.file_sha(path)!=asset['sha256']:raise ValueError('sealed package altered')
            shard_rows.extend(proof['rows']);assets.append(asset)
        if len(shard_rows)!=40000:raise ValueError('incomplete shard')
        shards[shard]=counts(shard_rows);rows.extend(shard_rows)
    if len(rows)!=80000 or len({r['modelId'] for r in rows})!=80000 or len({r['targetModelId'] for r in rows})!=80000 or len({record for r in rows for record in r['sourcePromptRecordIds']})!=400000:raise ValueError('80,000 original/target IDs and 400,000 prompt records must be unique')
    if any(r['changeRatio']>.02 or r['recoloredOriginalVoxelCount'] for r in rows):raise ValueError('repair quality exceeded')
    baseline={j['modelId'] for j in plan['jobs'] if j['baselineStatus']=='success'}
    success={r['modelId'] for r in rows if r['geometryPassed']}
    if baseline-success:raise ValueError('original published geometry success regressed')
    retained={r['modelId'] for r in plan.get('retainedPreviousOutcomes',[]) if r['status']=='success'}
    if retained-success:raise ValueError('previous completed Q4 geometry success regressed')
    summary={**counts(rows),'remainingModelCount':0,'releaseTag':plan['releaseTag'],'shards':shards,
             'geometryPassRate':len(success)/80000,'originalPublishedGeometryPassed':len(baseline),
             'geometryRegressionsFromOriginalRelease':0,'originalModelAndPromptBytesPreserved':True,
             'allPublicZipCrcShaGeometryRepairGateAndPhysicsReadbackPassed':True,
             'duplicateSourceExactHashCount':80000-len({r['sourceExactOccupancyHash'] for r in rows}),
             'duplicateDerivedTargetExactHashCount':80000-len({r['targetExactOccupancyHash'] for r in rows}),
             'full80000RerunCompleted':True,'staticVerified':None,'fullPhysics':False,
             'retainedPreviousModelCount':len(plan.get('retainedPreviousOutcomes',[])),
             'retainedPreviousGeometryPassed':len(retained),'retainedPreviousGeometryRegressions':0,
             'actualSearchOptionCounts':dict(Counter(json.dumps(r['actualSearchOptions'],sort_keys=True) for r in rows)),
             'semanticVerified':False,'physicsAssumptions':e.g.ASSUMPTIONS,'runPlanSha256':plan_sha,
             'algorithmVersion':plan.get('algorithmVersion',e.VERSION),'algorithmSourceCodeSha256':plan['algorithmSourceCodeSha256']}
    if plan.get('auditorName')=='relaxed_pipeline':
        summary.update(geometryTier='relaxed_modular_grounded_not_physical_certification',geometryPolicy=plan['geometryPolicy'],
                       geometryGoal=.60,geometryGoalAchieved=len(success)>=48000)
    if 'previousModularPlanSha256' in plan:
        summary.update(sourceCodeGenerationCounts=dict(Counter(r['sourceCodeGenerationSha256'] for r in rows)),
                       generationPlanCounts=dict(Counter(r['generationPlanSha256'] for r in rows)),
                       preservedSealedPackageCount=len(plan['inheritedPackages']),
                       preservedSealedModelCount=sum(v['modelCount'] for v in plan['inheritedPackages'].values()),
                       rejectedSolverCandidatePolicy='unchanged force/moment tolerance; rejected candidates retained as diagnostics, never physical pass')
    atomic_json(meta/'assembly_summary.json',summary)
    meta.mkdir(parents=True,exist_ok=True)
    (meta/'assembly_index.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows),encoding='utf8')
    provenance={k:plan[k] for k in ('releaseTag','algorithmSourceCodeSha256','runtimeSourceCodeSha256','options','sourceMetadataSha256','reusePolicy')}
    if 'schedulerPolicy' in plan:provenance['schedulerPolicy']=plan['schedulerPolicy']
    if 'previousPlanSha256' in plan:provenance['previousPlanSha256']=plan['previousPlanSha256']
    if 'previousCensusRuntimeSourceCodeSha256' in plan:provenance['previousCensusRuntimeSourceCodeSha256']=plan['previousCensusRuntimeSourceCodeSha256']
    for name in ('previousModularPlanSha256','previousModularRuntimeSourceCodeSha256','previousModularAlgorithmSourceCodeSha256','inheritedPackages','recoveryPolicy'):
        if name in plan:provenance[name]=plan[name]
    atomic_json(meta/'provenance.json',provenance)
    lines=['# '+('放宽几何档' if plan.get('auditorName')=='relaxed_pipeline' else 'Q4')+' 全量 A/B 80,000 模型装配结果','',
           f'几何通过 {len(success):,} / 80,000（{len(success)/80000:.4%}）；假设下最终及全部完成层筛查 {summary["gravityScreenedPassed"]:,} 个。','',
           '不是80,000个成功装配；失败文件明确为 .draft。新增优先，失败后少量删除，合计≤原体素数2%，原文件字节和保留体素原色不变。','',
           '几何/修复差异、仅新增失败门槛、JSON/TXT/LDR、物理力平衡见证已从实际 ZIP 独立回读，全部 CRC/SHA 通过。',
           '质量与接触参数未经实物标定，未知咬合力不算物理通过；staticVerified=null / fullPhysics=false。',
           'source.model.json 和 source.prompts.json 是未经改写的原数据；训练提示词只绑定原目标，不自动重绑定派生 target.model.json。',
           '原来源ID、派生目标ID与hash、修改点RGB与比例、物理状态、失败证据均保留。',
           '原始Release和旧装配Release不更新。完整清单在 assembly_index.jsonl，分片数据包在独立 AI_A/AI_B 目录。','',
           '| 分片 | 已处理 | 几何通过 | 全部完成层静力筛查 |','|---|---:|---:|---:|']
    for shard,part in shards.items():lines.append(f'| {shard} | 40,000 | {part["geometryPassed"]:,} | {part["gravityScreenedPassed"]:,} |')
    (meta/'ASSEMBLY_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    for name,digest in plan['runtimeSourceCodeSha256'].items():
        source=run/'source_snapshot'/name
        if q.a.file_sha(source)!=digest:raise ValueError('frozen runtime changed')
        target=meta/'algorithm_source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    expected_metadata={'assembly_summary.json','assembly_index.jsonl','provenance.json','ASSEMBLY_REPORT.md'}|{'algorithm_source/'+name for name in plan['runtimeSourceCodeSha256']}
    for name,digest in plan.get('previousCensusRuntimeSourceCodeSha256',{}).items():
        source=Path(plan['retainedPreviousRuntimeSnapshotPath'])/name
        if q.a.file_sha(source)!=digest:raise ValueError('previous census runtime changed')
        target=meta/'previous_census_source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        expected_metadata.add('previous_census_source/'+name)
    for name,digest in plan.get('previousModularRuntimeSourceCodeSha256',{}).items():
        source=Path(plan['retainedPreviousModularRuntimeSnapshotPath'])/name
        if q.a.file_sha(source)!=digest:raise ValueError('previous modular runtime changed')
        target=meta/'previous_modular_source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        expected_metadata.add('previous_modular_source/'+name)
    if {p.relative_to(meta).as_posix() for p in meta.rglob('*') if p.is_file()}!=expected_metadata:raise ValueError('unexpected metadata files; refusing publication')
    archive=out/'packages'/('relaxed_assembly_metadata.zip' if plan.get('auditorName')=='relaxed_pipeline' else 'q4_assembly_metadata.zip');partial=archive.with_suffix('.zip.part')
    if archive.exists():
        # Metadata is deterministic for the sealed plan; do not overwrite existing delivery.
        with zipfile.ZipFile(archive) as z:
            if len(z.namelist())!=len(expected_metadata) or set(z.namelist())!=expected_metadata:raise ValueError('existing metadata inventory differs')
            for path in sorted(meta.rglob('*')):
                if path.is_file() and z.read(path.relative_to(meta).as_posix())!=path.read_bytes():raise ValueError('existing metadata archive differs')
            if z.testzip() is not None:raise ValueError('metadata CRC mismatch')
    else:
        if partial.exists():raise ValueError('unsealed metadata archive needs inspection')
        with zipfile.ZipFile(partial,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for path in sorted(meta.rglob('*')):
                if path.is_file():z.write(path,path.relative_to(meta).as_posix())
        with zipfile.ZipFile(partial) as z:
            if z.testzip() is not None:raise ValueError('metadata CRC mismatch')
        partial.replace(archive)
    assets.append({'name':archive.name,'bytes':archive.stat().st_size,'sha256':q.a.file_sha(archive),'kind':'metadata',
                   'sourceRelativePath':'packages/'+archive.name,'url':f'https://github.com/BuShiGeMenn/BrickMore/releases/download/{plan["releaseTag"]}/{archive.name}'})
    relaxed=plan.get('auditorName')=='relaxed_pipeline'
    manifest={'repository':'BuShiGeMenn/BrickMore','releaseTag':plan['releaseTag'],
              'releaseName':('Grounded modular geometry' if relaxed else 'Q4 derived assembly')+': 80,000 original voxel models / 400,000 original bilingual records',
              'releaseBody':f'{"放宽几何档：允许多个真实stud接地组件，不认证安装顺序或承力" if relaxed else "Q4"}。全量处理A/B各40,000模型，几何通过{len(success):,}/80,000（{len(success)/80000:.4%}）；假设下全部完成层静力筛查{summary["gravityScreenedPassed"]:,}。\n新增优先，失败后允许少量删除，合计≤2%；原模型、原色和提示词保留。\n成功、失败草稿和未知咬合力明确标注，不是物理认证。所有实际ZIP已独立回读CRC/SHA、JSON/TXT/LDR、修改记录和力平衡见证。原始与旧装配Release不变。',
              'modelCount':80000,'promptRecordCount':400000,'assetCount':len(assets),
              'totalDownloadBytes':sum(a['bytes'] for a in assets),'assets':assets}
    atomic_json(out/'download_manifest.json',manifest)
    return summary,manifest
