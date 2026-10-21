"""Evaluate all available Model GLBs with a fixed eight-view protocol and Base encoders."""
import argparse
import base64
import csv
import functools
import hashlib
import io
import json
import math
import statistics
import threading
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = {
    'version':'brickmore-eight-view-v1', 'width':512, 'height':512,
    'azimuth_degrees':list(range(0,360,45)), 'elevation_degrees':25,
    'camera':'perspective', 'fov_degrees':42, 'sphere_fit_margin':1.12,
    'material':'uniform LDraw yellow #f2cd37, matching bundled judge viewer',
    'background':'#c2c3bf', 'exposure':1.15, 'pooling':'max over eight views',
    'text':'original English prompt; no template',
    'scope':'semantic image-text alignment; not physical validity or color compliance',
}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    temp.replace(path)


def load_rows(path):
    if not path.exists(): return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def latest(path):
    return {row['sample_id']:row for row in load_rows(path)}


def manifest(out):
    rows=[]; missing=[]; ids=set(); candidates=0
    for package in sorted((ROOT/'Model').iterdir()):
        if not package.is_dir(): continue
        items_path=package/'judge_tool/static/items.json'
        if not items_path.exists(): continue
        items=json.loads(items_path.read_text(encoding='utf-8'))
        for category, levels in items.items():
            for level, values in levels.items():
                for item in values:
                    candidates+=1
                    key=item['id']
                    base=package/Path(item['glb']).parent
                    for variant in ('raw','stitched'):
                        path=base/f'{variant}.glb'
                        record={'sample_id':f'{package.name}__{key}__{variant}',
                                'candidate_id':key,'package':package.name,'category':category,
                                'level':level,'label':item['label'],'batch':item['batch'],
                                'variant':variant,'caption':item['prompt'].strip(),
                                'model_path':path.relative_to(ROOT).as_posix()}
                        assert record['sample_id'] not in ids
                        ids.add(record['sample_id'])
                        if not path.exists():
                            missing.append(record)
                            continue
                        record['model_sha256']=digest(path)
                        rows.append(record)
    all_files={path.relative_to(ROOT).as_posix() for path in (ROOT/'Model').rglob('*.glb')}
    indexed={row['model_path'] for row in rows}
    assert indexed==all_files, f'Unindexed GLBs: {sorted(all_files-indexed)[:5]}'
    out.mkdir(parents=True,exist_ok=True)
    with (out/'manifest.jsonl').open('w',encoding='utf-8') as stream:
        for row in rows: stream.write(json.dumps(row,ensure_ascii=False)+'\n')
    write_json(out/'missing_variants.json',missing)
    write_json(out/'render_protocol.json',PROTOCOL)
    write_json(out/'input_summary.json',{'candidates':candidates,'available_glbs':len(rows),
               'by_variant':dict(Counter(row['variant'] for row in rows)),
               'missing_by_variant':dict(Counter(row['variant'] for row in missing)),
               'categories':sorted({row['category'] for row in rows})})
    print(f'Indexed {len(rows)} GLBs / {candidates} candidates; missing variants: {len(missing)}',flush=True)


def render(out, limit):
    from PIL import Image
    from playwright.sync_api import sync_playwright
    rows=load_rows(out/'manifest.jsonl')
    if limit: rows=rows[:limit]
    protocol_hash=hashlib.sha256(json.dumps(PROTOCOL,sort_keys=True).encode()).hexdigest()
    source_hash=digest(Path(__file__).with_name('render.html'))
    complete=latest(out/'renders.jsonl')
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(ROOT)))
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
                headless=True,args=['--ignore-gpu-blocklist','--use-angle=d3d11','--disable-background-timer-throttling','--disable-renderer-backgrounding'])
            page=browser.new_page(viewport={'width':512,'height':512},device_scale_factor=1)
            page.goto(f'http://127.0.0.1:{server.server_port}/Evaluation/pipeline/render.html')
            page.wait_for_function('window.ready===true',timeout=60000)
            write_json(out/'renderer_info.json',page.evaluate('window.rendererInfo()'))
            with (out/'renders.jsonl').open('a',encoding='utf-8') as stream:
                for index,row in enumerate(rows):
                    cached=complete.get(row['sample_id'])
                    if cached and cached['model_sha256']==row['model_sha256'] and cached['protocol_hash']==protocol_hash and cached.get('renderer_source_sha256')==source_hash and all((out/path).is_file() for path in cached['view_paths']): continue
                    start=time.monotonic()
                    try:
                        result=page.evaluate('url=>window.renderModel(url)','/'+row['model_path'])
                        assert len(result['images'])==8
                        folder=out/'renders'/row['sample_id']; folder.mkdir(parents=True,exist_ok=True)
                        paths=[]; hashes=[]; foreground=[]
                        for view,encoded in enumerate(result['images']):
                            data=base64.b64decode(encoded)
                            image=Image.open(io.BytesIO(data)).convert('RGB')
                            assert image.size==(512,512)
                            assert max(high-low for low,high in image.getextrema())>20, 'Blank render'
                            path=folder/f'{view:02d}.png'; path.write_bytes(data)
                            paths.append(path.relative_to(out).as_posix()); hashes.append(hashlib.sha256(data).hexdigest())
                        record={**row,'view_paths':paths,'view_sha256':hashes,'protocol_hash':protocol_hash,
                                'renderer_source_sha256':source_hash,'bounds':result['bounds'],'triangles':result['triangles']}
                        stream.write(json.dumps(record,ensure_ascii=False)+'\n'); stream.flush()
                        if index%10==0 or index+1==len(rows):
                            print(f'Rendered {index+1}/{len(rows)} {row["sample_id"]} ({time.monotonic()-start:.1f}s)',flush=True)
                    except Exception as error:
                        with (out/'render_errors.jsonl').open('a',encoding='utf-8') as errors:
                            errors.write(json.dumps({'sample_id':row['sample_id'],'error':str(error)})+'\n')
                        raise
            browser.close()
    finally:
        server.shutdown(); server.server_close()


def score(out, models, metric, limit):
    import torch
    from importlib.metadata import version
    from PIL import Image
    torch.set_num_threads(4)
    assert torch.cuda.is_available()
    rows=load_rows(out/'manifest.jsonl')
    if limit: rows=rows[:limit]
    assert rows, 'No model records'
    renders=latest(out/'renders.jsonl')
    for row in rows:
        assert row['sample_id'] in renders, f'Missing render: {row["sample_id"]}'
        assert renders[row['sample_id']]['model_sha256']==row['model_sha256']
        assert len(renders[row['sample_id']]['view_paths'])==8
    model_dir=models/('siglip2-base' if metric=='siglip2' else 'pe-base')
    provenance=json.loads((model_dir/'download_manifest.json').read_text())
    if metric=='siglip2':
        from transformers import AutoModel, AutoProcessor
        model=AutoModel.from_pretrained(model_dir,local_files_only=True,dtype=torch.bfloat16).cuda().eval()
        processor=AutoProcessor.from_pretrained(model_dir,local_files_only=True,use_fast=False)
        context=64
        def compute(images,caption):
            tokens=processor.tokenizer(caption,add_special_tokens=True,truncation=False)['input_ids']
            inputs=processor(images=images,text=[caption],padding='max_length',truncation=True,max_length=context,return_tensors='pt')
            inputs={key:value.to('cuda',dtype=torch.bfloat16) if value.is_floating_point() else value.cuda() for key,value in inputs.items()}
            values=torch.sigmoid(model(**inputs).logits_per_image.float())[:,0]
            return values.cpu().tolist(),len(tokens)
        precision='bfloat16 weights/inference; sigmoid in float32'
    else:
        import open_clip
        model_id='local-dir:'+model_dir.as_posix()
        model,_,preprocess=open_clip.create_model_and_transforms(model_id)
        tokenizer=open_clip.get_tokenizer(model_id)
        model=model.cuda().eval()
        context=model.context_length
        def compute(images,caption):
            images=torch.stack([preprocess(image) for image in images]).cuda()
            text=tokenizer([caption]).cuda()
            count=len(tokenizer.encode(caption))+2
            with torch.autocast('cuda',dtype=torch.float16):
                image_features=model.encode_image(images,normalize=True)
                text_features=model.encode_text(text,normalize=True)
            # Float32 reduction avoids avoidable dot-product rounding.
            image_features=torch.nn.functional.normalize(image_features.float(),dim=-1)
            text_features=torch.nn.functional.normalize(text_features.float(),dim=-1)
            values=(image_features@text_features.T)[:,0]
            return values.cpu().tolist(),count
        precision='float32 weights; float16 autocast; normalized cosine reduction in float32'
    signature={'metric':metric,'model_repository':provenance['repository'],'model_revision':provenance['revision'],
               'context_length':context,'precision':precision,'image_size':224,'pooling':'max of eight views',
               'device':torch.cuda.get_device_name(0),'torch_version':torch.__version__,
               'package_versions':{name:version(name) for name in ('transformers','open_clip_torch','timm','pillow','torchvision')},
               'source_sha256':digest(Path(__file__))}
    print('Loaded',metric,signature,flush=True)
    meta_path=out/f'{metric}_config.json'
    if meta_path.exists():
        assert json.loads(meta_path.read_text())==signature, 'Scoring configuration changed; use a new output directory'
    else: write_json(meta_path,signature)
    result_path=out/f'{metric}.jsonl'; cached=latest(result_path)
    start=time.monotonic()
    with result_path.open('a',encoding='utf-8') as stream,torch.inference_mode():
        for index,row in enumerate(rows):
            rendered=renders[row['sample_id']]
            if row['sample_id'] in cached:
                old=cached[row['sample_id']]
                assert old['model_sha256']==row['model_sha256'] and old['view_sha256']==rendered['view_sha256']
                continue
            images=[]
            for path,expected in zip(rendered['view_paths'],rendered['view_sha256']):
                path=out/path
                assert digest(path)==expected
                with Image.open(path) as image: images.append(image.convert('RGB'))
            values,token_count=compute(images,row['caption'])
            assert len(values)==8 and all(math.isfinite(value) for value in values)
            assert all((0 if metric=='siglip2' else -1.00001)<=value<=1.00001 for value in values)
            record={**row,'view_sha256':rendered['view_sha256'],'scores':values,
                    'max_score':max(values),'mean_score':statistics.mean(values),
                    'best_view':max(range(8),key=values.__getitem__),
                    'text_token_count':token_count,'text_truncated':token_count>context}
            stream.write(json.dumps(record,ensure_ascii=False)+'\n'); stream.flush()
            if index%20==0 or index+1==len(rows):
                print(f'{metric}: {index+1}/{len(rows)} ({time.monotonic()-start:.1f}s elapsed)',flush=True)
    print(metric,'complete; peak allocated GPU MiB:',torch.cuda.max_memory_allocated()/1048576,flush=True)
    write_json(out/f'{metric}_runtime.json',{'wall_seconds':time.monotonic()-start,
                'peak_allocated_gpu_mib':torch.cuda.max_memory_allocated()/1048576,
                'result_rows':len(latest(result_path))})


def summarize(out):
    rows=load_rows(out/'manifest.jsonl'); renders=latest(out/'renders.jsonl')
    scores={metric:latest(out/f'{metric}.jsonl') for metric in ('siglip2','pe')}
    assert all(len(data)==len(rows) for data in scores.values()), 'Incomplete scores'
    combined=[]; groups=defaultdict(list)
    for row in rows:
        result=dict(row)
        for metric,data in scores.items():
            for field in ('max_score','mean_score','best_view','text_token_count','text_truncated'):
                result[f'{metric}_{field}']=data[row['sample_id']][field]
        combined.append(result)
        groups[(row['variant'],row['category'],row['level'])].append(result)
    with (out/'scores.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(combined[0])); writer.writeheader(); writer.writerows(combined)
    group_rows=[]
    for (variant,category,level),values in sorted(groups.items()):
        group_rows.append({'variant':variant,'category':category,'level':level,'count':len(values),
                           **{metric:statistics.mean(row[f'{metric}_max_score'] for row in values) for metric in scores}})
    with (out/'by_category_level.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(group_rows[0])); writer.writeheader(); writer.writerows(group_rows)
    overall={}
    for variant in ('raw','stitched'):
        values=[row for row in combined if row['variant']==variant]
        overall[variant]={'count':len(values),**{metric:statistics.mean(row[f'{metric}_max_score'] for row in values) for metric in scores},
                          'truncated':{metric:sum(row[f'{metric}_text_truncated'] for row in values) for metric in scores}}
    candidates=defaultdict(dict)
    for row in combined: candidates[(row['package'],row['candidate_id'])][row['variant']]=row
    paired=[]
    for (_,candidate),versions in candidates.items():
        if set(versions)=={'raw','stitched'}:
            paired.append({'candidate_id':candidate,'category':versions['raw']['category'],'level':versions['raw']['level'],
                           **{metric+'_delta':versions['stitched'][metric+'_max_score']-versions['raw'][metric+'_max_score'] for metric in scores}})
    with (out/'paired_changes.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(paired[0])); writer.writeheader(); writer.writerows(paired)
    summary={'input':json.loads((out/'input_summary.json').read_text()),'overall':overall,
             'paired_count':len(paired),'paired_mean_delta':{metric:statistics.mean(row[metric+'_delta'] for row in paired) for metric in scores},
             'rendered':len(renders),'per_view_images':len(renders)*8,
             'completed_at_utc':datetime.now(timezone.utc).isoformat()}
    write_json(out/'summary.json',summary)
    lines=['# Model 文件夹图文语义评分结果','',
           '使用 SigLIP2 Base 224 与 PE-Core Base 224。每份 GLB 渲染八个固定视角，单模型取视角最高分，汇总为样本均值。',
           '','| 版本 | GLB 数 | SigLIP2 | PE |','|---|---:|---:|---:|']
    for variant,value in overall.items(): lines.append(f'| {variant} | {value["count"]} | {value["siglip2"]:.6f} | {value["pe"]:.6f} |')
    lines+=['',f'共评估 {len(rows)} 份 GLB、{len(renders)*8} 张图片；配对候选 {len(paired)} 个。',
            '',f'拼接版减原始版的配对平均变化：SigLIP2 {summary["paired_mean_delta"]["siglip2"]:+.6f}，PE {summary["paired_mean_delta"]["pe"]:+.6f}。',
            '', '## 解释与限制','',
            '- 每个候选使用自己的原始英文提示词，候选之间的提示词不同。分数不能单独作为同组最佳模型判据。',
            '- 为匹配自带评审器，所有模型统一使用黄色材质；不评估原始颜色。',
            '- PE Base 上下文仅 32 tokens，长描述发生截断；数量见 summary.json 与逐行结果。',
            '- 采用本项目固定渲染协议；这些 Base 模型分数不能直接与 Giant/bigG 论文数字比较。',
            '- 这些是图文语义匹配分数，不是正确率，也不证明连接、碰撞或物理稳定性。',
            '- 缺失版本列于 missing_variants.json，没有替代为另一版本或按零分计入均值。',
            '', '完整逐模型结果见 scores.csv；八视角分数见 siglip2.jsonl 与 pe.jsonl；配对变化见 paired_changes.csv。']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['manifest','render','score','summarize'])
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--models',type=Path,default=Path(r'D:\PythonEnvs\brickmore-eval\cache\huggingface\models'))
    parser.add_argument('--metric',choices=['siglip2','pe'])
    parser.add_argument('--limit',type=int,default=0)
    args=parser.parse_args(); args.out=args.out.resolve()
    if args.action=='manifest': manifest(args.out)
    elif args.action=='render': render(args.out,args.limit)
    elif args.action=='score':
        assert args.metric
        score(args.out,args.models,args.metric,args.limit)
    else: summarize(args.out)


if __name__=='__main__': main()
