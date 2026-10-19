import json,hashlib,zipfile,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from collections import Counter
from produce import ROOT,savejson

def viewer(rows):
    examples=[]
    categories=list(dict.fromkeys(r['category'] for r in rows))
    for cat in categories:
        cr=[r for r in rows if r['category']==cat]
        for i in range(3):
            row=cr[i*len(cr)//3];doc=json.loads((ROOT/row['modelJsonPath']).read_text(encoding='utf-8'))
            recs=json.loads((ROOT/row['modelJsonPath']).with_name('prompts.json').read_text(encoding='utf-8'))
            examples.append({'category':cat,'modelId':row['modelId'],'voxels':doc['voxels'],'captions':[r['captionZh'] for r in recs]})
    html='''<!DOCTYPE html><html lang="zh"><meta charset="utf-8"><title>10000 个体素模型效果查看</title>
<style>body{margin:0;background:#f2f5fa;font:16px system-ui;color:#233047}header{padding:22px 30px;background:#172941;color:white}h1{font-size:25px;margin:0 0 8px}main{max-width:1300px;margin:25px auto;padding:0 20px}.controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap}select,button{font:inherit;padding:9px;border:1px solid #cad4e0;border-radius:6px;background:white}canvas{width:100%;height:580px;background:#fff;border-radius:15px;margin:18px 0;touch-action:none}.caption{background:white;padding:22px;border-radius:12px;line-height:1.9}a{color:#316bc0}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:20px}.cards img{width:100%}.hint{color:#64748b;margin:12px 0}.cards a{background:white;padding:10px;border-radius:10px;text-decoration:none}</style>
<header><h1>10,000 个体素模型 · 效果查看</h1><div>21 类 · 50,000 条中英双语描述 · 每个模型一份几何</div></header>
<main><div class="controls"><select id="cat"></select><select id="example"></select><select id="level"><option value="0">L1 简短描述</option><option value="1">L2 基本结构</option><option value="2">L3 几何</option><option value="3">L4 比例</option><option value="4" selected>L5 完整描述</option></select><button id="front">正视</button><button id="side">侧视</button><button id="top">俯视</button><button id="iso">斜视</button><label>打开其他模型 <input type="file" id="file" accept=".json"></label></div>
<div class="hint">拖动模型旋转，滚轮缩放。每类内置 3 个实际模型；下方图片可查看该类 8 个样例。所有内容可离线查看。</div><canvas id="canvas"></canvas><div id="caption" class="caption"></div><div id="info" class="hint"></div><div id="cards" class="cards"></div></main>
<script>const data=__DATA__;const cat=document.getElementById('cat'),ex=document.getElementById('example'),level=document.getElementById('level'),cv=document.getElementById('canvas'),ctx=cv.getContext('2d');let current=data[0],yaw=.65,pitch=.45,zoom=1,drag=null;
const categories=[...new Set(data.map(d=>d.category))];categories.forEach(c=>cat.add(new Option(c,c)));
function choose(){let items=data.filter(d=>d.category===cat.value);ex.innerHTML='';items.forEach((d,i)=>ex.add(new Option('样例 '+(i+1),data.indexOf(d))));current=items[0];show()}
function show(){document.getElementById('caption').textContent=(current.captions||[])[+level.value]||'已载入实际模型，可旋转查看。';document.getElementById('info').textContent=current.modelId+' · '+current.voxels.length+' 个体素';render()}
function render(){cv.width=cv.clientWidth*devicePixelRatio;cv.height=cv.clientHeight*devicePixelRatio;let W=cv.width,H=cv.height;ctx.clearRect(0,0,W,H);let vox=current.voxels,min=[48,48,48],max=[0,0,0];vox.forEach(v=>[v.x,v.y,v.z].forEach((n,i)=>{min[i]=Math.min(min[i],n);max[i]=Math.max(max[i],n)}));let center=min.map((n,i)=>(n+max[i]+1)/2),span=Math.max(...max.map((n,i)=>n-min[i]+1)),scale=Math.min(W,H)*.73/span*zoom;
function tr(p){let x=p[0]-center[0],y=p[1]-center[1],z=p[2]-center[2],xx=x*Math.cos(yaw)-z*Math.sin(yaw),zz=x*Math.sin(yaw)+z*Math.cos(yaw);return [W/2+xx*scale,H/2+(-y*Math.cos(pitch)+zz*Math.sin(pitch))*scale,zz*Math.cos(pitch)+y*Math.sin(pitch)]}
let occupied=new Set(vox.map(v=>[v.x,v.y,v.z].join(','))),faces=[],defs=[[[1,0,0],[[1,0,0],[1,1,0],[1,1,1],[1,0,1]],.85],[[-1,0,0],[[0,0,1],[0,1,1],[0,1,0],[0,0,0]],.85],[[0,1,0],[[0,1,1],[1,1,1],[1,1,0],[0,1,0]],1],[[0,-1,0],[[0,0,0],[1,0,0],[1,0,1],[0,0,1]],.58],[[0,0,1],[[1,0,1],[1,1,1],[0,1,1],[0,0,1]],.72],[[0,0,-1],[[0,0,0],[0,1,0],[1,1,0],[1,0,0]],.72]];
vox.forEach(v=>defs.forEach(([n,c,s])=>{if(occupied.has([v.x+n[0],v.y+n[1],v.z+n[2]].join(',')))return;let normal=n[0]*Math.sin(yaw)*Math.cos(pitch)+n[2]*Math.cos(yaw)*Math.cos(pitch)+n[1]*Math.sin(pitch);if(normal<=0)return;let pts=c.map(p=>tr([v.x+p[0],v.y+p[1],v.z+p[2]]));faces.push({pts,depth:pts.reduce((a,p)=>a+p[2],0)/4,col:v.color.map(a=>Math.round(a*s))})}));faces.sort((a,b)=>a.depth-b.depth);faces.forEach(f=>{ctx.beginPath();f.pts.forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.closePath();ctx.fillStyle='rgb('+f.col.join(',')+')';ctx.fill()})}
cat.onchange=choose;ex.onchange=()=>{current=data[+ex.value];show()};level.onchange=show;cv.onpointerdown=e=>{drag=[e.clientX,e.clientY];cv.setPointerCapture(e.pointerId)};cv.onpointerup=()=>drag=null;cv.onpointermove=e=>{if(drag){yaw+=(e.clientX-drag[0])*.009;pitch=Math.max(-1.4,Math.min(1.4,pitch+(e.clientY-drag[1])*.008));drag=[e.clientX,e.clientY];render()}};cv.onwheel=e=>{e.preventDefault();zoom=Math.max(.4,Math.min(3,zoom*Math.exp(-e.deltaY*.001)));render()};[['front',0,0],['side',Math.PI/2,0],['top',0,1.55],['iso',.65,.45]].forEach(([id,y,p])=>document.getElementById(id).onclick=()=>{yaw=y;pitch=p;render()});window.onresize=render;document.getElementById('file').onchange=async e=>{try{let d=JSON.parse(await e.target.files[0].text());if(!Array.isArray(d.voxels))throw Error('需要 model.json 文件');current=d;show()}catch(err){alert(err.message)}};
document.getElementById('cards').innerHTML=categories.map(c=>'<a href="previews/'+c+'.png"><b>'+c+'</b><img loading="lazy" src="previews/'+c+'.png"></a>').join('');choose();</script></html>'''
    (ROOT/'查看效果.html').write_text(html.replace('__DATA__',json.dumps(examples,ensure_ascii=False,separators=(',',':'))),encoding='utf-8')

def package(index,rows):
    path=ROOT/'packages'/f'AI_A_models_{index+1:02d}_1000.zip'
    recs=[]
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
        for row in rows:
            folder=(ROOT/row['modelJsonPath']).parent
            for file in sorted(folder.iterdir()):
                if file.is_file():z.write(file,file.relative_to(ROOT).as_posix())
            recs+=json.loads((folder/'prompts.json').read_text(encoding='utf-8'))
        prefix=f'package_metadata/AI_A_{index+1:02d}/'
        z.writestr(prefix+'manifest.json',json.dumps({'modelCount':len(rows),'promptRecordCount':len(recs),'models':rows},ensure_ascii=False))
        z.writestr(prefix+'all_prompts.jsonl','\n'.join(json.dumps(r,ensure_ascii=False,separators=(',',':')) for r in recs)+'\n')
        z.writestr(prefix+'validation_summary.json',json.dumps({'independentReadbackPassed':True,'modelCount':len(rows),'promptRecordCount':len(recs),'validationReport':'independent_verification.json'}))
        z.writestr(prefix+'README.txt','本包含1000个独立模型、5000条描述。将所有分包解压到同一根目录，models路径保持一致。各包元数据位于独立package_metadata子目录，互不覆盖。各模型包含JSON/NPZ/OBJ/MTL/VOX/四视图PNG/validation/prompts。')
    with zipfile.ZipFile(path) as z:
        bad=z.testzip();assert bad is None
        assert sum(n.endswith('/model.json') for n in z.namelist())==1000
        assert len(z.namelist())==8004
    return {'package':path.name,'modelCount':len(rows),'promptRecordCount':len(recs),'bytes':path.stat().st_size,
            'sha256':hashlib.file_digest(path.open('rb'),'sha256').hexdigest(),'zipCrcPassed':True}

def main():
    manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'));rows=manifest['models']
    verification=json.loads((ROOT/'independent_verification.json').read_text(encoding='utf-8'));assert verification['passed']
    structural=json.loads((ROOT/'structural_review.json').read_text(encoding='utf-8'));assert structural['status']=='screens_passed'
    cross=json.loads((ROOT/'cross_category_structural_review.json').read_text(encoding='utf-8'));assert cross['passed']
    viewer(rows)
    pilot_rows=[next(r for r in rows if r['category']==c) for c in dict.fromkeys(r['category'] for r in rows)]
    savejson(ROOT/'pilot_manifest.json',{'datasetVersion':manifest['datasetVersion'],'modelCount':21,'promptRecordCount':105,'models':pilot_rows})
    savejson(ROOT/'pilot_independent_verification.json',{'passed':True,'modelCount':21,'promptRecordCount':105,'evidence':'These current 21 pilot models are included in the successful full independent readback.','fullReport':'independent_verification.json'})
    readme=f'''# AI_A 首批 10,000 模型效果验收包

完成日期：2026-10-10。当前交付为用户指定的首批10,000个独立模型，配套50,000条中英双语训练记录，每级10,000条；不是40,000全任务完成包。

打开“查看效果.html”可离线旋转查看21类×3个实际样例，并查看每类8样例图片。preview_21_categories.png为总览，previews/为类别拼图。models/保存全部10,000个完整模型。

类别：basket、bed、bench、birdhouse各477模型；其余17类各476模型。所有模型750—1250体素、48网格、Y向上、最低接地点Y=0、单一六邻域组件。每个模型只存一份几何，五级描述引用同一modelId/seed/hash/路径。训练默认使用captionZh/En，voxelPromptZh/En为带执行规则的备用字段。

生成方法为本地可复现的参数化解析几何程序；不是调用图像生成或外部3D生成模型。L5文字和可执行geometryPlan共同记录建模规格。初始参数几何在每次密度尝试中统一XYZ重建，不使用删点、补数块、签名凸点或无关连接杆。脚、轮、提把、层板、封底、空腔和入口按所属类别设计。每模型包含JSON、NPZ、OBJ、MTL、VOX、四视图PNG、validation和五条prompts。

规范JSON生成后派生全部格式。独立验证重新读取JSON/NPZ/VOX/OBJ/MTL/PNG/五级描述，实测坐标颜色一致、体素数、连通、部件计数、容器侧漏和开口、把手孔、书架层板、轮组、表面功能锚点与预期相机射线；OBJ全部外表面和材质与占用格核对。实际前向为+Z、正视从+Z观察、右视从+X、俯视从+Y；VOX写出(x,z,y)，读回逆变换检查。

历史55,255个原始占用hash比较无重叠；本批exact/canonical hash各10,000个唯一。canonical算法枚举48种轴变换，平移归零，排序字符串取SHA256字典序最小值。历史无原坐标，所以历史旋转/镜像/近重复排除未获证明。AI_B索引未提供，跨任务去重状态awaiting_merge。

结构族复核发现原参数族在栅格化后重叠，因此以实际类别部件尺寸、相对体积和部件位置选取每类40个真实锚点，逐对检查至少两项测量差异，保留原规划并重新分配首批11/12实例配额。详情见design_manifest、family_design_audit和repair_history。近重复复核覆盖全部类内模型对，先筛体形及主要部件比例，再比较三视图轮廓和统一比例归一的完整占用（含空腔）；阈值和范围见structural_review。自动筛查提供可复核证据，视觉审美与全面语义质量仍由效果查看评估。

packages/含10个完整模型分包，每包1000模型+5000描述；metadata.zip含全量训练文件、索引、验证、设计和程序。解压到同一个目录，各级训练子集引用公共模型路径。

复现依赖：Python、numpy、scipy、Pillow。programs/produce.py --pilot或--full支持分类别检查点恢复；最终审核与族重新分配由repair_review.py执行，verify.py独立验收，audit_designs.py结构筛查，finish.py打包。geometryPlan包含实际全部参数，seed不是唯一的复现依据。

本批没有执行LEGO排砖或物理稳定性处理，也没有声称通过这些处理。
'''
    readme+='\n跨类别结构筛查另外在全部10,000模型建立统一的外形/体积/三视图面积索引，对候选跨类别模型比较完整三视图和体积IoU。发现的巴士/列车近形通过真实列车车钩和下部承重车架重设计解决，复核见cross_category_structural_review与train_category_redesign。\n'
    (ROOT/'README.md').write_text(readme,encoding='utf-8')
    savejson(ROOT/'generation_status.json',{'status':'completed_first_10000_review_batch','completedModelCount':10000,'completedPromptRecordCount':50000,
         'pendingModelCountThisBatch':0,'failedModelCountThisBatch':0,'fullShardRemainingModelCount':30000,
         'independentReadbackPassed':True,'structuralScreensPassed':True,'crossShardDedupStatus':'awaiting_merge','legoPhysicalProcessingStatus':'not_run'})
    (ROOT/'packages').mkdir(exist_ok=True);packs=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        fs=[pool.submit(package,i,rows[i*1000:(i+1)*1000]) for i in range(10)]
        for f in as_completed(fs):packs.append(f.result());print('PACKAGE VERIFIED',packs[-1]['package'],flush=True)
    savejson(ROOT/'package_manifest.json',{'packages':sorted(packs,key=lambda p:p['package']),'modelCount':10000,'promptRecordCount':50000})
    metadata=ROOT/'packages'/'metadata.zip'
    with zipfile.ZipFile(metadata,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
        for file in ROOT.rglob('*'):
            if file.is_file() and 'models' not in file.relative_to(ROOT).parts and 'packages' not in file.relative_to(ROOT).parts and '__pycache__' not in file.relative_to(ROOT).parts and 'checkpoints' not in file.relative_to(ROOT).parts:
                z.write(file,file.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(metadata) as z:assert z.testzip() is None
    files=[f for f in ROOT.rglob('*') if f.is_file() and '__pycache__' not in f.parts and f.name!='SHA256SUMS.txt']
    with (ROOT/'SHA256SUMS.txt').open('w',encoding='utf-8') as out:
        for file in sorted(files):
            with file.open('rb') as handle:sha=hashlib.file_digest(handle,'sha256').hexdigest()
            out.write(sha+'  '+file.relative_to(ROOT).as_posix()+'\n')
    print('DELIVERY READY',len(files),'hashed files',flush=True)

if __name__=='__main__':main()
