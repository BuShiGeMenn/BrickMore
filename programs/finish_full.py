"""Publish only the completely verified local AI_A shard and its 40 packages."""
import hashlib,json,zipfile,subprocess
from concurrent.futures import ThreadPoolExecutor,as_completed
from produce import ROOT,savejson
from finish import viewer,package

def main():
    manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'));rows=manifest['models'];assert len(rows)==40000
    verification=json.loads((ROOT/'independent_verification.json').read_text(encoding='utf-8'));assert verification['passed']
    structural=json.loads((ROOT/'structural_review.json').read_text(encoding='utf-8'));assert structural['status']=='screens_passed'
    cross=json.loads((ROOT/'cross_category_structural_review.json').read_text(encoding='utf-8'));assert cross['passed']
    family=json.loads((ROOT/'family_design_audit.json').read_text(encoding='utf-8'));assert family['passed']
    # Independently compare the exported per-model index with the manifest.
    with (ROOT/'dedup_index.jsonl').open(encoding='utf-8') as handle:
        for row in rows:assert json.loads(next(handle))==row,'dedup index and manifest differ'
        assert next(handle,None) is None,'extra dedup index row'
    savejson(ROOT/'index_verification.json',{'passed':True,'manifestModelCount':len(rows),'dedupIndexRowCount':len(rows),
        'allIndexRowsEqualManifest':True,'uniqueModelIdCount':len({r['modelId'] for r in rows})})
    viewer(rows);path=ROOT/'查看效果.html'
    path.write_text(path.read_text(encoding='utf-8').replace('10000 个体素模型效果查看','40000 个体素模型效果查看').replace('10,000 个体素模型','40,000 个体素模型').replace('50,000 条中英双语描述','200,000 条中英双语描述'),encoding='utf-8')
    subprocess.run(['node',str(ROOT/'programs'/'verify_viewer.cjs')],check=True)
    pilot=[next(r for r in rows if r['category']==c) for c in manifest['categoryCounts']]
    savejson(ROOT/'pilot_manifest.json',{'modelCount':21,'promptRecordCount':105,'models':pilot})
    savejson(ROOT/'pilot_independent_verification.json',{'passed':True,'modelCount':21,'promptRecordCount':105,
        'evidence':'These retained pilot geometries are included in the complete 40000-model independent readback.','fullReport':'independent_verification.json'})
    (ROOT/'README.md').write_text('''# AI_A 完整 40,000 模型交付

本次补齐30,000个模型和150,000条双语记录，保留首批10,000个模型的实际几何与已审定结构族。完整交付40,000个独立模型、200,000条中英文配对训练记录；L1—L5各40,000条。21类中前20类各1,905模型，vessel为1,900模型；各类40个真实结构族，按任务规定每族47或48模型。

打开“查看效果.html”可离线旋转查看21类×3个实际模型、切换五级描述、载入其他model.json，并浏览各类8个样例拼图。preview_21_categories.png为总览，models/为全部模型，training_subsets/为105个类别/级别子集。

每模型750—1250个体素，坐标0—47、X左右/Y向上/Z前后，最低真实接地点Y=0，单一六邻域连通分量。每个模型仅一份几何，五级记录引用同一modelId、seed、hash和路径。目录包含model.json、model.npz、model.obj、model.mtl、model.vox、preview.png、validation.json、prompts.json。模型由可复现的本地连续解析参数程序生成，L5建模文字和geometryPlan共同记录设计规格；每次密度尝试直接从原始参数几何统一XYZ重建。未使用随机删点、填实空腔、无关支撑或去重签名凸点。

训练默认使用captionZh/En；voxelPromptZh/En含固定执行规则，作为备用字段。不同详细级别逐级增加事实，均描述同一目标几何。五条双语记录算五条，不将中英文加倍计数。每个模型ordinal按类别/序号排序为1—40000，modelSeed=800000000+ordinal。

独立验证从磁盘读取所有模型格式、外表面材质与五级描述，重新计算体素数、RGB、占用、部件尺寸、相对体积、部件位置和类别拓扑；NPZ与JSON逐点相同，VOX写出(x,z,y)后读回逆变换一致，OBJ全部可见外表面与真实占用一致，PNG可解码。检查空腔/封底/侧漏、把手孔/根部、轮组、支脚、层板空隙、功能开口及表面特征的空气邻居、部件连接和预期相机射线。每250个新增模型保存进度并执行独立回读；最终40,000模型统一独立验收。

全部40,000个exact和canonical占用hash唯一，与55,255条历史原始hash无重叠。canonical枚举48种轴置换与正负组合，各轴平移归零，坐标排序串联后取48个SHA256的字典序最小值，忽略颜色。结构筛查覆盖全部类内模型对、全部类别组合的候选近形、每类780个实际结构族锚点对及族内全部实例对；每对族内实例须在至少两项实际部件尺寸、相对体积或相对位置上差异达到0.025。比例相近候选比较三个正交轮廓与保留空腔的统一比例归一占用。阈值和结果见structural_review、cross_category_structural_review与family_design_audit。自动筛查不能代替审美和全面人工语义评估。

首批结构族曾根据实际几何重新审核分配；本次沿用其真实锚点和已交付实例，扩充类别合理比例、轮廓和附件位置，再筛除重复，不修改首批几何。retained_first10000.json和independent_verification.json记录保留核对。失败密度/拓扑/重复方案保留在retry_queue.jsonl并重新规划，不丢失最终配额。

packages/包含40个完整分包，每包1,000模型和5,000条记录，另有metadata.zip保存训练文件、索引、设计、报告、查看器和生产/验证程序。所有分包可解压到同一根目录；每包元数据保存在不同的package_metadata/AI_A_XX/目录，互不覆盖。分包均验证ZIP CRC、模型数和条目数，package_manifest.json记录SHA256；SHA256SUMS.txt提供全文件校验值。

复现依赖Python、numpy、scipy、Pillow。programs/complete_shard.py --workers 12支持检查点恢复，geometry.py解释保存的geometryPlan，review_full.py进行完整结构审核，verify.py独立回读并流式核对JSONL/CSV及子集，finish_full.py打包。首批原交付目录独立保留。

历史只提供hash，没有完整坐标，所以历史旋转/镜像及近重复检查标记unavailable_coordinates。尚未收到AI_B索引，A/B合并去重保持awaiting_merge。本次未执行LEGO排砖或物理稳定性处理（not_run）。
''',encoding='utf-8')
    (ROOT/'packages').mkdir(exist_ok=True);packs=[]
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures=[pool.submit(package,i,rows[i*1000:(i+1)*1000]) for i in range(40)]
        for future in as_completed(futures):packs.append(future.result());print('PACKAGE VERIFIED',packs[-1]['package'],len(packs),'/ 40',flush=True)
    savejson(ROOT/'package_manifest.json',{'packages':sorted(packs,key=lambda p:p['package']),'modelCount':40000,'promptRecordCount':200000,
        'retainedFirstBatchModelCount':10000,'newModelCount':30000,'allPackageCrcPassed':True})
    savejson(ROOT/'generation_status.json',{'status':'completed_AI_A_40000','completedModelCount':40000,'completedPromptRecordCount':200000,
        'retainedFirstBatchModelCount':10000,'newModelCount':30000,'pendingModelCount':0,'failedModelCount':0,
        'fullShardRemainingModelCount':0,'independentReadbackPassed':True,'structuralScreensPassed':True,'packageCount':40,
        'crossShardDedupStatus':'awaiting_merge','historicalCanonicalDedupStatus':'unavailable_coordinates','legoPhysicalProcessingStatus':'not_run'})
    metadata=ROOT/'packages'/'metadata.zip'
    files=[f for f in ROOT.rglob('*') if f.is_file() and '__pycache__' not in f.parts]
    with zipfile.ZipFile(metadata,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
        for file in files:
            parts=file.relative_to(ROOT).parts
            if not any(p in parts for p in ['models','packages','checkpoints']) and file.name!='SHA256SUMS.txt':z.write(file,file.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(metadata) as z:assert z.testzip() is None
    print('METADATA CRC VERIFIED',metadata.stat().st_size,flush=True)
    files=[f for f in ROOT.rglob('*') if f.is_file() and '__pycache__' not in f.parts and f.name!='SHA256SUMS.txt' and f.suffix not in ['-wal','-shm']]
    with (ROOT/'SHA256SUMS.txt').open('w',encoding='utf-8') as out:
        for i,file in enumerate(sorted(files),1):
            with file.open('rb') as handle:sha=hashlib.file_digest(handle,'sha256').hexdigest()
            out.write(sha+'  '+file.relative_to(ROOT).as_posix()+'\n')
            if i%40000==0:print('FILE HASHES',i,'/',len(files),flush=True)
    print('FULL DELIVERY READY',len(files),'hashed files',flush=True)

if __name__=='__main__':main()
