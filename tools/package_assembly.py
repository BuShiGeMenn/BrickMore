"""Seal portable, independently re-read LEGO outcomes, including failure drafts.

Source runs are immutable. Public archives include original model/prompt bytes,
actual JSON/TXT/LDR outputs and sanitized reports, not just algorithm metadata.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'algorithms'/'voxel_assembly_b'))
import assembly_pipeline as a

VERSION = 'portable_assembly_archive_v1'
STATUSES = ('success','infeasible_under_selected_policy','search_failed')


def encode(value):
    return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf8')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def private_paths(value):
    if isinstance(value,dict):
        return any(private_paths(v) for v in value.values())
    if isinstance(value,list):
        return any(private_paths(v) for v in value)
    return isinstance(value,str) and bool(re.search(r'(?i)(?:(?:^|[^a-z0-9])[a-z]:[/\\]|/Users/|/home/)',value))


def payload_audit(files):
    """Reconstruct independently from the actual published ZIP member bytes."""
    value=json.loads(files['assembly.json'])
    source=json.loads(files['source.model.json'])
    suffix='' if value['status']=='success' else '.draft'
    raw=value['bricks']
    txt=[a.Placement.parse(line) for line in files[f'model{suffix}.txt'].decode('utf8').splitlines() if line.strip()]
    ldr=a.parse_ldr(files[f'model{suffix}.ldr'].decode('utf8'))
    keys=('h','w','x','y','z')
    model,_=a.dataset_model(source)
    result=a.independent_audit(raw,model.cells,value['policy'])
    result.update(txtReadbackMatches=[tuple(getattr(b,k) for k in keys) for b in txt]==[tuple(b[k] for k in keys) for b in raw],
                  ldrReadbackMatches=ldr==raw,sourceModelId=source['modelId'],
                  sourceCanonicalGeometryHash=source.get('canonicalGeometryHash'),
                  canonicalPreservedByExactCoordinateEquality=result['exactCoverage'],readbackPerformed=True)
    if not result['txtReadbackMatches'] or not result['ldrReadbackMatches']:
        result['passed']=False
        result['issues'].append('export_readback_mismatch')
    return result


def check_prompts(data,job):
    rows=json.loads(data)
    if not isinstance(rows,list) or len(rows)!=5 or {r['promptLevel'] for r in rows}!={1,2,3,4,5}:
        raise ValueError('not exactly five original prompt levels: '+job['modelId'])
    if len({r['recordId'] for r in rows})!=5:
        raise ValueError('duplicate original prompt record ID')
    for row in rows:
        if row['modelId']!=job['modelId'] or row['targetOccupancyHash']!=job['exactOccupancyHash'] or row['targetCanonicalGeometryHash']!=job['canonicalGeometryHash']:
            raise ValueError('source prompt target association mismatch: '+job['modelId'])
    return [row['recordId'] for row in rows]


def selected_jobs(base,refinement):
    config=json.loads((base/'config.json').read_bytes())
    first=json.loads((base/'summary.json').read_bytes())
    verified=json.loads((base/'readback_verification.json').read_bytes())
    extra=json.loads((refinement/'summary.json').read_bytes())
    extra_verified=json.loads((refinement/'readback_verification.json').read_bytes())
    jobs=json.loads((base/'selection.json').read_bytes())
    if first['remainingModelCount'] or first['processedModelCount']!=len(jobs) or len(jobs)!=40000:
        raise ValueError('initial assembly must finish all 40,000 models')
    if not verified['allDeliveredOutputsReadbackPassed'] or sum(verified['counts'].values())!=len(jobs) or verified['counts'].get('verified_success',0)!=first['statusCounts'].get('success',0):
        raise ValueError('initial output readback incomplete')
    if extra['attemptedModelCount']!=first['statusCounts'].get('search_failed',0) or extra_verified['readbackVerifiedModelCount']!=extra['attemptedModelCount'] or not extra_verified['allDeliveredOutputsReadbackPassed']:
        raise ValueError('not all bounded search failures have been refined and re-read')
    if extra_verified['counts'].get('verified_success',0)!=extra['statusCounts'].get('success',0):
        raise ValueError('refinement success/readback counts disagree')
    selection=[json.loads(line) for line in (refinement/'selected_assembly_index.jsonl').read_text(encoding='utf8').splitlines()]
    index={r['modelId']:r for r in selection}
    if len(index)!=len(jobs) or len(index)!=len(selection) or set(index)!={j['modelId'] for j in jobs}:
        raise ValueError('selected index must contain exactly one result per input')
    result=[]
    dataset=Path(config['datasetPath'])
    for job in jobs:
        row=index[job['modelId']]
        folder=Path(row['resultPath']).resolve()
        if not (folder.is_relative_to(base.resolve()) or folder.is_relative_to(refinement.resolve())):
            raise ValueError('selected result outside declared runs')
        if digest(folder/'report.json')!=row['reportFileSha256'] or row['status'] not in STATUSES:
            raise ValueError('selected result changed or has invalid status')
        result.append({'job':job,'selection':row,'folder':str(folder),
                       'sourceFolder':str(dataset/job['modelPath'])})
    provenance={'baseAlgorithmVersion':config['algorithmVersion'],
                'baseRunnerSha256':config['sourceCodeSha256'],
                'baseSelectionSha256':config['selectionSha256'],
                'toolkitSourceSha256':config['toolkitSourceSha256'],
                'refinementConfig':{k:v for k,v in json.loads((refinement/'config.json').read_bytes()).items()
                                    if k not in ('baseRun','datasetPath')},
                'baseSummary':first,'baseReadback':verified,'refinementSummary':extra,
                'refinementReadback':extra_verified,'policy':config['policy'],
                'sourceManifestSha256':digest(dataset/'manifest.json'),
                'sourceAllPromptsSha256':digest(dataset/'all_prompts.jsonl')}
    if private_paths(provenance):raise ValueError('private path in public provenance')
    return result,provenance


def build_package(task):
    shard,number,items,out,tag=task
    out=Path(out)
    name=f'AI_{shard}_assembly_{number:02d}_1000.zip'
    target=out/'packages'/name
    proof_path=out/'checkpoints'/('AI_'+shard)/f'{number:02d}.json'
    plan=[{'modelId':i['job']['modelId'],'reportSha256':i['selection']['reportFileSha256']} for i in items]
    plan_sha=a.sha(json.dumps(plan,sort_keys=True).encode('utf8'))
    if proof_path.exists():
        old=json.loads(proof_path.read_bytes())
        if old['selectionPlanSha256']!=plan_sha or old['packagerSourceSha256']!=digest(__file__) or not target.exists() or digest(target)!=old['asset']['sha256']:
            raise ValueError('sealed package checkpoint changed; use a new output directory')
        return old
    target.parent.mkdir(parents=True,exist_ok=True)
    partial=target.with_suffix('.zip.part')
    if partial.exists() or target.exists():
        raise ValueError('unsealed archive already exists; inspect it and use a new output directory')
    rows=[]
    expected_names=set()
    with zipfile.ZipFile(partial,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for item in items:
            job=item['job'];chosen=item['selection'];folder=Path(item['folder']);source_folder=Path(item['sourceFolder'])
            report_bytes=(folder/'report.json').read_bytes()
            if a.sha(report_bytes)!=chosen['reportFileSha256']:raise ValueError('run report changed')
            report=json.loads(report_bytes)
            source=(source_folder/'model.json').read_bytes()
            prompts=(source_folder/'prompts.json').read_bytes()
            if a.sha(source)!=report['sourceFileSha256']:raise ValueError('original model changed')
            record_ids=check_prompts(prompts,job)
            files={name:(folder/name).read_bytes() for name in report['outputFileSha256']}
            if not all(a.sha(files[n])==h for n,h in report['outputFileSha256'].items()):raise ValueError('assembly output changed')
            files.update({'source.model.json':source,'source.prompts.json':prompts})
            if report['status']!=chosen['status'] or report['geometryPassed']!=(chosen['status']=='success'):
                raise ValueError('selection/status disagreement')
            if report['sourceExactOccupancyHash']!=job['exactOccupancyHash'] or report['sourceCanonicalGeometryHash']!=job['canonicalGeometryHash']:
                raise ValueError('assembly target hash disagreement')
            if json.loads(source)['modelId']!=job['modelId']:raise ValueError('source model ID mismatch')
            prefix=f'AI_{shard}/models/{job["category"]}/{job["modelId"]}'
            public={**report,'sourceModelPath':'source.model.json','sourcePairedPromptsPath':'source.prompts.json',
                    'sourcePromptFileSha256':a.sha(prompts),'originalRunReportSha256':chosen['reportFileSha256'],
                    'outputFileSha256':{n:a.sha(data) for n,data in files.items()}}
            if private_paths(public):raise ValueError('private path in public report')
            files['report.json']=encode(public)
            for filename,data in files.items():
                path=prefix+'/'+filename
                if path in expected_names:raise ValueError('duplicate archive entry')
                expected_names.add(path);archive.writestr(path,data)
            suffix='' if report['geometryPassed'] else '.draft'
            rows.append({'modelId':job['modelId'],'category':job['category'],'shardId':shard,
                         'status':report['status'],'geometryPassed':report['geometryPassed'],
                         'sourceExactOccupancyHash':job['exactOccupancyHash'],
                         'sourceCanonicalGeometryHash':job['canonicalGeometryHash'],
                         'sourceFileSha256':report['sourceFileSha256'],
                         'sourcePromptFileSha256':a.sha(prompts),'sourcePromptRecordIds':record_ids,
                         'promptRecordCount':5,'assetName':name,'resultPath':prefix,
                         'sourceModelJsonPath':prefix+'/source.model.json',
                         'sourcePairedPromptsPath':prefix+'/source.prompts.json',
                         'assemblyJsonPath':prefix+'/assembly.json',
                         'modelTxtPath':prefix+f'/model{suffix}.txt',
                         'modelLdrPath':prefix+f'/model{suffix}.ldr',
                         'validationPath':prefix+'/validation.json','reportPath':prefix+'/report.json',
                         'reportFileSha256':a.sha(files['report.json']),
                         'brickCount':report['validation']['brickCount'],
                         'staticVerified':None,'fullPhysics':False})
    # Re-open the actual ZIP, check every CRC/SHA and reconstruct every outcome.
    with zipfile.ZipFile(partial) as archive:
        if len(archive.namelist())!=len(expected_names) or set(archive.namelist())!=expected_names or archive.testzip() is not None:
            raise ValueError('archive inventory or CRC mismatch')
        for row in rows:
            prefix=row['resultPath']+'/'
            report_data=archive.read(row['reportPath'])
            if a.sha(report_data)!=row['reportFileSha256']:raise ValueError('public report SHA mismatch')
            report=json.loads(report_data)
            files={n:archive.read(prefix+n) for n in report['outputFileSha256']}
            if not all(a.sha(files[n])==h for n,h in report['outputFileSha256'].items()):raise ValueError('public artifact SHA mismatch')
            result=payload_audit(files)
            if result!=json.loads(files['validation.json']) or result!=report['validation'] or result['passed']!=row['geometryPassed']:
                raise ValueError('published JSON/TXT/LDR independent readback mismatch')
            if not result['txtReadbackMatches'] or not result['ldrReadbackMatches']:
                raise ValueError('failure draft exports disagree')
    partial.replace(target)
    proof={'selectionPlanSha256':plan_sha,'packagerSourceSha256':digest(__file__),
           'allPublicZipMemberCrcShaAndReadbackPassed':True,'modelCount':len(rows),
           'promptRecordCount':len(rows)*5,'rows':rows,
           'asset':{'name':name,'bytes':target.stat().st_size,'sha256':digest(target),
                    'kind':'assembly_package','shardId':shard,'modelCount':len(rows),
                    'promptRecordCount':len(rows)*5,'sourceRelativePath':'packages/'+name,
                    'url':f'https://github.com/BuShiGeMenn/BrickMore/releases/download/{tag}/{name}'}}
    a.dump(proof_path,proof)
    return proof


def export_shard(args):
    items,provenance=selected_jobs(args.base,args.refinement)
    tasks=[(args.shard,n+1,items[start:start+1000],str(args.out),args.tag)
           for n,start in enumerate(range(0,len(items),1000))]
    results=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for number,result in enumerate(pool.map(build_package,tasks),1):
            results.append(result)
            print('PUBLIC_PACKAGE_READBACK',args.shard,number,'/',len(tasks),result['asset']['name'],flush=True)
    rows=[row for result in results for row in result['rows']]
    if len(rows)!=40000 or len({r['modelId'] for r in rows})!=40000 or len({i for r in rows for i in r['sourcePromptRecordIds']})!=200000:
        raise ValueError('public shard index or prompt record IDs incomplete/duplicated')
    counts=Counter(r['status'] for r in rows)
    categories=defaultdict(Counter)
    for row in rows:categories[row['category']][row['status']]+=1
    summary={'shardId':args.shard,'processedModelCount':len(rows),'remainingModelCount':0,
             'promptRecordCount':len(rows)*5,'statusCounts':dict(counts),
             'successfulBrickCount':sum(r['brickCount'] for r in rows if r['geometryPassed']),
             'geometryAssemblyPassRate':counts['success']/len(rows),
             'categoryStatusCounts':{k:dict(v) for k,v in categories.items()},
             'additionalPassedModelCount':provenance['refinementSummary']['statusCounts'].get('success',0),
             'allPublicZipMemberCrcShaAndReadbackPassed':True,
             'allModelsAssemblyPassed':counts['success']==len(rows),'originalModelAndPromptBytesPreserved':True,
             'staticVerifiedModelCount':0,'physicsStatus':'not_attempted','fullPhysics':False}
    metadata=args.out/'metadata'/('AI_'+args.shard)
    a.dump(metadata/'summary.json',summary)
    a.dump(metadata/'provenance.json',provenance)
    a.dump(metadata/'package_verification.json',{'assets':[r['asset'] for r in results],
           'allPublicZipMemberCrcShaAndReadbackPassed':True,'modelCount':40000,'promptRecordCount':200000})
    (metadata/'assembly_index.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf8')
    print('PUBLIC_SHARD_SEALED',args.shard,json.dumps(summary,ensure_ascii=False),flush=True)


def finalize(args):
    rows=[];assets=[];summaries={}
    for shard in ('A','B'):
        folder=args.out/'metadata'/('AI_'+shard)
        summary=json.loads((folder/'summary.json').read_bytes())
        proof=json.loads((folder/'package_verification.json').read_bytes())
        if summary['processedModelCount']!=40000 or not summary['allPublicZipMemberCrcShaAndReadbackPassed'] or not proof['allPublicZipMemberCrcShaAndReadbackPassed']:
            raise ValueError('both shards must be completely sealed before publication')
        summaries[shard]=summary
        rows.extend(json.loads(line) for line in (folder/'assembly_index.jsonl').read_text(encoding='utf8').splitlines())
        for asset in proof['assets']:
            path=args.out/asset['sourceRelativePath']
            if digest(path)!=asset['sha256'] or path.stat().st_size!=asset['bytes']:raise ValueError('sealed public package changed')
            assets.append(asset)
    if len(rows)!=80000 or len({r['modelId'] for r in rows})!=80000 or len({i for r in rows for i in r['sourcePromptRecordIds']})!=400000:
        raise ValueError('80,000 model / 400,000 prompt public index must be unique')
    counts=Counter(r['status'] for r in rows)
    summary={'schemaVersion':1,'releaseTag':args.tag,'processedModelCount':80000,'remainingModelCount':0,
             'promptRecordCount':400000,'statusCounts':dict(counts),'shards':summaries,
             'allPublicZipMemberCrcShaAndReadbackPassed':True,'allModelsAssemblyPassed':counts['success']==80000,
             'staticVerifiedModelCount':0,'physicsStatus':'not_attempted','fullPhysics':False,
             'originalModelAndPromptBytesPreserved':True,'duplicateModelIdCount':0,'duplicatePromptRecordIdCount':0}
    a.dump(args.out/'metadata'/'assembly_summary.json',summary)
    (args.out/'metadata'/'assembly_index.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf8')
    text=['# A/B 80,000 模型 LEGO 拼接与独立回读交付','',
          '两批均实际处理，成功和失败各保留一份被选结果；模型数不是成功装配数。','',
          '| 分片 | 已处理 | 几何通过 | 所选规则必要条件失败 | 有界搜索未通过 |',
          '|---|---:|---:|---:|---:|']
    for shard,part in summaries.items():
        c=part['statusCounts'];text.append(f'| AI_{shard} | 40,000 | {c.get("success",0):,} | {c.get("infeasible_under_selected_policy",0):,} | {c.get("search_failed",0):,} |')
    text+=['','所有公开 ZIP 已检查 CRC、逐文件 SHA，并从 ZIP 内的真实 JSON/TXT/LDR 独立重建校验。',
           '每模型含原始 source.model.json、source.prompts.json、assembly.json、validation.json、report.json，以及成功 model.txt/model.ldr 或明确命名的失败 model.draft.txt/model.draft.ldr。',
           '原提示词中的 modelJsonPath/modelNpzPath 保持原始分片相对路径，不重写原记录；本包定位使用统一 assembly_index.jsonl 的 sourceModelJsonPath/sourcePairedPromptsPath。',
           '几何通过范围：精确占用、RGB、无碰撞、标准同色矩形单砖高砖库、逐层下支撑、单 stud 组件和接地。',
           '必要条件失败仅针对所选砖库和策略；有界搜索失败不证明无解。失败草稿不是可用装配。',
           '未验证静力、抗倾覆、接头受力、摩擦、插入路径或实物搭建，staticVerified=null / fullPhysics=false。',
           '源 Y-up [x,y,z] 转内部 Z-up [x,z,y]，不修改原占用/RGB。水平一格=1stud，竖直一格=1标准砖高，LDraw比例20/20/24，实物比例不同于等距体素预览。',
           '下载所有 AI_A_assembly_*.zip、AI_B_assembly_*.zip 及 assembly_metadata.zip，安全解压到同一目录。与原体素数据集建议分开目录。']
    (args.out/'metadata'/'ASSEMBLY_REPORT.md').write_text('\n'.join(text)+'\n',encoding='utf8')
    archive=args.out/'packages'/'assembly_metadata.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in sorted((args.out/'metadata').rglob('*')):
            if path.is_file():z.write(path,path.relative_to(args.out/'metadata').as_posix())
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('assembly metadata archive CRC mismatch')
    assets.append({'name':archive.name,'bytes':archive.stat().st_size,'sha256':digest(archive),
                   'kind':'metadata','sourceRelativePath':'packages/'+archive.name,
                   'url':f'https://github.com/BuShiGeMenn/BrickMore/releases/download/{args.tag}/{archive.name}'})
    manifest={'repository':'BuShiGeMenn/BrickMore','releaseTag':args.tag,
              'releaseName':'LEGO assembly outcomes: 80,000 models / 400,000 original bilingual records',
              'releaseBody':'AI_A 和 AI_B 各四万个模型均已拼接、独立回读和打包校验。成功与失败分开标注，详见仓库 datasets/assembly_80000/ASSEMBLY_REPORT.md。\n本发布包含实际 JSON/TXT/LDR、原模型和五级提示词、验证报告及失败证据，不只是算法源码。\n几何通过不等于物理稳定性通过。原 AI_A/AI_B 发布保持不变。',
              'modelCount':80000,'promptRecordCount':400000,'assetCount':len(assets),
              'totalDownloadBytes':sum(r['bytes'] for r in assets),'assets':assets}
    a.dump(args.out/'download_manifest.json',manifest)
    print('PUBLIC_ASSEMBLY_COMPLETE',json.dumps({'counts':dict(counts),'assets':len(assets),'bytes':manifest['totalDownloadBytes']},ensure_ascii=False),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('export','finalize'))
    p.add_argument('--shard',choices=('A','B'))
    p.add_argument('--base',type=Path);p.add_argument('--refinement',type=Path)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--tag',default='lego-assembly-ab-80000-20261011-v1')
    p.add_argument('--workers',type=int,default=8)
    args=p.parse_args()
    if args.workers<1:p.error('workers must be positive')
    if args.action=='export':
        if not args.shard or not args.base or not args.refinement:p.error('--shard, --base, --refinement required')
        export_shard(args)
    else:finalize(args)


if __name__=='__main__':
    main()
