"""Join immutable assembly runs by modelId; verify scope and seal metadata."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import zipfile

import assembly_pipeline as a


def main():
    root=a.HERE
    base=root/'runs'/'B_extended_v2'
    refinement=root/'runs'/'B_layer_refinement_v1'
    first=json.loads((base/'summary.json').read_text(encoding='utf8'))
    readback=json.loads((base/'readback_verification.json').read_text(encoding='utf8'))
    extra=json.loads((refinement/'summary.json').read_text(encoding='utf8'))
    extra_readback=json.loads((refinement/'readback_verification.json').read_text(encoding='utf8'))
    if not readback['allDeliveredOutputsReadbackPassed'] or first['remainingModelCount']:
        raise ValueError('initial assembly/readback incomplete')
    if extra['attemptedModelCount']!=first['statusCounts']['search_failed']:
        raise ValueError('refinement has not examined all initial search failures')
    if extra_readback['readbackVerifiedModelCount']!=extra['attemptedModelCount'] or not extra_readback['allDeliveredOutputsReadbackPassed']:
        raise ValueError('refinement readback incomplete')
    if readback['counts']['verified_success']!=first['statusCounts']['success'] or extra_readback['counts'].get('verified_success',0)!=extra['statusCounts'].get('success',0):
        raise ValueError('verification and processing counts disagree')
    jobs=json.loads((base/'selection.json').read_text(encoding='utf8'))
    expected={job['modelId']:job for job in jobs}
    selected=[json.loads(line) for line in (refinement/'selected_assembly_index.jsonl').read_text(encoding='utf8').splitlines()]
    if len(selected)!=len(expected) or {r['modelId'] for r in selected}!=set(expected):
        raise ValueError('selected index is not one entry per original model')
    dataset=Path(json.loads((base/'config.json').read_text(encoding='utf8'))['datasetPath'])
    rows=[]
    counts=Counter()
    categories=defaultdict(Counter)
    for number,row in enumerate(selected,1):
        job=expected[row['modelId']]
        folder=Path(row['resultPath']).resolve()
        if not (folder.is_relative_to(base.resolve()) or folder.is_relative_to(refinement.resolve())):
            raise ValueError('selected output outside the two declared assembly runs')
        report_path=folder/'report.json'
        if a.file_sha(report_path)!=row['reportFileSha256']:
            raise ValueError('selected report changed')
        report=json.loads(report_path.read_text(encoding='utf8'))
        if report['sourceExactOccupancyHash']!=job['exactOccupancyHash'] or report['sourceCanonicalGeometryHash']!=job['canonicalGeometryHash']:
            raise ValueError('source target association mismatch')
        if report['geometryPassed']!=(row['status']=='success') or report['geometryPassed']!=report['validation']['passed']:
            raise ValueError('success status disagrees with independent verification')
        if report['geometryPassed'] and (not report['validation']['exactCoverage'] or not report['validation']['colorPreserved'] or report['validation']['studComponentCount']!=1):
            raise ValueError('successful output missing exact/connected geometry proof')
        source_folder=dataset/job['modelPath']
        suffix='' if row['status']=='success' else '.draft'
        rows.append({**row,'semanticGroupKey':job['modelId'],
                     'sourceModelJsonPath':str((source_folder/'model.json').resolve()),
                     'sourcePairedPromptsPath':str((source_folder/'prompts.json').resolve()),
                     'assemblyJsonPath':str(folder/'assembly.json'),
                     'modelTxtPath':str(folder/f'model{suffix}.txt'),
                     'modelLdrPath':str(folder/f'model{suffix}.ldr'),
                     'validationPath':str(folder/'validation.json'),
                     'brickCount':report['validation']['brickCount'],
                     'staticVerified':None,'fullPhysics':False})
        counts[row['status']]+=1
        categories[row['category']][row['status']]+=1
        if number%10000==0:
            print('SELECTION_ASSOCIATION_CHECK',number,'/',len(selected),flush=True)
    summary={'processedModelCount':len(rows),'sourceModelCount':len(expected),'remainingModelCount':0,
             'statusCounts':dict(counts),'additionalPassedModelCount':extra['statusCounts'].get('success',0),
             'geometryAssemblyPassRate':counts['success']/len(rows),
             'successfulBrickCount':sum(r['brickCount'] for r in rows if r['geometryPassed']),
             'categoryStatusCounts':{k:dict(v) for k,v in categories.items()},
             'allDeliveredOutputsReadbackPassed':True,'allModelsAssemblyPassed':counts['success']==len(rows),
             'physicsStatus':'not_attempted','staticVerifiedModelCount':0,'voxelSourceModified':False,
             'sourceTrainingPromptRecordCount':len(rows)*5,
             'coordinateMapping':'source Y-up [x,y,z] -> internal Z-up [x,z,y]',
             'physicalScaleNote':'1 horizontal grid unit=1 stud; 1 vertical grid unit=1 standard brick height; LDraw=20/20/24',
             'scope':'selected monochrome rectangular unit-height extended library; geometry checks, not full physics'}
    a.dump(root/'assembly_summary.json',summary)
    (root/'assembly_index.jsonl').write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows),encoding='utf8')
    text=['# B 分片 LEGO 拼接及校验交付报告','',
          f"实际处理 {len(rows):,} 个独立模型；几何装配通过 {counts['success']:,} 个（{counts['success']/len(rows):.2%}）。",
          f"当前规则的必要条件失败 {counts['infeasible_under_selected_policy']:,} 个；两套有界搜索仍未通过 {counts['search_failed']:,} 个。",
          f"补充 MRV 逐层精确覆盖新增通过 {extra['statusCounts'].get('success',0):,} 个；两批全部输出已独立再次读回。",'',
          '原 40,000 个体素模型、200,000 条配对训练记录、原数据压缩包都未修改。最终索引每个 modelId 一行，只选择一个拼接结果，不重复增加模型数量。',
          '成功输出 JSON/TXT/LDR；失败输出明确命名的 draft 文件和证据。JSON/TXT/LDR 回读、标准砖库、占用/RGB、碰撞、逐层下支撑、单stud组件与接地均实测。',
          '必要条件失败仅适用于当前同色矩形、单砖高、上下stud连接及支撑策略；搜索失败不证明无解。',
          '静力、抗倾覆、接头受力、摩擦、插入路径及实物搭建均未验证，不能称物理验收通过。','',
          '坐标从 Y-up 转为 Z-up，不改离散占用；水平1stud、竖直1标准砖高，LDraw比例20/20/24，实物高宽比与等距体素预览不同。','',
          '| 类别 | 模型数 | 拼接通过 | 必要条件失败 | 搜索未通过 |','|---|---:|---:|---:|---:|']
    for category,c in categories.items():
        text.append(f"| {category} | {sum(c.values())} | {c['success']} | {c['infeasible_under_selected_policy']} | {c['search_failed']} |")
    text+=['','最终定位：assembly_index.jsonl 的 assemblyJsonPath/modelLdrPath/validationPath 指向被选结果；sourcePairedPromptsPath 指向该模型原有五级配对记录。',
           'assembly_algorithm_v2.zip 只含算法、工具源码快照、测试和汇总/索引，不含 runs/models 的完整拼接资产；实际模型文件保存在本目录 runs/。',
           '原数据的历史与 A/B 去重状态不因拼接而改变。']
    (root/'ASSEMBLY_REPORT.md').write_text('\n'.join(text)+'\n',encoding='utf8')
    archive=root/'assembly_algorithm_v2.zip'
    files=[p for p in root.iterdir() if p.is_file() and p.suffix in ('.py','.md','.json','.jsonl')
           and p.name!='assembly_delivery_verification.json']
    files+=list((root/'toolkit_snapshot').glob('*.py'))+list((root/'validation').glob('*.json'))
    for run in (base,refinement):
        files+=[run/name for name in ('config.json','summary.json','readback_verification.json')]
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in sorted(set(files)):
            z.write(path,path.relative_to(root).as_posix())
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError('algorithm metadata ZIP CRC failed')
    digest=a.file_sha(archive)
    (root/'SHA256SUMS').write_text(digest+'  '+archive.name+'\n',encoding='ascii')
    a.dump(root/'assembly_delivery_verification.json',{'passed':True,'processedModelCount':len(rows),
             'successModelCount':counts['success'],'uniqueModelAssociations':True,
             'baseExportReadbackPassed':True,'refinementExportReadbackPassed':True,
             'algorithmMetadataZipCrcPassed':True,'algorithmMetadataZipSha256':digest,
             'algorithmMetadataZipContainsModelAssets':False,'physicsStatus':'not_attempted'})
    print('ASSEMBLY_DELIVERY_VERIFIED',dict(counts),flush=True)


if __name__=='__main__':
    main()
