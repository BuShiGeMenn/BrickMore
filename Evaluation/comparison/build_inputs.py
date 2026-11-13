"""Audit and stage the three supplied generators, with a fixed matched-prompt cohort."""
from __future__ import annotations
import argparse,collections,hashlib,importlib.machinery,importlib.util,json,shutil,sys,tarfile,zipfile
from pathlib import Path
import numpy as np
from assemblies import recover_glb,recover_procedural_glb,parse_ldr,orient_ldraw
from common import dump,write_rows,sha,Progress

WORKSPACE=Path(__file__).resolve().parents[2]
SOURCE=WORKSPACE/'BrickNet_BrickGPT_Compirasion'

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    from bricknet.data import load_catalog,load_aliases
    catalog,aliases=load_catalog(),load_aliases()
    plan_dir=SOURCE/'BrickMore_交接包_20261030/prompt对照实验_均分2份_20261109'
    batches={part:json.loads((plan_dir/(part+'_57条_prompts.json')).read_text(encoding='utf-8-sig'))['prompts'] for part in ('A','B')}
    prompts={r['prompt_id']:{**r,'batch':part} for part,seq in batches.items() for r in seq}
    assert len(prompts)==114
    curated_path=SOURCE/'BrickMore_汇总交付_20261107/展示/static/curated.json'
    display=curated_path.parent.parent;curated=json.loads(curated_path.read_text(encoding='utf-8-sig'))
    model_to_prompt={mid:r for r in prompts.values() for mid in r['model_ids']}
    assert len(model_to_prompt)==115
    registry={r['id']:r for r in curated}
    for mid,r in model_to_prompt.items():assert registry[mid]['prompt']==r['prompt'],mid
    original=out/'Data/original';assemblies=out/'Data/assemblies';assemblies.mkdir(parents=True,exist_ok=True)
    staged=[];by_id={};glb_bounds=[];needed=set();checks=[]
    legacy_file=next((WORKSPACE/'Deploy/build/eval630_20261027_staging').rglob('glb_structure*.pyc'),None)
    legacy=None
    if legacy_file:
        loader=importlib.machinery.SourcelessFileLoader('legacy_glb_reference',str(legacy_file));spec=importlib.util.spec_from_loader('legacy_glb_reference',loader)
        legacy=importlib.util.module_from_spec(spec);loader.exec_module(legacy)
    def add(system,mid,variant,caption,category,level,prompt_id,batch,source_path=None,source_bytes=None,source_name=None,extra=None):
        sid=f'{system.lower()}__{mid}__{variant}';suffix=Path(source_name or source_path).suffix.lower()
        target=original/system/(sid+suffix);target.parent.mkdir(parents=True,exist_ok=True)
        content=source_bytes if source_bytes is not None else Path(source_path).read_bytes();target.write_bytes(content)
        if suffix=='.ldr':assembly=parse_ldr(content.decode('utf-8-sig'),catalog,aliases)
        else:
            try:assembly=recover_glb(target)
            except ValueError:assembly=recover_procedural_glb(target)
            if legacy and not assembly.get('reconstruction'):
                ref=legacy.recover(target)
                assert len(ref['instances'])==len(assembly['instances'])
                for a,b in zip(ref['instances'],assembly['instances']):
                    assert a['part_stem']==b['part_stem'] and np.allclose(a['matrix_ldu'],b['matrix_ldu'],atol=1e-7),sid
            glb_bounds.extend((sid,b) for b in assembly['mesh_bounds'])
        needed.update(i['part_stem'] for i in assembly['instances']);assembly=orient_ldraw(assembly)
        ap=assemblies/(sid+'.json');dump(ap,assembly)
        row=dict(sample_id=sid,system=system,model_id=mid,variant=variant,caption=caption,category=category,
                 level=level if level in range(1,6) else None,prompt_id=prompt_id,batch=batch,primary=False,
                 source_path=target.relative_to(out).as_posix(),source_sha256=sha(target),assembly_path=ap.relative_to(out).as_posix(),
                 assembly_sha256=sha(ap),part_count=len(assembly['instances']),order_provenance=assembly['order_provenance'],
                 original_source=str(source_path or source_name),caption_sha256=hashlib.sha256(caption.encode()).hexdigest())
        if extra:row.update(extra)
        if assembly.get('reconstruction'):row['reconstruction']=assembly['reconstruction']
        staged.append(row);by_id[sid]=row;return row
    progress=Progress('Index BrickMore',len(curated))
    for n,r in enumerate(curated,1):
        mid=r['id'];paired=model_to_prompt.get(mid);caption=r.get('prompt','')
        record=display/r['records'] if r.get('records') else None
        paths={'raw':r.get('raw_glb') or r.get('glb'),'stitched':r.get('stitched_glb')}
        available={}
        for variant,relative in paths.items():
            ldr=(record/('model.ldr' if variant=='stitched' else 'raw_geometry.ldr')) if record else None
            if ldr and ldr.exists():path=ldr
            elif relative:path=display/relative
            else:continue
            row=add('BrickMore',mid,variant,caption,r['category'],r.get('level'),paired['prompt_id'] if paired else None,
                    paired['batch'] if paired else 'supplemental',source_path=path,
                    extra=dict(source_kind=r.get('source'),visual_review=r.get('visual_review'),postprocessed=variant=='stitched'))
            available[variant]=row
        if paired and mid==paired['model_ids'][0]:
            selected=available.get('stitched') or available.get('raw');assert selected,mid;selected['primary']=True
        progress.update(n,mid)
    summary_path=SOURCE/'BrickGPT原版_AB对照实验_20261109/ab_experiment_20261109/summary.jsonl'
    summaries=[json.loads(l) for l in summary_path.read_text(encoding='utf-8-sig').splitlines() if l.strip()]
    assert len(summaries)==114
    progress=Progress('Index BrickGPT',len(summaries))
    for n,report in enumerate(summaries,1):
        pr=prompts[report['prompt_id']];assert report['caption']==pr['prompt'],pr['prompt_id']
        path=summary_path.parent/report['part']/report['prompt_id']/'bricks.ldr'
        row=add('BrickGPT',pr['prompt_id'],'generated',pr['prompt'],pr['category'],pr['level'],pr['prompt_id'],report['part'],source_path=path,
                extra=dict(generation_stable=report.get('stable'),generation_regenerations=report.get('n_regenerations'),generation_world_dim=report.get('world_dim')))
        row['primary']=True;progress.update(n,pr['prompt_id'])
    for part,seq in batches.items():
        zp=SOURCE/'BrickGPT'/(part+'_ldr_57.zip')
        with zipfile.ZipFile(zp) as z:
            files=collections.defaultdict(list)
            for name in z.namelist():
                if name.lower().endswith('.ldr'):files[int(Path(name).name.split('-')[0])].append(name)
            assert len(files)==57
            for index,pr in enumerate(seq):
                assert len(files[index])==1
                name=files[index][0]
                row=add('BrickNet',pr['prompt_id'],'generated',pr['prompt'],pr['category'],pr['level'],pr['prompt_id'],part,
                    source_bytes=z.read(name),source_name=name,extra=dict(original_archive=str(zp),original_archive_sha256=sha(zp),
                    generation_policy='accepted parser/graph sample, no-collision generation; evaluate all supplied files without further filtering'))
                row['primary']=True
    primary=[r for r in staged if r['primary']]
    counts=collections.Counter(r['system'] for r in primary);assert counts=={'BrickMore':114,'BrickGPT':114,'BrickNet':114},counts
    for pr in prompts.values():
        matched=[r for r in primary if r['prompt_id']==pr['prompt_id']]
        assert len(matched)==3 and len({r['caption_sha256'] for r in matched})==1
    assets=out/'Assets';inset=assets/'inset';inset.mkdir(parents=True,exist_ok=True)
    archive=Path(r'D:\PythonEnvs\brickmore-paper\cache\bricknet-original\original-inset.tar.xz')
    missing={stem for stem in needed if not (inset/(stem+'.ply')).exists()};progress=Progress('Extract official colliders',len(missing))
    total=len(missing);done=0
    if missing:
        with tarfile.open(archive,mode='r|xz') as tar:
            for member in tar:
                stem=Path(member.name).stem
                if member.isfile() and stem in missing:
                    stream=tar.extractfile(member);(inset/(stem+'.ply')).write_bytes(stream.read());missing.remove(stem);done+=1;progress.update(done,stem)
                    if not missing:break
    if missing:raise ValueError(f'Missing official meshes: {sorted(missing)}')
    import meshlib.mrmeshpy as mm
    import meshlib.mrmeshnumpy as mn
    protos=assets/'render_meshes';protos.mkdir(exist_ok=True);parts={};progress=Progress('Build shared render meshes',len(needed))
    for n,stem in enumerate(sorted(needed),1):
        mesh=mm.loadMesh(str(inset/(stem+'.ply')));v=mn.getNumpyVerts(mesh).copy();f=mn.getNumpyFaces(mesh.topology).copy();v[:,2]*=-1
        target=protos/(stem+'.npz');np.savez_compressed(target,vertices=v.astype(np.float32),faces=f.astype(np.int32))
        parts[stem]=dict(part_id=catalog.stem_to_id[stem],vertices=len(v),faces=len(f),bounds=[v.min(0).tolist(),v.max(0).tolist()],
            collider_sha256=sha(inset/(stem+'.ply')),render_sha256=sha(target));progress.update(n,stem)
    bounds_differences=[]
    for sid,b in glb_bounds:
        actual=np.array([b['local_lo_ldu'],b['local_hi_ldu']]);reference=np.array(parts[b['part_stem']]['bounds']);difference=float(np.abs(actual-reference).max())
        if difference>.75:raise ValueError(f'Render/collider origin/scale mismatch {sid} {b["part_stem"]}: {difference} LDU')
        bounds_differences.append(difference)
    dump(assets/'catalog.json',dict(bricknet_version='0.1.0',parts=parts,source_archive_sha256=sha(archive),
        collider_policy='official 0.1.0 triangle meshes inset 0.25 LDU per surface; canonical Z flip',
        rendering_policy='same actual inset part meshes for all three systems, uniform yellow; adapted protocol, not original paper renderer'))
    write_rows(out/'Data/manifest.jsonl',staged);write_rows(out/'Data/primary_manifest.jsonl',primary)
    audit=dict(passed=True,source_root=str(SOURCE),total_records=len(staged),primary_records=len(primary),
        primary_counts=dict(counts),all_counts=dict(collections.Counter(r['system'] for r in staged)),matched_prompts=114,
        formal_groups=len({(r['category'],r['level']) for r in primary}),part_types=len(needed),
        legacy_adapter_crosschecked=bool(legacy),glb_mesh_bounds_checks=len(bounds_differences),
        procedural_glb_reconstructions=sum('reconstruction' in r for r in staged),
        maximum_render_collider_bounds_difference_ldu=max(bounds_differences,default=0),
        source_naming_note='BrickGPT/ A_ldr_57.zip and B_ldr_57.zip contain BrickNet; identified using accompanying generation report.',
        primary_policy='Fixed 114 A/B prompts. BrickMore first pre-existing model_ids entry, stitched if available, raw otherwise. No metric-based best-of-N.',
        supplemental_policy='Other displayed BrickMore candidates, raw/stitched counterparts, and ungraded car trials retained separately; duplicate delivery copies and unreferenced historical files excluded.',
        previous_server_data=dict(old_918='/mnt/brickmore-data/brickmore-jrd-20261025/BrickMore/Results/server_paper_full_20261026/',
            eval630='/mnt/brickmore-data/brickmore-jrd-20261025/uploads/eval630-20261027/BrickMoreEval630/Results/eval630_full_v2/',
            source='archived chat records only; no server connection or current verification',original_package='brickmore-eval630-four-scores-20261027.tar.gz'))
    dump(out/'Data/input_audit.json',audit)
    (out/'Provenance').mkdir(exist_ok=True)
    for file,label in [(curated_path,'brickmore_curated.json'),(SOURCE/'BrickGPT/总结_AB对照_20261109.md','bricknet_generation_summary.md'),(summary_path,'brickgpt_generation_summary.jsonl')]:shutil.copy2(file,out/'Provenance'/label)
    for part in ('A','B'):shutil.copy2(plan_dir/(part+'_57条_prompts.json'),out/'Provenance'/(part+'_prompts.json'))
    print(json.dumps(audit,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
