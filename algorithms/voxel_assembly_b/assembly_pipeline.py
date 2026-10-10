"""Exact-grid LEGO assembly of the B shard, with independent exported-file audits.

The sealed voxel dataset is read-only. Failure drafts never become successes.
No force solver, generated geometry repair, recoloring, or virtual ground union.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random
import shutil
import sys
import time

HERE = Path(__file__).resolve().parent
DEFAULT_DATASET = HERE.parent / 'voxel_B_20261010'
ORIGINAL_TOOLKIT = HERE.parent / 'brick_assembly_toolkit'
TOOLKIT_FILES = ('optimized_geometry.py', 'brick_catalog.py', 'voxel_io.py',
                 'interlocking.py', 'voxel_assembly.py')
SNAPSHOT = HERE / 'toolkit_snapshot'
sys.path.insert(0, str(SNAPSHOT if SNAPSHOT.exists() else ORIGINAL_TOOLKIT))
from optimized_geometry import GeometryConfig, GeometryState, Placement
from voxel_io import VoxelModel
from voxel_assembly import assemble, candidate_tiles, to_ldr
from interlocking import layout_metrics
from brick_catalog import EXTENDED_PARTS, dimensions_for_library

VERSION = 'B_exact_grid_assembly_v2'
_DATASET = None
_RUN = None
_POLICY = None


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(Path(path).read_bytes())


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')
    temp.replace(path)


def exact_hash(cells):
    return sha(';'.join(','.join(map(str, p)) for p in sorted(cells)).encode('utf8'))


def dataset_model(value):
    """Explicit Y-up -> Z-up and RGB triplet adapter; reject rather than clean."""
    cells = {}
    original = {}
    for voxel in value['voxels']:
        p = tuple(voxel[k] for k in ('x', 'y', 'z'))
        rgb = voxel['color']
        if any(type(v) is not int or not 0 <= v < 48 for v in p):
            raise ValueError('non_integer_or_out_of_bounds_coordinate')
        if not isinstance(rgb, list) or len(rgb) != 3 or any(
                type(v) is not int or not 0 <= v <= 255 for v in rgb):
            raise ValueError('invalid_rgb_triplet')
        if p in original:
            raise ValueError('duplicate_source_coordinate')
        color = (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]
        original[p] = color
        cells[(p[0], p[2], p[1])] = color
    if not cells or min(p[2] for p in cells) != 0:
        raise ValueError('missing_ground_contact')
    if value.get('actualVoxelCount', len(cells)) != len(cells):
        raise ValueError('source_count_mismatch')
    return VoxelModel(cells, {'source_up_axis': 'y', 'internal_up_axis': 'z',
                             'axis_transform': '[x,y,z] -> [x,z,y]',
                             'origin_shift_xyz': [0, 0, 0],
                             'source_model_id': value.get('modelId')}), original


def feasibility(model, cfg):
    """Necessary conditions, independent of the bounded tiling search.

    This graph OVER-approximates possible brick connections. Horizontal edges
    exist only within same-color potential bricks; vertical studs may mix color.
    A disconnected graph certifies impossibility only for this rectangular,
    single-height, monochrome brick library with vertical stud connections.
    """
    cells = model.cells
    remaining = set(cells)
    groups = []
    while remaining:
        start = min(remaining)
        remaining.remove(start)
        stack = [start]
        size = 0
        while stack:
            p = stack.pop()
            size += 1
            for dx, dy, dz in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
                q = (p[0]+dx, p[1]+dy, p[2]+dz)
                if q in remaining and (dz or cells[p] == cells[q]):
                    remaining.remove(q)
                    stack.append(q)
        groups.append({'voxelCount': size, 'witnessInternalXYZ': list(start)})
    result = {'necessaryConnectionGraphComponents': len(groups),
              'componentWitnesses': groups, 'unsupportedVoxelWitnesses': [],
              'scope': 'selected monochrome rectangular unit-height stud library and bottom-up policy'}
    if len(groups) != 1:
        result.update(passed=False, reason='disconnected_possible_stud_graph')
        return result
    # With previous layers completely covered, every target cell must admit
    # SOME supported same-color rectangle. Search choices cannot improve this.
    for p in sorted(cells):
        x, y, z = p
        if z == 0 or (x, y, z-1) in cells:
            continue
        possible = False
        for h, w in cfg.dimensions:
            if possible:
                break
            for dx in range(h):
                if possible:
                    break
                for dy in range(w):
                    b = Placement(h, w, x-dx, y-dy, z)
                    footprint = tuple(b.cells())
                    if not all(q in cells and cells[q] == cells[p] for q in footprint):
                        continue
                    supports = [(q[0], q[1]) for q in footprint if (q[0],q[1],z-1) in cells]
                    if not supports or len(supports)/(h*w) < cfg.min_support_fraction:
                        continue
                    if cfg.max_cantilever_distance is not None:
                        distance = max(min(abs(q[0]-a)+abs(q[1]-b) for a,b in supports) for q in footprint)
                        if distance > cfg.max_cantilever_distance:
                            continue
                    possible = True
                    break
        if not possible:
            result['unsupportedVoxelWitnesses'].append(list(p))
            # A single witness proves the necessary condition fails.
            break
    result.update(passed=not result['unsupportedVoxelWitnesses'],
                  reason='necessary_conditions_passed' if not result['unsupportedVoxelWitnesses']
                  else 'no_supported_same_color_brick_for_voxel')
    return result


def independent_audit(raw_bricks, target, policy):
    """Reconstruct cells and a separate DSU, without GeometryState or flags."""
    issues = []
    occupied = {}
    parent = []
    ground = []
    support_fractions = []
    distances = []
    last_z = 0
    dimensions = set(dimensions_for_library(policy['brick_library']))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, b in enumerate(raw_bricks):
        keys = ('h','w','x','y','z','color')
        if any(type(b.get(k)) is not int for k in keys):
            issues.append(f'brick_{i}:invalid_integer_fields')
            continue
        h,w,x,y,z,c = (b[k] for k in keys)
        if (h,w) not in dimensions or not 0 <= c <= 0xFFFFFF:
            issues.append(f'brick_{i}:invalid_library_or_color')
            continue
        if not (0 <= x <= policy['world_dim']-h and 0 <= y <= policy['world_dim']-w
                and 0 <= z < policy['world_dim']):
            issues.append(f'brick_{i}:out_of_bounds')
            continue
        positions = [(a,b,z) for a in range(x,x+h) for b in range(y,y+w)]
        if any(p in occupied for p in positions):
            issues.append(f'brick_{i}:collision')
            continue
        if z < last_z or z > last_z+1:
            issues.append(f'brick_{i}:layer_order_or_jump')
        last_z = z
        lower = [(p[0],p[1]) for p in positions if (p[0],p[1],z-1) in occupied]
        fraction = len(lower)/(h*w) if z else 1.0
        distance = max(min(abs(p[0]-a)+abs(p[1]-b) for a,b in lower) for p in positions) if lower else (0 if z==0 else None)
        support_fractions.append(fraction)
        distances.append(distance)
        if z and (not lower or fraction < policy['min_support_fraction']):
            issues.append(f'brick_{i}:lower_support')
        if z and policy['max_cantilever_distance'] is not None and (
                distance is None or distance > policy['max_cantilever_distance']):
            issues.append(f'brick_{i}:cantilever')
        index = len(parent)
        parent.append(index)
        ground.append(z == 0)
        contacts = {occupied[q][0] for p in positions
                    for q in ((p[0],p[1],z-1),(p[0],p[1],z+1)) if q in occupied}
        for j in contacts:
            parent[find(j)] = find(index)
        if len({find(j) for j in range(len(parent))}) > policy['max_components']:
            issues.append(f'brick_{i}:prefix_component_budget')
        for p in positions:
            occupied[p] = (index,c)
    output = {p:v[1] for p,v in occupied.items()}
    missing = set(target)-set(output)
    added = set(output)-set(target)
    recolored = [p for p in set(output)&set(target) if output[p] != target[p]]
    roots = {find(j) for j in range(len(parent))}
    grounded_roots = {find(j) for j in range(len(parent)) if ground[j]}
    if len(roots) != 1:
        issues.append('multiple_or_zero_stud_components')
    if not roots or roots != grounded_roots:
        issues.append('not_ground_reachable')
    if missing or added or recolored:
        issues.append('shape_or_color_mismatch')
    # Source coordinates are Y-up, independent of the toolkit's input hash.
    source_cells = {(x,z,y):c for (x,y,z),c in target.items()}
    output_cells = {(x,z,y):c for (x,y,z),c in output.items()}
    return {'passed': not issues, 'issues': issues, 'brickCount': len(raw_bricks),
            'studComponentCount': len(roots), 'groundReachable': bool(roots) and roots == grounded_roots,
            'inputVoxelCount': len(target), 'outputVoxelCount': len(output),
            'missingVoxelCount': len(missing), 'addedVoxelCount': len(added),
            'recoloredVoxelCount': len(recolored), 'exactCoverage': not missing and not added,
            'colorPreserved': not recolored, 'minimumPrefixSupportFraction': min(support_fractions, default=0),
            'maximumCantileverDistance': max((d for d in distances if d is not None), default=0),
            'sourceExactOccupancyHash': exact_hash(source_cells),
            'assembledExactOccupancyHash': exact_hash(output_cells),
            'staticVerified': None, 'fullPhysics': False, 'semanticVerified': False}


def parse_ldr(text):
    reverse = {part:dims for dims,part in EXTENDED_PARTS.items()}
    out = []
    for line in text.splitlines():
        fields = line.split()
        if not fields or fields[0] == '0':
            continue
        if len(fields) != 15 or fields[0] != '1' or fields[-1] not in reverse:
            raise ValueError('unsupported_or_malformed_ldr_record')
        if len(fields[1]) != 9 or not fields[1].startswith('0x2'):
            raise ValueError('expected_direct_rgb_ldr_color')
        c = int(fields[1][3:],16)
        matrix = tuple(float(v) for v in fields[5:14])
        small, large = reverse[fields[-1]]
        if matrix == (0,0,1,0,1,0,-1,0,0):
            h,w = small,large
        elif matrix == (-1,0,0,0,1,0,0,0,-1):
            h,w = large,small
        else:
            raise ValueError('unexpected_ldr_orientation')
        coords = (float(fields[2])/20-h/2, float(fields[4])/20-w/2, -float(fields[3])/24)
        if any(not v.is_integer() for v in coords):
            raise ValueError('off_grid_ldr_translation')
        out.append(dict(h=h,w=w,x=int(coords[0]),y=int(coords[1]),z=int(coords[2]),color=c))
    return out


def exported_audit(folder, source, policy):
    """Actual disk readback of assembly JSON, TXT, LDR, and original voxels."""
    value = json.loads((Path(folder)/'assembly.json').read_text(encoding='utf8'))
    raw = value['bricks']
    suffix = '' if value['status']=='success' else '.draft'
    txt = [Placement.parse(line) for line in (Path(folder)/f'model{suffix}.txt').read_text(encoding='utf8').splitlines() if line.strip()]
    ldr = parse_ldr((Path(folder)/f'model{suffix}.ldr').read_text(encoding='utf8'))
    geometry_keys = ('h','w','x','y','z')
    json_geometry = [tuple(b[k] for k in geometry_keys) for b in raw]
    txt_equal = [tuple(getattr(b,k) for k in geometry_keys) for b in txt] == json_geometry
    ldr_equal = ldr == raw
    model,original = dataset_model(source)
    result = independent_audit(raw, model.cells, policy)
    result.update(txtReadbackMatches=txt_equal, ldrReadbackMatches=ldr_equal,
                  sourceModelId=source['modelId'], sourceCanonicalGeometryHash=source.get('canonicalGeometryHash'),
                  canonicalPreservedByExactCoordinateEquality=result['exactCoverage'],
                  readbackPerformed=True)
    if not txt_equal or not ldr_equal:
        result['passed'] = False
        result['issues'].append('export_readback_mismatch')
    return result


def greedy(model, cfg, seed, max_seconds=3):
    """One exact candidate path; every brick uses existing checked placement."""
    state = GeometryState(cfg)
    remaining = set(model.cells)
    rng = random.Random(seed)
    stats = Counter()
    deadline = time.monotonic()+max_seconds
    while remaining:
        if time.monotonic() >= deadline:
            stats['time_budget'] += 1
            break
        choices = candidate_tiles(state, remaining, model.cells, rng, 6, stats)
        if not choices:
            break
        _,brick,cells = choices[0]
        state.add(brick)
        remaining.difference_update(cells)
    raw = [{**asdict(b), 'color':model.cells[(b.x,b.y,b.z)]} for b in state.bricks]
    return raw, {'candidateStats':dict(stats),'layoutQuality':layout_metrics(state),
                 'remainingVoxels':len(remaining)}


def initialize(dataset, run, policy):
    global _DATASET, _RUN, _POLICY
    _DATASET, _RUN, _POLICY = Path(dataset), Path(run), policy


def process(job):
    start = time.monotonic()
    model_id = job['modelId']
    folder = _RUN/'models'/job['category']/model_id
    source_path = _DATASET/job['modelPath']/'model.json'
    source_bytes = source_path.read_bytes()
    source_sha = sha(source_bytes)
    report_path = folder/'report.json'
    if report_path.exists():
        old = json.loads(report_path.read_text(encoding='utf8'))
        if old['sourceFileSha256'] != source_sha:
            raise ValueError(f'input changed since checkpoint: {model_id}')
        if all(file_sha(folder/name) == digest for name,digest in old['outputFileSha256'].items()):
            return old
        raise ValueError(f'checkpoint output changed: {model_id}; use a new run directory')
    source = json.loads(source_bytes)
    model,original = dataset_model(source)
    if exact_hash(original) != job['exactOccupancyHash']:
        raise ValueError(f'manifest exact hash mismatch: {model_id}')
    cfg = GeometryConfig(world_dim=48,min_bricks=1,brick_library=_POLICY['brick_library'],
                         min_support_fraction=_POLICY['min_support_fraction'],
                         max_components=_POLICY['max_components'],
                         max_cantilever_distance=_POLICY['max_cantilever_distance'])
    necessary = feasibility(model,cfg)
    raw = []
    search = {}
    if necessary['passed']:
        raw,search = greedy(model,cfg,job['modelSeed'],_POLICY['max_seconds'])
        check = independent_audit(raw,model.cells,_POLICY)
        if not check['passed']:
            fallback = assemble(model,cfg,max_nodes=_POLICY['max_nodes'],beam_width=_POLICY['beam_width'],
                                seed=job['modelSeed'],solution_limit=1,improve_nodes=0,
                                max_seconds=_POLICY['max_seconds'])
            trial = [{**b,'color':model.cells[(b['x'],b['y'],b['z'])]} for b in fallback['bricks']]
            trial_check = independent_audit(trial,model.cells,_POLICY)
            if trial_check['passed'] or trial_check['outputVoxelCount'] > check['outputVoxelCount']:
                raw = trial
            search['fallback'] = {k:v for k,v in fallback.items() if k not in ('bricks','metadata')}
    check = independent_audit(raw,model.cells,_POLICY)
    status = 'success' if check['passed'] else ('infeasible_under_selected_policy' if not necessary['passed'] else 'search_failed')
    # to_ldr accepts only geometry fields, and looks up exact source colors.
    toolkit_result = {'status':'success' if status=='success' else 'draft',
                      'bricks':[{k:b[k] for k in ('h','w','x','y','z')} for b in raw]}
    value = {'algorithmVersion':VERSION,'modelId':model_id,'category':job['category'],
             'status':toolkit_result['status'], 'assemblyOutcome':status,
             'coordinateSystem':{'internalUpAxis':'z','sourceUpAxis':'y',
                                 'sourceToInternal':'[x,y,z] -> [x,z,y]',
                                 'horizontalUnit':'1 stud','verticalUnit':'1 standard brick height',
                                 'ldrUnitScales':[20,20,24],
                                 'physicalAspectRatioDiffersFromIsotropicVoxelPreview':True},
             'bricks':raw,'policy':_POLICY,'staticVerified':None,'fullPhysics':False}
    folder.mkdir(parents=True,exist_ok=True)
    dump(folder/'assembly.json',value)
    suffix = '' if status=='success' else '.draft'
    (folder/f'model{suffix}.txt').write_text(''.join(Placement(**b).to_txt() for b in toolkit_result['bricks']),encoding='utf8')
    (folder/f'model{suffix}.ldr').write_text(to_ldr(toolkit_result,model.cells),encoding='utf8')
    readback = exported_audit(folder,source,_POLICY)
    if status=='success' and not readback['passed']:
        raise ValueError(f'export readback failed: {model_id}')
    dump(folder/'validation.json',readback)
    report = {'modelId':model_id,'category':job['category'],'status':status,
              'sourceModelPath':str(source_path.resolve()),'sourceFileSha256':source_sha,
              'sourceExactOccupancyHash':job['exactOccupancyHash'],
              'sourceCanonicalGeometryHash':job['canonicalGeometryHash'],
              'geometryPassed':readback['passed'],'staticVerified':None,'fullPhysics':False,
              'feasibility':necessary,'validation':readback,'search':search,
              'elapsedSeconds':time.monotonic()-start,
              'outputFileSha256':{p.name:file_sha(p) for p in sorted(folder.iterdir()) if p.suffix != '.tmp'}}
    dump(report_path,report)
    return report


def verify_job(job):
    folder = _RUN/'models'/job['category']/job['modelId']
    if not (folder/'report.json').exists():
        return 'missing_output'
    report = json.loads((folder/'report.json').read_text(encoding='utf8'))
    source_path = _DATASET/job['modelPath']/'model.json'
    if file_sha(source_path) != report['sourceFileSha256']:
        raise ValueError('source changed since assembly: '+job['modelId'])
    if not all(file_sha(folder/name)==v for name,v in report['outputFileSha256'].items()):
        raise ValueError('output changed since assembly: '+job['modelId'])
    result = exported_audit(folder,json.loads(source_path.read_text(encoding='utf8')),_POLICY)
    if result['passed'] != report['geometryPassed'] or result != report['validation']:
        raise ValueError('independent readback changed: '+job['modelId'])
    return 'verified_success' if result['passed'] else 'verified_failure_draft'


def summarize(run, jobs):
    rows = []
    for job in jobs:
        path = run/'models'/job['category']/job['modelId']/'report.json'
        if path.exists():
            full = json.loads(path.read_text(encoding='utf8'))
            rows.append({**{k:full[k] for k in ('modelId','category','status','geometryPassed',
                         'sourceExactOccupancyHash','sourceCanonicalGeometryHash','sourceFileSha256','fullPhysics')},
                         'brickCount':full['validation']['brickCount'],
                         'failureReason':full['feasibility']['reason'] if not full['feasibility']['passed']
                         else ('search_failed' if not full['geometryPassed'] else None)})
    counts = Counter(row['status'] for row in rows)
    by_category = defaultdict(Counter)
    for row in rows:
        by_category[row['category']][row['status']] += 1
    report = {'algorithmVersion':VERSION,'requestedModelCount':len(jobs),
              'processedModelCount':len(rows),'remainingModelCount':len(jobs)-len(rows),
              'statusCounts':dict(counts),'categoryStatusCounts':{k:dict(v) for k,v in by_category.items()},
              'successfulBrickCount':sum(r['brickCount'] for r in rows if r['geometryPassed']),
              'geometryAssemblyPassedModelCount':counts['success'],
              'allModelsAssemblyPassed':len(rows)==len(jobs) and counts['success']==len(jobs),
              'failureReasonCounts':dict(Counter(r['failureReason'] for r in rows if not r['geometryPassed'])),
              'staticVerifiedModelCount':0,'physicsStatus':'not_attempted',
              'voxelSourceModified':False,'notes':[
                  'Failures are not voxel-data validation failures; six-neighbor connectivity is weaker than stud connectivity.',
                  'Infeasibility is scoped to the chosen monochrome rectangular single-height library and lower-support policy.',
                  'Bounded search failure does not prove mathematical impossibility.',
                  'Discrete grid and RGB are preserved; LEGO height=24 versus stud pitch=20 changes physical aspect ratio.',
                  'No contact force, tipping, friction, stud insertion path, or actual construction verification.']}
    dump(run/'summary.json',report)
    (run/'assembly_index.jsonl').write_text(''.join(json.dumps({k:r[k] for k in (
        'modelId','category','status','geometryPassed','sourceExactOccupancyHash',
        'sourceCanonicalGeometryHash','sourceFileSha256','fullPhysics')},ensure_ascii=False)+'\n' for r in rows),encoding='utf8')
    text = ['# LEGO 拼接处理报告','',
            f"实际处理 {len(rows)}/{len(jobs)} 个模型；几何装配通过 {counts['success']} 个。",
            f"必要条件不满足 {counts['infeasible_under_selected_policy']} 个；有界搜索未通过 {counts['search_failed']} 个。",
            '静力/实物搭建未验证；原体素和五级训练记录未修改。','',
            '| 类别 | 已处理 | 通过 | 必要条件失败 | 搜索失败 |',
            '|---|---:|---:|---:|---:|']
    for category,c in by_category.items():
        text.append(f"| {category} | {sum(c.values())} | {c['success']} | {c['infeasible_under_selected_policy']} | {c['search_failed']} |")
    text += ['', '本报告的通过仅指离散占用/RGB不变、标准砖库、前缀支撑、单stud组件和JSON/TXT/LDR独立回读；不指完整静力通过。',
             '必要条件失败的证明仅适用于所选同色矩形、单砖高、上下stud连接和下支撑规则。搜索失败不等同于无解。',
             '每个格点按水平1stud、竖直1标准砖高解释，实物高宽比与等距体素预览不同。',
             '每模型实际证据见 models/<category>/<modelId>/report.json；全量再读回见 readback_verification.json。']
    (run/'REPORT.md').write_text('\n'.join(text)+'\n',encoding='utf8')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('pilot','run','verify','summary'))
    p.add_argument('--dataset',type=Path,default=DEFAULT_DATASET)
    p.add_argument('--out',type=Path,default=HERE/'runs'/'B_extended_v2')
    p.add_argument('--workers',type=int,default=8)
    p.add_argument('--count',type=int)
    p.add_argument('--seconds',type=float,default=3)
    p.add_argument('--nodes',type=int,default=1500)
    p.add_argument('--beam',type=int,default=8)
    p.add_argument('--brick-library',choices=('brickgpt','extended'),default='extended')
    args = p.parse_args()
    if args.workers < 1 or args.seconds <= 0 or args.nodes < 1 or args.beam < 1:
        p.error('positive worker and search budgets required')
    manifest = json.loads((args.dataset/'manifest.json').read_text(encoding='utf8'))
    jobs = [{k:m[k] for k in ('modelId','category','modelPath','modelSeed','exactOccupancyHash','canonicalGeometryHash')}
            for m in manifest['models']]
    if args.action in ('verify','summary') and (args.out/'selection.json').exists():
        jobs = json.loads((args.out/'selection.json').read_text(encoding='utf8'))
    elif args.action == 'pilot':
        seen = set()
        jobs = [j for j in jobs if not (j['category'] in seen or seen.add(j['category']))]
    if args.count is not None and args.action not in ('verify','summary'):
        if args.count < 1:
            p.error('count must be positive')
        jobs = jobs[:args.count]
    # Freeze dependencies as an additive snapshot; originals remain untouched.
    if not SNAPSHOT.exists():
        SNAPSHOT.mkdir(parents=True)
        for name in TOOLKIT_FILES:
            shutil.copyfile(ORIGINAL_TOOLKIT/name,SNAPSHOT/name)
    policy = dict(world_dim=48,brick_library=args.brick_library,min_support_fraction=.10,
                  max_cantilever_distance=2,max_components=64,max_seconds=args.seconds,
                  max_nodes=args.nodes,beam_width=args.beam)
    config = {'algorithmVersion':VERSION,'datasetVersion':manifest['datasetVersion'],
              'datasetPath':str(args.dataset.resolve()),'policy':policy,
              'selectionSha256':sha(json.dumps(jobs,sort_keys=True).encode('utf8')),
              'sourceCodeSha256':file_sha(__file__),
              'toolkitSourceSha256':{name:file_sha(SNAPSHOT/name) for name in TOOLKIT_FILES}}
    args.out.mkdir(parents=True,exist_ok=True)
    if (args.out/'config.json').exists():
        if json.loads((args.out/'config.json').read_text(encoding='utf8')) != config:
            p.error('configuration/source changed: choose a new output directory')
    else:
        dump(args.out/'config.json',config)
        dump(args.out/'selection.json',jobs)
        shutil.copyfile(__file__,args.out/'runner_snapshot.py')
    initialize(args.dataset,args.out,policy)
    if args.action in ('pilot','run'):
        counts = Counter()
        started = time.monotonic()
        with ProcessPoolExecutor(max_workers=args.workers,initializer=initialize,
                                 initargs=(args.dataset,args.out,policy)) as pool:
            for number,result in enumerate(pool.map(process,jobs,chunksize=1),1):
                counts[result['status']] += 1
                if args.action=='pilot' or number%100==0 or number==len(jobs):
                    print('ASSEMBLY_PROGRESS',number,'/',len(jobs),dict(counts),
                          'seconds',round(time.monotonic()-started,1),flush=True)
                if number%250==0:
                    dump(args.out/'progress.json',{'processedThisInvocation':number,'requested':len(jobs),
                         'statusCounts':dict(counts),'elapsedSeconds':time.monotonic()-started})
    elif args.action == 'verify':
        counts = Counter()
        with ProcessPoolExecutor(max_workers=args.workers,initializer=initialize,
                                 initargs=(args.dataset,args.out,policy)) as pool:
            for number,outcome in enumerate(pool.map(verify_job,jobs,chunksize=8),1):
                counts[outcome] += 1
                if number%1000==0:
                    print('READBACK_PROGRESS',number,'/',len(jobs),flush=True)
        dump(args.out/'readback_verification.json',{'allDeliveredOutputsReadbackPassed':not counts['missing_output'],
             'requestedModelCount':len(jobs),'counts':dict(counts),'staticVerified':None,'fullPhysics':False})
        print('EXPORTED_READBACK',dict(counts),flush=True)
    summary = summarize(args.out,jobs)
    print('ASSEMBLY_SUMMARY',json.dumps({k:v for k,v in summary.items() if k not in ('categoryStatusCounts','notes')},ensure_ascii=False),flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
