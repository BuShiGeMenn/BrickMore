"""Package regenerated models with an offline Three.js review page."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import zipfile

HTML = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BrickMore · 五组重生成</title>
<script type="importmap">{"imports":{"three":"./static/three.module.js"}}</script>
<style>
*{box-sizing:border-box}body{margin:0;background:#f3f5f7;color:#19232f;font:15px/1.6 system-ui,"Microsoft YaHei",sans-serif}
header{padding:24px 36px 18px;background:#fff;border-bottom:1px solid #dde2e8}h1{margin:0;font-size:26px}header p{margin:6px 0 0;color:#5b6675}
main{display:grid;grid-template-columns:290px 1fr;gap:24px;max-width:1440px;margin:auto;padding:24px}.cards{display:grid;gap:12px;align-content:start}
.card{display:flex;align-items:center;gap:12px;text-align:left;background:#fff;border:1px solid #dde2e8;border-radius:12px;padding:10px;cursor:pointer;width:100%;color:inherit}.card.selected{border:2px solid #b87b13;padding:9px}.card img{width:90px;height:80px;object-fit:cover;border-radius:7px}.card strong{display:block;font-size:15px}.card small{color:#647081}
.panel{background:#fff;border:1px solid #dde2e8;border-radius:16px;overflow:hidden}#viewer{height:520px;position:relative;background:#e9edf2}#viewer canvas{display:block}.details{padding:22px 26px}h2{margin:0 0 10px;font-size:22px}.prompt{padding:14px 16px;border-left:3px solid #d2a241;background:#faf6ec;color:#493e2c;margin:12px 0;white-space:pre-wrap}.stats{color:#536171;font-size:14px}.actions{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0}.actions a,button.toggle{color:#714b0b;text-decoration:none;border:1px solid #d8b97d;border-radius:7px;background:#fffaf0;padding:7px 12px;cursor:pointer;font:inherit}.note{font-size:13px;color:#718092;margin:12px 0 0}#status{position:absolute;top:12px;left:16px;color:#596675;font-size:13px}
@media(max-width:850px){main{grid-template-columns:1fr;padding:14px}.cards{grid-template-columns:repeat(2,minmax(0,1fr))}.card img{width:60px;height:60px}#viewer{height:420px}header{padding:20px}}
</style>
<header><h1>BrickMore · 五组重生成</h1><p>camera L2 / car L4 / car L5 / guitar L1 / vessel L1 · 新措辞，训练元素，同级复杂度 · car L3 与 piano L5 保持原选择</p></header>
<main><aside class="cards" id="cards"></aside><section class="panel"><div id="viewer"><span id="status">正在载入</span></div><div class="details"><h2 id="title"></h2><div class="stats" id="stats"></div><div class="prompt" id="prompt"></div><button class="toggle" id="toggle">查看原始排砖</button><div class="actions" id="links"></div><p class="note">左键旋转，滚轮缩放，右键平移。黄色为统一展示色；模型输出不包含颜色。几何和凸点连通检查不等同于物理稳定性认证，外形请人工复审。</p></div></section></main>
<script type="module">
import * as THREE from 'three';
import {OrbitControls} from './static/OrbitControls.js';
const rows=await(await fetch('manifest.json')).json();
const host=document.querySelector('#viewer'),scene=new THREE.Scene();scene.background=new THREE.Color('#e9edf2');
const camera=new THREE.PerspectiveCamera(35,1,.1,10000),renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.SRGBColorSpace;host.append(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;
scene.add(new THREE.HemisphereLight(0xffffff,0x8191a6,2.1));
for(const [x,y,z,p] of [[40,70,35,3],[-40,30,-15,1.2]]){let light=new THREE.DirectionalLight(0xffffff,p);light.position.set(x,y,z);scene.add(light)}
let model=null,current=null,raw=false,serial=0;
const material=new THREE.MeshStandardMaterial({color:0xe8b42b,roughness:.36,metalness:0});
const studGeo=new THREE.CylinderGeometry(.24,.24,.2,16);
function resize(){const w=host.clientWidth,h=host.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix()}
new ResizeObserver(resize).observe(host);resize();
function clean(){if(!model)return;scene.remove(model);model.traverse(o=>{if(o.geometry&&o.geometry!==studGeo)o.geometry.dispose()})}
async function show(row,reset=true){current=row;const ticket=++serial;
document.querySelector('#title').textContent=row.category+' · L'+row.level+' · Seed '+row.seed;
document.querySelector('#prompt').textContent=row.prompt;
document.querySelector('#stats').textContent=(row.validation?'几何通过 · '+row.validation.brick_count+' 块砖 · '+row.validation.occupied_voxels+' 个占用格 · 单一凸点连通':'几何检查未通过，保留原始结果')+' · 外形待人工复审';
document.querySelector('#status').textContent=raw?'原始生成排砖':'保形重铺 / 最终几何';
document.querySelector('#toggle').textContent=raw?'查看最终几何':'查看原始排砖';
document.querySelectorAll('.card').forEach(c=>c.classList.toggle('selected',c.dataset.id===row.id));
const links=document.querySelector('#links');links.replaceChildren();
for(const [file,label]of [['model.ldr','下载 LDR'],['model.glb','下载 GLB'],['model.txt','下载排砖 TXT'],['raw.txt','模型原始输出'],['validation.json','检查记录'],['raw_report.json','原始检查']]){if(!row.validation&&(file.startsWith('model')||file==='validation.json'))continue;let a=document.createElement('a');a.href=row.folder+'/'+file;a.textContent=label;a.download='';links.append(a)}
let f=raw?'raw_geometry.json':(row.validation?'model.json':'raw_geometry.json');
const {bricks}=await(await fetch(row.folder+'/'+f)).json();if(ticket!==serial)return;
clean();model=new THREE.Group();const cells=new Set();for(const b of bricks)for(let x=b.x;x<b.x+b.h;x++)for(let y=b.y;y<b.y+b.w;y++)cells.add(`${x},${y},${b.z}`);
for(const b of bricks){let body=new THREE.Mesh(new THREE.BoxGeometry(b.h-.028,1.188,b.w-.028),material);body.position.set(b.x+b.h/2,(b.z+.5)*1.2,b.y+b.w/2);model.add(body);
for(let x=b.x;x<b.x+b.h;x++)for(let y=b.y;y<b.y+b.w;y++){if(cells.has(`${x},${y},${b.z+1}`))continue;let s=new THREE.Mesh(studGeo,material);s.position.set(x+.5,(b.z+1)*1.2+.1,y+.5);model.add(s)}}
let box=new THREE.Box3().setFromObject(model),center=box.getCenter(new THREE.Vector3());model.position.sub(center);scene.add(model);
if(reset){let size=box.getSize(new THREE.Vector3()),r=Math.max(size.x,size.y,size.z);camera.position.set(r*1.7,r*1.25,r*1.9);controls.target.set(0,0,0);controls.update()}}
for(const row of rows){const button=document.createElement('button');button.className='card';button.dataset.id=row.id;const img=document.createElement('img');img.src=row.folder+'/'+(row.preview_image||'preview.png');const label=document.createElement('span'),strong=document.createElement('strong'),small=document.createElement('small');strong.textContent=row.category+' · L'+row.level;small.textContent=(row.id.endsWith('_G')?'确定性解码':'Seed '+row.seed)+(row.source_candidate_id.startsWith('reconstructed-')?' · 新构造提示词':(row.source_candidate_id.startsWith('dataset-')?' · dataset 同级文本':(row.current_prompt?' · 当前提示词':' · 原同级备选')));label.append(strong,small);button.append(img,label);button.onclick=()=>{raw=false;show(row)};document.querySelector('#cards').append(button)}
document.querySelector('#toggle').onclick=()=>{raw=!raw;show(current,false)};
if(rows.length)await show(rows[0]);
renderer.setAnimationLoop(()=>{controls.update();renderer.render(scene,camera)});
</script></html>'''

LAUNCHER = '''from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import webbrowser
root=Path(__file__).resolve().parent
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(root)))
url=f'http://127.0.0.1:{server.server_port}/'
print('BrickMore preview:',url,flush=True)
if '--no-browser' not in sys.argv:
    webbrowser.open(url)
try:
    server.serve_forever()
except KeyboardInterrupt:
    server.server_close()
'''


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('output',type=Path)
    parser.add_argument('--destination',type=Path)
    args=parser.parse_args()
    base=args.output.resolve()
    root=Path(__file__).resolve().parents[2]
    (base/'static').mkdir(exist_ok=True)
    for name in ('three.module.js','OrbitControls.js'):
        shutil.copy2(root/'brickmore48_tools/showcase/static/js'/name,base/'static'/name)
    (base/'index.html').write_text(HTML,encoding='utf-8')
    (base/'start_preview.py').write_text(LAUNCHER,encoding='utf-8')
    (base/'start_preview.cmd').write_text('@echo off\ncd /d "%~dp0"\npython start_preview.py\npause\n',encoding='ascii')
    rows=json.loads((base/'manifest.json').read_text(encoding='utf-8'))
    attempts_path=base/'all_attempts_manifest.json'
    all_rows=json.loads(attempts_path.read_text(encoding='utf-8')) if attempts_path.exists() else []
    all_rows={row['id']:row for row in all_rows+rows}
    attempts_path.write_text(json.dumps(list(all_rows.values()),ensure_ascii=False,indent=2),encoding='utf-8')
    rows=[row for row in all_rows.values() if row.get('validation') and
          row.get('visual_review',{}).get('decision')!='rejected' and not row['status'].startswith('rejected')]
    plan=json.loads((base/'revised_prompts.json').read_text(encoding='utf-8'))
    expected={group['group']:{p['candidate_id']:p for p in group['prompts']} for group in plan['groups']}
    assert set(row['group'] for row in rows)==set(expected)
    sys.path.insert(0,str(root/'Train/algorithms/voxel_assembly_b'))
    import assembly_pipeline as assembly
    audit_rows=[]
    for row in rows:
        row['preview_image']='reverse.png' if row['category']=='camera' else 'preview.png'
        source_prompt=json.loads((base/row['folder']/'source_prompt.json').read_text(encoding='utf-8'))
        if 'evidence' in source_prompt:
            row['prompt_evidence']=source_prompt['evidence']
        generation=json.loads((base/row['folder']/'generation.json').read_text(encoding='utf-8'))
        assert row['prompt']==expected[row['group']][row['source_candidate_id']]['prompt']==source_prompt['prompt']==generation['prompt']
        assert generation['instruction'].split('### Input:\n',1)[1]==row['prompt']
        assert generation['completed'] and generation['revision']=='92d1c595f5fe076971cc2633d6844f097a84eef3'
        evidence=source_prompt['evidence']
        assert evidence['newly_constructed'] and not evidence['exact_caption_match']
        assert evidence['reference_caption']!=row['prompt']
        assert evidence['reference_caption'] not in generation['instruction']
        assert evidence['prompt_level']==row['level']
        reference=root/evidence['reference_file']
        assert hashlib.sha256(reference.read_bytes()).hexdigest()==evidence['reference_file_sha256']
        if row.get('validation'):
            folder=base/row['folder']
            bricks=json.loads((folder/'model.json').read_text(encoding='utf-8'))['bricks']
            back=assembly.parse_ldr((folder/'model.ldr').read_text(encoding='utf-8'))
            fields=('h','w','x','y','z')
            assert [tuple(b[k] for k in fields) for b in back]==[tuple(b[k] for k in fields) for b in bricks]
            expected_text=''.join(f"{b['h']}x{b['w']} ({b['x']},{b['y']},{b['z']})\n" for b in bricks)
            assert (folder/'model.txt').read_text(encoding='utf-8')==expected_text
            content=(folder/'model.glb').read_bytes()
            magic,version,length=struct.unpack('<4sII',content[:12])
            assert magic==b'glTF' and version==2 and length==len(content)
            render=json.loads((folder/'render_metadata.json').read_text(encoding='utf-8'))
            assert render['source_file']=='model.json'
            assert render['source_sha256']==hashlib.sha256((folder/'model.json').read_bytes()).hexdigest()
        audit_rows.append(dict(group=row['group'],prompt_matches_generation=True,
            new_wording_verified=True,dataset_caption_not_used_as_input=True,
            level_and_reference_hash_verified=True,ldr_txt_glb_readback_passed=bool(row.get('validation'))))
    same_outputs={}
    for row in rows:
        digest=hashlib.sha256((base/row['folder']/'raw.txt').read_bytes()).hexdigest()
        same_outputs.setdefault(digest,[]).append(row['id'])
    duplicates=[ids for ids in same_outputs.values() if len(ids)>1]
    (base/'artifact_audit.json').write_text(json.dumps(dict(passed=True,rows=audit_rows,
        identical_raw_output_groups=duplicates),ensure_ascii=False,indent=2),encoding='utf-8')
    recommended=[]
    seen_prompts=set()
    prompt_text=['BrickMore 本轮推荐提示词：全部重新构造，不复用 dataset 原始 caption。','']
    for row in rows:
        if row['source_candidate_id'] in seen_prompts:
            continue
        seen_prompts.add(row['source_candidate_id'])
        prompt=expected[row['group']][row['source_candidate_id']]
        recommended.append(dict(group=row['group'],category=row['category'],level=row['level'],**prompt))
        prompt_text.extend([row['group'],prompt['prompt'],prompt['prompt_zh'],''])
    (base/'recommended_prompts.json').write_text(json.dumps(recommended,ensure_ascii=False,indent=2),encoding='utf-8')
    (base/'recommended_prompts.txt').write_text('\n'.join(prompt_text),encoding='utf-8')
    (base/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    from PIL import Image, ImageDraw, ImageFont
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',23)
    small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
    overview=Image.new('RGB',(1440,76+((len(rows)+2)//3)*492),'#f3f5f7')
    draw=ImageDraw.Draw(overview)
    draw.text((24,18),'BrickMore · 五组重生成 · 实际模型预览',font=font,fill='#19232f')
    for i,row in enumerate(rows):
        x,y=(i%3)*480,76+(i//3)*492
        path=base/row['folder']/row['preview_image']
        if path.exists():
            picture=Image.open(path).convert('RGB').resize((480,427),Image.Resampling.LANCZOS)
            overview.paste(picture,(x,y))
        draw.text((x+16,y+430),row['category']+' · L'+str(row['level'])+' · '+str(row['seed']),font=font,fill='#19232f')
        check='几何通过，外形待复审' if row.get('validation') else '几何检查未通过'
        draw.text((x+16,y+461),check,font=small,fill='#5b6675')
    overview.save(base/'overview.png')
    detailed=Image.new('RGB',(1260,68+len(rows)*414),'#f3f5f7')
    draw=ImageDraw.Draw(detailed)
    draw.text((22,16),'多角度检查 · 视角一 / 侧面 / 视角二',font=font,fill='#19232f')
    for i,row in enumerate(rows):
        y=68+i*414
        draw.text((14,y),row['category']+' L'+str(row['level'])+' · Seed '+str(row['seed']),font=font,fill='#19232f')
        angles=('reverse','side','preview') if row['category']=='camera' else ('preview','side','reverse')
        for j,name in enumerate(angles):
            path=base/row['folder']/(name+'.png')
            if path.exists():
                picture=Image.open(path).convert('RGB').resize((420,373),Image.Resampling.LANCZOS)
                detailed.paste(picture,(j*420,y+36))
    detailed.save(base/'overview_all_angles.png')
    lines=['# BrickMore 五组重生成','',
           '模型：`Kyle308666/BrickGPT-Qwen3-1.7B-BrickMore-48`。',
           '固定版本：`92d1c595f5fe076971cc2633d6844f097a84eef3`。','',
           '双击 `start_preview.cmd` 打开可旋转三维预览（需要 Python，无需权重或 GPU）。',
           '`overview.png` 是实际生成模型的多角度总览。每个模型同时提供 GLB、LDR、TXT 和原始推理输出。','',
           '仅处理 camera L2、car L4、car L5、guitar L1、vessel L1。car L3 和 piano L5 的原人工选择未修改。',
           '五条推荐提示词均重新构造措辞，参考 dataset 对应 Level 的训练元素与复杂度，不直接使用 dataset 原始 caption。当前推荐原文见 recommended_prompts.txt / .json；全部版本和分级证据见 revised_prompts.json。',
           '第一批五个候选已由用户判为不合格；直接采用 dataset 原 caption 的第二批只作对照。前两批保留在单独目录，不计入本批。',
           '原始输出与实际解码参数见各模型目录。主候选采用确定性解码，汽车 L5 另提供采样候选供比较。','',
           'all_attempts_manifest.json 保留本批所有尝试（包括已淘汰结果）；预览只显示几何通过且未被外形初审淘汰的候选。','',
           '| 组 | 种子 | 提示词来源 | 几何与凸点检查 |',
           '|---|---:|---|---|']
    for row in rows:
        status='通过（外形待人工复审）' if row.get('validation') else '未通过'
        lines.append(f"| {row['group']} | {row['seed']} | {row['source_candidate_id']} | {status} |")
    if duplicates:
        lines.extend(['','确定性解码出现相同原始输出：'+'；'.join(' / '.join(ids) for ids in duplicates)+
                      '。另附汽车 L5 采样候选供比较。'])
    lines.extend(['','黄色是统一展示色，模型输出没有颜色。',
        'raw.txt 是未经改写的模型输出；raw_geometry.txt 为沿用既有审查管线 YX 尺寸约定后的 XY 标准排砖。',
        '保形重铺严格覆盖原始砖块占用的体素并集，不增删体素；原始重叠另有记录。',
        '该尺寸约定与既有 630 模型审查一致，尚未对照原训练转换器核验。',
        '几何无重叠、无越界、单一凸点连通不等同于物理稳定性认证。模型外形需要人工复审。',''])
    (base/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    checks=[]
    for path in sorted(base.rglob('*')):
        if path.is_file() and path.name!='checksums.sha256':
            checks.append(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.relative_to(base).as_posix())
    (base/'checksums.sha256').write_text('\n'.join(checks)+'\n',encoding='utf-8')
    archive=base.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as output:
        for path in sorted(base.rglob('*')):
            if path.is_file():
                output.write(path,base.name+'/'+path.relative_to(base).as_posix())
    with zipfile.ZipFile(archive) as output:
        assert output.testzip() is None
    if args.destination:
        if args.destination.exists():
            raise FileExistsError('Destination already exists; preserve the previous delivery')
        shutil.copytree(base,args.destination)
        shutil.copy2(archive,args.destination.with_suffix('.zip'))
    print('PACKAGED',base,'ZIP',archive,flush=True)


if __name__=='__main__':
    main()
