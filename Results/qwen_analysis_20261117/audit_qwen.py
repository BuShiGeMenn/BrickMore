import csv, hashlib, json, math, re, statistics as st, struct, zipfile
from collections import Counter, defaultdict
from pathlib import Path as P

root = P(r'D:\BrickMore\Qwen_Comparision\Results')
source = root/'Results/qwen_A_B'
work = P(r'D:\BrickMore\Results\qwen_analysis_20261117')
archive = work/'intake/Results'
deploy = P(r'D:\BrickMore\Deploy\build\qwen_AB_20261117\QwenComparison_20261117')
extra = work/'intake/BrickMore_A260_20261117'
base = extra/'Results/brickmore_A260'
metrics = ('pinv','vqa','pe','siglip2')
stages = {'structure':'structure.jsonl','render':'rendered/renders.jsonl',**{k:k+'.jsonl' for k in metrics[1:]}}
failures = []
tests = Counter()
checks = Counter()

def verify(ok, label, detail=None):
    tests[label] += 1
    if ok:
        checks[label] += 1
    else:
        failures.append([label,detail])

def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def csvs(p):
    with p.open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def digest(obj): return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
def close(x,y): return math.isclose(float(x),float(y),rel_tol=1e-10,abs_tol=1e-12)
def index(rows,key): return {r[key]:r for r in rows}
def without(d,*fields): return {k:v for k,v in d.items() if k not in fields}

local = root/'Results'
arc_paths = {p.relative_to(archive) for p in archive.rglob('*') if p.is_file()}
local_paths = {p.relative_to(local) for p in local.rglob('*') if p.is_file()}
verify(arc_paths==local_paths,'Local extracted file inventory', {'archive':len(arc_paths),'local':len(local_paths)})
for rel in sorted(arc_paths & local_paths):
    verify(sha(archive/rel)==sha(local/rel),'Local file SHA256 matches archive',rel.as_posix())
arc_file = P(r'G:\桌面\Results.rar')
arc_sha = sha(arc_file)
verify(arc_sha=='69e38826fa56b692f07d67af4924b06946b228e7937dfb9e6322d0c97879c6d4','Source archive SHA256')
manifest = rows(source/'selected_manifest.jsonl')
coverage = rows(deploy/'Data/prompt_coverage.jsonl')
cov_index = index(coverage,'prompt_id')
by_id = index(manifest,'sample_id')
ids = set(by_id)
prompts = index(manifest,'prompt_id')
verify(len(manifest)==len(ids)==len(prompts)==345,'Unique scoreable rows')
verify(len(coverage)==len(cov_index)==525,'Unique expected prompt rows')
verify(manifest==rows(deploy/'Data/manifest.jsonl'),'Deployed manifest equals server selection')
cfg_run = read(source/'run_config.json')
verify(cfg_run['bundle_manifest_sha256']==sha(deploy/'Data/manifest.jsonl'),'Deployed manifest SHA256')
verify(cfg_run['sample_ids']==list(by_id) and cfg_run['mode']=='full' and cfg_run['scope']=='all' and not cfg_run['cpu_only'] and not cfg_run['structure_only'],'Full run selection and mode')
verify({r['prompt_id'] for r in coverage if r['input_status'].startswith('scoreable_')}==set(prompts),'Eligible rows equal selected rows')
progress = read(source/'progress.json')
verify(progress['current_stage']=='finished' and set(progress['stages'])==set(stages),'Run finished and has all five stages')
times = {}
journals = {}
configs = {}
scorers = read(deploy/'Data/scoring_models.json')
for stage,loc in stages.items():
    stat = progress['stages'][stage]
    verify(stat['status']=='completed' and stat['exit_code']==0 and stat['done']==stat['total']==(2760 if stage=='render' else 345),'Stage completion',stage)
    times[stage] = round(stat['end']-stat['start'],3)
    path=source/loc
    cb=read(path.with_suffix('.config.json'))
    configs[stage] = without(cb,'signature')
    verify(digest(configs[stage])==cb['signature'],'Stage configuration signature',stage)
    batch=rows(path)
    idx=index(batch,'sample_id')
    verify(len(batch)==len(idx)==345 and set(idx)==ids,'Stage journal completeness',stage)
    verify(all(x['config_signature']==cb['signature'] for x in batch),'Stage journal uses one configuration',stage)
    if stage in metrics[1:]:
        verify(cb['preset']=='paper-text' and cb['samples']==345 and cb['view_evaluations']==2760 and cb['input_manifest_sha256']==sha(source/stages['render']),'Image metric protocol and render input hash',stage)
        verify(cb['resolved_model']['model'].endswith('/'+scorers[stage]['revision']),'Recorded scorer checkpoint',stage)
        for f,h in cb['sources'].items():
            verify(sha(deploy/'Scripts'/f)==h,'Scorer script SHA256',f)
    else:
        verify(cb['input_sha256']==sha(source/'selected_manifest.jsonl') and cb['catalog_sha256']==sha(deploy/'Assets/catalog.json'),'Geometry stage input/catalog SHA256',stage)
        verify(cb['source_sha256']==sha(deploy/'Scripts'/(stage+'.py')),'Geometry stage script SHA256',stage)
    journals[stage]=idx

verify(configs['render']==read(source/'rendered/render_protocol.json'),'Recorded render protocol')
measured = []
trunc = {k:[] for k in metrics[1:]}
images=set()
meshes=defaultdict(set)
for m in manifest:
    pid,sid=m['prompt_id'],m['sample_id']
    c,r,s=cov_index[pid],journals['render'][sid],journals['structure'][sid]
    verify(all(c[k]==m[k] for k in ('prompt_id','sample_id','batch','level','category','caption','system'))
        and hashlib.sha256(m['caption'].encode()).hexdigest()==m['caption_sha256'],'Prompt metadata and caption SHA256',pid)
    verify(m['source_sha256']==sha(deploy/m['source_path']) and m['assembly_sha256']==sha(deploy/m['assembly_path']),'Source LDR and assembly hashes',pid)
    instances = read(deploy/m['assembly_path'])['instances']
    verify(len(instances)==m['part_count'],'Assembly parts count',pid)
    meshes[m['batch']].update(x['part_stem'] for x in instances)
    geo = digest(sorted((x['part_stem'],tuple(v for row in x['matrix_ldu'] for v in row)) for x in instances))
    n,inv = s['n_actions'],s['invalid_placements']
    verify(s['status']=='ok' and n==m['part_count'] and n>0 and inv==len(s['collisions'])==len(set(s['collisions'])) and all(x in range(n) for x in s['collisions']) and close(s['pinv'],inv/n),'Structure status/count/P_inv consistency',pid)
    verify(s['metric']=='pinv_file_order' and not s['original_generation_order_verified'] and not s['fixed_edge_exemptions'] and not s['missing_colliders_are_zero'] and s['input_sha256']==digest({'assembly':m['assembly_sha256'],'source':m['source_sha256']}),'Structure protocol and input hash',pid)
    verify(all(r.get(k)==v for k,v in m.items()) and r['render_protocol']==configs['render'] and r['input_sha256']==digest({'assembly':m['assembly_sha256'],'config':configs['render']}),'Render metadata and input hash',pid)
    verify(len(r['view_paths'])==len(r['view_sha256'])==8,'Eight fixed views per row',pid)
    for loc, expected in zip(r['view_paths'],r['view_sha256']):
        path = (source/'rendered'/loc).resolve()
        verify(path.is_relative_to((source/'rendered/views').resolve()),'Safe view path',loc)
        data=path.read_bytes()
        verify(hashlib.sha256(data).hexdigest()==expected and data[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',data[16:24])==(512,512),'PNG SHA256, format and size',loc)
        images.add(path)
    fingerprint = digest({'row':r,'actual_view_sha256':r['view_sha256']})
    row = {**m,'pinv':s['pinv'],'invalid_placements':inv,'image_group':tuple(r['view_sha256']),'geometry_group':geo,'rep_image_paths':r['view_paths']}
    for k in metrics[1:]:
        rec = journals[k][sid]
        vals=rec['scores']
        verify(rec['status']=='ok' and len(vals)==len(rec['diagnostics'])==8 and all(math.isfinite(x) and (-1 if k=='pe' else 0)<=x<=1 for x in vals),'Eight valid scores in nominal range',[pid,k])
        verify(close(max(vals),rec['max_score']) and vals[rec['best_view']]==max(vals) and close(st.mean(vals),rec['mean_score']),'View pooling and winning angle',[pid,k])
        verify(rec['input_sha256']==fingerprint and all(rec.get(kk)==vv for kk,vv in r.items() if kk not in ('input_sha256','config_signature')),'Scorer paired with actual image bytes and prompt',[pid,k])
        row[k]=rec['max_score']
        row[k+'_view_mean']=rec['mean_score']
        if any(d.get('text_truncated') for d in rec['diagnostics']):
            trunc[k].append({'prompt_id':pid,'batch':m['batch'],'level':m['level'],'text_tokens':max(d.get('text_tokens',0) for d in rec['diagnostics'])})
    measured.append(row)

verify(len(images)==2760 and images=={p.resolve() for p in (source/'rendered/views').rglob('*.png')},'Exactly 2760 unique render file paths')
metric_by_pid=index(measured,'prompt_id')
scores=csvs(source/'report/scores.csv')
csv_cover=csvs(source/'report/coverage_and_scores.csv')
verify(len(scores)==345 and set(index(scores,'sample_id'))==ids,'Scores CSV row coverage')
verify(len(csv_cover)==525 and set(index(csv_cover,'prompt_id'))==set(cov_index),'Coverage CSV prompt inventory')
for s in scores:
    m=metric_by_pid[s['prompt_id']]
    verify(all(s[k]==m[k] for k in ('sample_id','caption','system','batch','category')) and int(s['level'])==m['level']
        and int(s['part_count'])==m['part_count'] and int(s['invalid_placements'])==m['invalid_placements'] and s['structure_status']=='ok'
        and all(close(s[k],m[k]) for k in metrics),'Scores CSV reconciles with four journals',s['prompt_id'])
for r in csv_cover:
    pid=r['prompt_id']
    c=cov_index[pid]
    m=metric_by_pid.get(pid)
    verify(all(str(c[k])==r[k] for k in c) and r['selected_for_run']==str(m is not None)
        and all(close(r[k],m[k]) if m else r[k]=='' for k in metrics),'Coverage CSV joins correctly; missing rows blank',pid)

def summarize(a):
    n = len(a)
    parts = sum(r['part_count'] for r in a)
    inv = sum(r['invalid_placements'] for r in a)
    z = {'n':n,'parts':parts,'invalid':inv,'no_collision':sum(r['pinv']==0 for r in a),
        'pinv_micro': inv/parts if parts else None, 'parts_mean': parts/n if n else None,
        'parts_median':st.median(r['part_count'] for r in a) if n else None}
    for k in metrics:
        v=[r[k] for r in a]
        q=st.quantiles(v,n=4,method='inclusive') if n>1 else v*3
        z[k]={'mean':st.mean(v),'median':st.median(v),'q1':q[0],'q3':q[2],'min':min(v),'max':max(v)} if v else {}
    return z

def with_coverage(a,c):
    return {**summarize(a),'expected':len(c),'input_status':dict(Counter(r['input_status'] for r in c))}

def group_rollup(a,key):
    g=defaultdict(list)
    for r in a: g[r[key]].append(r)
    clusters=sorted(g.values(),key=lambda x:(-len(x),x[0]['prompt_id']))
    return {'unique':len(g),'repeated_samples':sum(len(x) for x in clusters if len(x)>1),
        'clusters':[{'size':len(x),'representative':x[0]['prompt_id'],'part_counts':dict(Counter(y['part_count'] for y in x)),
            'categories':sorted({y['category'] for y in x}),'levels':dict(sorted(Counter(y['level'] for y in x).items())),
            'pins':sorted({y['pinv'] for y in x}), 'prompt_ids':[y['prompt_id'] for y in x],
            'source_examples':[{'prompt_id':y['prompt_id'],'category':y['category'],'caption':y['caption']} for y in x[:5]],
            **({'representative_view_paths':x[0]['rep_image_paths']} if key=='image_group' else {})}
            for x in clusters]}

orig=read(source/'report/summary.json')
verify(orig['samples']==len(measured),'Server summary scored count')
smoke = read(local/'comparison_smoke/report/summary.json')
verify(smoke['samples']==len(rows(local/'comparison_smoke/selected_manifest.jsonl'))==3,'Smoke batch separate')
batch_summary={}
for b in 'AB':
    a=[r for r in measured if r['batch']==b]
    c=[r for r in coverage if r['batch']==b]
    sg=with_coverage(a,c)
    bsum=orig['by_batch'][b]
    sys_summary = next(iter(bsum['systems'].values()))
    verify(sg['expected']==bsum['expected_prompts'] and sg['n']==bsum['selected_prompts']==sys_summary['records'] and sg['input_status']==orig['source_input_coverage'][b], 'Batch counts and statuses match server',b)
    verify(close(sg['pinv_micro'],sys_summary['pinv_micro']) and all(sys_summary[k]['n']==sg['n'] and sys_summary[k]['missing']==0 and close(sys_summary[k]['mean'],sg[k]['mean']) for k in metrics),'Batch metrics match server summary',b)
    sg.update(levels={l:with_coverage([r for r in a if r['level']==l],[r for r in c if r['level']==l]) for l in range(1,6)},
        categories={l:with_coverage([r for r in a if r['category']==l],[r for r in c if r['category']==l]) for l in sorted({r['category'] for r in c})},
        render_groups=group_rollup(a,'image_group'), geometry_groups=group_rollup(a,'geometry_group'),
        parts_distribution=dict(sorted(Counter(r['part_count'] for r in a).items())),
        truncated={k:dict(sorted(Counter(r['level'] for r in trunc[k] if r['batch']==b).items())) for k in trunc},
        score_maxima={k:{'prompt_id':(row:=max(a,key=lambda r:r[k]))['prompt_id'],'score':row[k]} for k in metrics[1:]},
        max_view_minus_mean={k:st.mean(r[k]-r[k+'_view_mean'] for r in a) for k in metrics[1:]},
        sample_files_having_unsupported_parts=[{'prompt_id':r['prompt_id'],'reason':r['input_reason']} for r in c if r['input_status']=='unsupported_part'])
    sg['ineligible_records']=[{'prompt_id':r['prompt_id'],'level':r['level'],'category':r['category'],'reason':r['input_reason'],'status':r['input_status']} for r in c if r['prompt_id'] not in metric_by_pid]
    sg['score_top_one_share']={k:max(r[k] for r in a)/sum(r[k] for r in a) for k in ('vqa','siglip2')}
    for cluster in sg['render_groups']['clusters']:
        examples = {}
        for p in cluster['prompt_ids']:
            item=metric_by_pid[p]
            examples.setdefault(item['category'],{'prompt_id':p,'category':item['category'],'caption':item['caption']})
        cluster['examples_in_distinct_categories']=list(examples.values())
    batch_summary[b]=sg

# Supplement: use the previously scored BrickMore A archive only for matched A inputs.
basem=rows(base/'selected_manifest.jsonl')
baseidx=index(basem,'prompt_id')
basecov={c['prompt_id']:c for c in coverage if c['batch']=='A'}
verify(len(basem)==len(baseidx)==260 and set(baseidx)==set(basecov) and basem==rows(extra/'Data/manifest.jsonl') and sha(extra/'Data/manifest.jsonl')==read(base/'run_config.json')['bundle_manifest_sha256'],'Supplement BrickMore manifest coverage/provenance')
verify(all(m['system']=='BrickMore' and m['source_kind']=='raw_model_output' and type(m['geometry_valid']) is bool and m['glb_coverage'] in ('full','matching_prefix') and all(m[k]==basecov[p][k] for k in ('caption','category','level','batch')) for p,m in baseidx.items()),'Supplement BrickMore matches A prompts and records validation/export provenance')
verify(read(extra/'Data/scoring_models.json')==scorers,'Supplement uses same scorer revisions')
for stage,path in stages.items():
    bc=read((base/path).with_suffix('.config.json'))
    verify(digest(without(bc,'signature'))==bc['signature'],'Supplement stage configuration signature',stage)
    ignore=('input_sha256','signature','input_manifest_sha256','samples','view_evaluations','catalog_sha256')
    verify(without(bc,*ignore)==without(configs[stage],*ignore),'Supplement protocol and scorer resolution match',stage)
    if stage in ('structure','render'):
        verify(bc['catalog_sha256']==sha(extra/'Assets/catalog.json'),'Supplement catalog SHA256',stage)
acat=read(deploy/'Assets/catalog.json')
bcat=read(extra/'Assets/catalog.json')
shared=set(acat['parts']) & set(bcat['parts'])
verify(len(shared)==len(bcat['parts']) and all(acat['parts'][k]==bcat['parts'][k] for k in shared)
    and without(acat,'parts')==without(bcat,'parts'),'Supplement shared part colliders and render meshes match')
bs=csvs(base/'report/scores.csv')
bss=index(bs,'prompt_id')
br=read(base/'report/summary.json')
verify(len(bs)==len(bss)==br['samples']==260 and set(bss)==set(baseidx),'Supplement scores table coverage')
bsj=index(rows(base/'structure.jsonl'),'sample_id')
base_img=index(rows(base/'rendered/renders.jsonl'),'sample_id')
base_metric={k:index(rows(base/(k+'.jsonl')),'sample_id') for k in metrics[1:]}
bid={m['sample_id'] for m in basem}
verify(all(set(t)==bid for t in (bsj,base_img,*base_metric.values())), 'Supplement stage journal coverage')
for k in metrics[1:]:
    verify(read(base/(k+'.config.json'))['input_manifest_sha256']==sha(base/'rendered/renders.jsonl'),'Supplement image scorer input manifest hash',k)
base_scores={}
for k,r in bss.items():
    m=baseidx[k]
    s=bsj[r['sample_id']]
    verify(all(r[h]==m[h] for h in ('system','sample_id','caption','category','batch')) and int(r['level'])==m['level'] and int(r['part_count'])==m['part_count']
        and r['structure_status']==s['status']=='ok' and int(r['invalid_placements'])==s['invalid_placements'] and close(r['pinv'],s['pinv']) and s['n_actions']==int(r['part_count']),'Supplement scores metadata and structural results',k)
    rr=base_img[r['sample_id']]
    fp=digest({'row':rr,'actual_view_sha256':rr['view_sha256']})
    verify(all(rr[h]==m[h] for h in m) and len(rr['view_sha256'])==8,'Supplement render metadata',k)
    for score_metric, table in base_metric.items():
        rec=table[r['sample_id']]
        verify(rec['status']=='ok' and rec['input_sha256']==fp and rec['caption']==m['caption'] and rec['view_sha256']==rr['view_sha256'] and len(rec['scores'])==8
               and all(math.isfinite(x) and (-1 if score_metric=='pe' else 0)<=x<=1 for x in rec['scores'])
               and close(max(rec['scores']),rec['max_score']) and close(r[score_metric],rec['max_score']),'Supplement semantic scores reconcile',[k,score_metric])
    base_scores[k]={**m,'invalid_placements':int(r['invalid_placements']),**{m0:float(r[m0]) for m0 in metrics}}
only_a=[r for r in measured if r['batch']=='A']
base_common=[base_scores[r['prompt_id']] for r in only_a]
base_all=list(base_scores.values())
baseall_stats=summarize(base_all)
verify(close(baseall_stats['pinv_micro'],br['primary']['BrickMore']['pinv_micro']) and all(close(baseall_stats[k]['mean'],br['primary']['BrickMore'][k]['mean']) for k in metrics),'Supplement BrickMore table matches its full server summary')
bcs=summarize(base_common)
comparison = {'archive':str(P(r'G:\桌面\BrickMore_A260_20261117.rar')),
    'sha256':sha(P(r'G:\桌面\BrickMore_A260_20261117.rar')),
    'archive_member_prefix':'BrickMore_A260_20261117/Results/brickmore_A260',
    'match_key':['batch','prompt_id','category','level','caption'],
    'matched_prompts':len(only_a),'excluded_qwen_prompts':180,'brickmore_all':baseall_stats,'brickmore_matched':bcs,
    'brickmore_order':dict(Counter(r['order_provenance'] for r in base_common)),
    'qwen_order':dict(Counter(r['order_provenance'] for r in only_a)),
    'brickmore_semantic_wins':{k:sum(b[k]>q[k] for q,b in zip(only_a,base_common)) for k in metrics[1:]},
    'ties':{k:sum(b[k]==q[k] for q,b in zip(only_a,base_common)) for k in metrics},
    'brickmore_lower_pinv':sum(b['pinv']<q['pinv'] for q,b in zip(only_a,base_common)),
    'paired_deltas_brickmore_minus_qwen':{k:st.mean(b[k]-q[k] for q,b in zip(only_a,base_common)) for k in metrics},
    'brickmore_upstream_geometry_valid':{'all':sum(r['geometry_valid'] for r in base_all),'matched':sum(r['geometry_valid'] for r in base_common)},
    'brickmore_export_coverage':{'all':dict(Counter(r['glb_coverage'] for r in base_all)),'matched':dict(Counter(r['glb_coverage'] for r in base_common))},
    'catalog_common_parts':len(shared),
    'catalog_qwen_total_parts':len(acat['parts']),'catalog_brickmore_total_parts':len(bcat['parts'])}

upstream_a=P(r'D:\BrickMore\Qwen_Comparision\base_qwen_A260_results.zip')
upstream_a_sha=sha(upstream_a)
verify(upstream_a_sha==sha(deploy/'Provenance/base_qwen_A260_results.zip'),'Original A generation report archive matches deploy provenance')
with zipfile.ZipFile(upstream_a) as z:
    ur=[json.loads(z.read(p).decode('utf-8-sig')) for p in z.namelist() if re.fullmatch(r'.*/results/A[0-9]+_L[1-5]/report[.]json',p)]
def canonical_a_pid(r):
    a,l=r['prompt_id'].split('_')
    return f'A{int(a[1:]):02d}_{l}'
upstream_reports={canonical_a_pid(r):r for r in ur}
verify(len(upstream_reports)==len(ur)==260 and set(upstream_reports)==set(basecov),'Original A generation reports cover all 260 original prompts')
verify(all(r['geometry_valid'] is False and type(r['completed']) is bool and r['model']=='Qwen/Qwen3-1.7B (base, no fine-tune)' and r['prompt']==basecov[pid]['caption']
           and r['brick_count']==basecov[pid]['reported_or_ldr_bricks'] for pid,r in upstream_reports.items()),'Original A report geometry rejection/provenance matches coverage')
qwen_meta={'A':{'generator': 'Qwen/Qwen3-1.7B (base)', 'selected_output_type':'parsed_partial',
    'upstream_geometry_valid_true':sum(r['geometry_valid'] for r in ur),
    'upstream_completed':sum(r['completed'] for r in ur),
    'selected_upstream_completed':sum(r['completed'] for p,r in upstream_reports.items() if p in prompts),
    'upstream_incomplete_statuses':dict(Counter(basecov[p]['input_status'] for p,r in upstream_reports.items() if not r['completed'])),
    'upstream_report_archive':str(upstream_a),'upstream_archive_sha256':upstream_a_sha},
    'B':{'generator': 'Qwen1.7b.zip', 'selected_output_type':'delivered_ldr',
         'recorded_nonempty_checkpoints':sorted({r['checkpoint_in_ldr'] for r in measured if r['batch']=='B' and r['checkpoint_in_ldr']})}}
verify(set(r['source_index'] for r in measured if r['batch']=='B')==set(range(265)) and all(r['source_index']==r['ordinal']-1 for r in measured if r['batch']=='B'),'B delivered LDR indexes align to prompt file order')
report={'format_version':1,'source_archive':str(arc_file),'source_archive_sha256':arc_sha,'source_run':str(source),
    'extracted_files':len(arc_paths),'full_run':{'expected':len(coverage),'scored':len(measured),'images':len(images),'per_view_semantic_scores':len(images)*3,
        'stages_elapsed_s':times,'total_elapsed_s':round(progress['finished']-progress['started'],3),'smoke_count_excluded':3},
    'qa':{'status':'PASS' if not failures else 'FAIL','checks_passed':sum(checks.values()),'checks_total':sum(tests.values()),
        'test_count_by_name':dict(tests),'failure_count':len(failures),'failures':failures},
    'run_protocol':orig['protocol'],'scorers':{**scorers,'text_context_length':{k:read(source/(k+'.model.json'))['text_context_length'] for k in ('pe','siglip2')}},
    'generator_identity':qwen_meta,'groups':batch_summary,'truncation_diagnostics':trunc,'supplement_brickmore_A':comparison,
    'assemblies_mesh_usage':{k:sorted(v) for k,v in meshes.items()}}
target = work/'analysis_work.json'
target.write_text(json.dumps(report,ensure_ascii=False,allow_nan=False,indent=2)+'\n',encoding='utf-8')
print('QA',report['qa']['status'],sum(checks.values()),sum(tests.values()),failures[:12])
for b,g in batch_summary.items():
    print(b,{k:g[k] for k in ('n','expected','parts','invalid','no_collision','parts_mean','parts_median','truncated')})
    print('groups',[(k,g[k]['unique'],g[k]['repeated_samples']) for k in ('render_groups','geometry_groups')])
    print('levels',[(l,s['n'],*[round(s[k].get('mean',0),6) for k in metrics]) for l,s in g['levels'].items()])
    print('dist',[(k,*[round(g[k][s],6) for s in ('mean','median','max')]) for k in metrics])
print('BrickMore',bcs,comparison['brickmore_semantic_wins'],comparison['brickmore_lower_pinv'],comparison['ties'])

