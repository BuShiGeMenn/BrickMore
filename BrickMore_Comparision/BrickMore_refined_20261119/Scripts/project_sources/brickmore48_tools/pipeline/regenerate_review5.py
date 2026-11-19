"""Portable, resumable BrickMore-48 inference for an unchanged review prompt file."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Train/algorithms/voxel_assembly_b'))
import assembly_pipeline as assembly

REVISION = '92d1c595f5fe076971cc2633d6844f097a84eef3'
REPOSITORY = 'Kyle308666/BrickGPT-Qwen3-1.7B-BrickMore-48'
DIMS = ((2,4),(4,2),(2,6),(6,2),(1,2),(2,1),(1,4),(4,1),(1,6),(6,1),
        (1,8),(8,1),(1,1),(2,2),(1,3),(3,1),(2,3),(3,2),(2,8),(8,2))
PATTERN = re.compile(r'(\d+)x(\d+)\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\)')


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def instruction(caption):
    return ('Create a LEGO model of the input. Format your response as a list of bricks: '
            '<brick dimensions> <brick position>, where the brick position is (x,y,z).\n'
            'Allowed brick dimensions are ' + ', '.join(f'{h}x{w}' for h,w in DIMS) + '.\n'
            'All bricks are 1 unit tall.\n'
            'The world is a 48x48x48 grid. All brick cells must have coordinates from 0 to 47.\n\n'
            '### Input:\n' + caption)


def footprint(b):
    return {(x,y,b['z']) for x in range(b['x'], b['x']+b['h'])
            for y in range(b['y'], b['y']+b['w'])}


def audit(bricks):
    owner = {}
    parent = list(range(len(bricks)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    overlaps = 0
    out_of_bounds = 0
    unsupported = []
    for i,b in enumerate(bricks):
        if (b['h'], b['w']) not in DIMS or not (0 <= b['x'] <= 48-b['h'] and
                0 <= b['y'] <= 48-b['w'] and 0 <= b['z'] < 48):
            out_of_bounds += 1
            continue
        for p in footprint(b):
            if p in owner:
                overlaps += 1
            owner[p] = i
    for (x,y,z),i in owner.items():
        j = owner.get((x,y,z+1))
        if j is not None:
            parent[find(i)] = find(j)
    for i,b in enumerate(bricks):
        if b['z'] and not any((x,y,z-1) in owner for x,y,z in footprint(b)):
            unsupported.append(i)
    labels = {p:find(i) for p,i in owner.items()}
    unseen = set(owner)
    voxel_components = 0
    while unseen:
        voxel_components += 1
        stack = [unseen.pop()]
        while stack:
            x,y,z = stack.pop()
            for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                if p in unseen:
                    unseen.remove(p)
                    stack.append(p)
    components = len(set(labels.values()))
    return dict(brick_count=len(bricks), occupied_voxels=len(owner), overlap_voxels=overlaps,
                out_of_bounds_bricks=out_of_bounds, voxel_components=voxel_components,
                stud_components=components, unsupported_from_below=len(unsupported),
                geometry_valid=bool(bricks) and not overlaps and not out_of_bounds and voxel_components == 1,
                single_stud_component=bool(bricks) and not overlaps and not out_of_bounds and components == 1,
                physical_stability_tested=False), labels


def parse(text):
    bricks, errors = [], []
    for number,line in enumerate(text.splitlines(),1):
        line = line.strip()
        if not line or line in ('<think>','</think>'):
            continue
        m = PATTERN.fullmatch(line)
        if not m:
            errors.append(f'Line {number}: malformed record: {line[:120]}')
            continue
        a,b,x,y,z = map(int,m.groups())
        # Same documented YX convention as the previous 630-model review pipeline.
        bricks.append(dict(h=b,w=a,x=x,y=y,z=z))
    report,_ = audit(bricks)
    report.update(format_errors=errors, raw_dimension_order='yx',
                  dimension_convention_source='existing 630-model pipeline; training converter not verified')
    report['geometry_valid'] &= not errors
    return bricks, report


def export(folder, name, bricks):
    folder = Path(folder)
    cells = {p:0xE8B42B for b in bricks for p in footprint(b)}
    dump(folder / (name + '.json'), {'bricks':bricks, 'up_axis':'z', 'dimension_order':'xy'})
    (folder / (name + '.txt')).write_text(''.join(
        f"{b['h']}x{b['w']} ({b['x']},{b['y']},{b['z']})\n" for b in bricks), encoding='utf-8')
    (folder / (name + '.ldr')).write_text(assembly.to_ldr(
        {'status':name,'bricks':bricks},cells), encoding='utf-8')
    back = assembly.parse_ldr((folder / (name + '.ldr')).read_text(encoding='utf-8'))
    expected = [tuple(b[k] for k in ('h','w','x','y','z')) for b in bricks]
    actual = [tuple(b[k] for k in ('h','w','x','y','z')) for b in back]
    if actual != expected:
        raise RuntimeError('LDR round-trip mismatch')


def retile(cells, seconds=60):
    """Exact cover with valid connectivity cuts; never adds or deletes voxels."""
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import coo_array
    start = time.monotonic()
    points = sorted(cells)
    index = {p:i for i,p in enumerate(points)}
    candidates, masks = [], []
    rr,cc = [],[]
    for x,y,z in points:
        for h,w in DIMS:
            b = dict(h=h,w=w,x=x,y=y,z=z)
            mask = footprint(b)
            if mask <= cells:
                j = len(candidates)
                candidates.append(b)
                masks.append(mask)
                rr.extend(index[p] for p in mask)
                cc.extend([j]*len(mask))
    n = len(candidates)
    base = coo_array((np.ones(len(rr)),(np.asarray(rr,dtype=np.int32),np.asarray(cc,dtype=np.int32))),
                     shape=(len(points),n)).tocsc()
    constraints = [LinearConstraint(base,np.ones(len(points)),np.ones(len(points)))]
    seen = set()
    log = []
    for iteration in range(120):
        remaining = seconds-(time.monotonic()-start)
        if remaining <= 0:
            break
        result = milp(c=np.ones(n),integrality=np.ones(n),bounds=Bounds(0,1),
                      constraints=constraints,options={'time_limit':min(remaining,15.),'mip_rel_gap':.08})
        if result.x is None:
            log.append({'iteration':iteration,'status':int(result.status),'solution':False})
            break
        chosen = [candidates[i] for i,v in enumerate(result.x) if v > .5]
        report, labels = audit(chosen)
        exact = set(labels) == cells
        log.append({'iteration':iteration,'status':int(result.status),
                    'brick_count':len(chosen),'stud_components':report['stud_components'],'exact_coverage':exact})
        if report['single_stud_component'] and exact:
            return chosen,dict(seconds=round(time.monotonic()-start,3),log=log,
                               method='exact_cover_with_stud_connectivity_cuts',shape_preserved=True)
        if not exact:
            break
        new_cuts = 0
        for component in set(labels.values()):
            part = frozenset(p for p,label in labels.items() if label == component)
            if part in seen:
                continue
            seen.add(part)
            cross = [i for i,mask in enumerate(masks) if mask & part and not mask <= part]
            if not cross:
                return None,dict(log=log,reason='no_possible_stud_connected_exact_cover')
            row = coo_array((np.ones(len(cross)),(np.zeros(len(cross),dtype=np.int32),
                            np.asarray(cross,dtype=np.int32))),shape=(1,n)).tocsc()
            constraints.append(LinearConstraint(row,1,np.inf))
            new_cuts += 1
        if not new_cuts:
            break
    return None,dict(seconds=round(time.monotonic()-start,3),log=log,reason='solver_budget_or_infeasible')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--prompts',type=Path,required=True)
    p.add_argument('--model',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--seeds',type=int,nargs='+',default=[71107])
    p.add_argument('--groups',nargs='*')
    p.add_argument('--prompt-index',type=int,default=0)
    p.add_argument('--retile-seconds',type=int,default=60)
    p.add_argument('--greedy',action='store_true')
    p.add_argument('--postprocess-only',action='store_true')
    args = p.parse_args()
    source = args.prompts.read_bytes()
    plan = json.loads(source.decode('utf-8-sig'))
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out / 'source_prompts.json').write_bytes(source)
    dump(args.out / 'provenance.json',dict(repository=REPOSITORY,revision=REVISION,
        prompt_source=str(args.prompts),prompt_source_sha256=hashlib.sha256(source).hexdigest(),
        prompt_policy=plan.get('prompt_policy','verbatim, no rewrite'),retained_groups=plan['retained_groups'],
        raw_dimension_order='yx',physical_stability_tested=False))
    if not args.postprocess_only:
        import torch
        import transformers
        from transformers import AutoModelForCausalLM, AutoTokenizer, StoppingCriteria, StoppingCriteriaList
        torch.set_num_threads(4)
        print('Loading tokenizer and BF16 model on CUDA',flush=True)
        tokenizer = AutoTokenizer.from_pretrained(args.model,local_files_only=True)
        model = AutoModelForCausalLM.from_pretrained(args.model,dtype=torch.bfloat16,
                    attn_implementation='sdpa',local_files_only=True).to('cuda').eval()
        print('MODEL_READY',torch.cuda.get_device_name(0),flush=True)
        class Progress(StoppingCriteria):
            def __init__(self,start):
                self.start = start
                self.last = time.monotonic()
            def __call__(self,input_ids,scores,**kwargs):
                if time.monotonic()-self.last >= 25:
                    self.last = time.monotonic()
                    print('  generated_tokens',input_ids.shape[1]-self.start,flush=True)
                return False
    manifest_path = args.out / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else []
    done = {m['id'] for m in manifest}
    for group in plan['groups']:
        if args.groups and group['group'] not in args.groups:
            continue
        if args.prompt_index >= len(group['prompts']):
            continue
        prompt = group['prompts'][args.prompt_index]
        for seed in args.seeds:
            suffix = 'G' if args.greedy else f'S{seed}'
            candidate_id = f"{group['group']}_P{args.prompt_index+1}_{suffix}"
            if candidate_id in done:
                continue
            folder = args.out / 'models' / candidate_id
            folder.mkdir(parents=True,exist_ok=True)
            row = dict(id=candidate_id,group=group['group'],category=group['category'],level=group['level'],
                seed=seed,prompt=prompt['prompt'],source_candidate_id=prompt['candidate_id'],
                current_prompt=prompt['is_current_model'],folder=str(folder.relative_to(args.out)).replace('\\','/'))
            if 'evidence' in prompt:
                row['prompt_evidence'] = prompt['evidence']
            dump(folder / 'source_prompt.json',prompt)
            print('START',candidate_id,flush=True)
            raw_path = folder / 'raw.txt'
            if not raw_path.exists():
                if args.postprocess_only:
                    continue
                transformers.set_seed(seed)
                message = instruction(prompt['prompt'])
                rendered = tokenizer.apply_chat_template([
                    {'role':'system','content':'You are a helpful assistant.'},
                    {'role':'user','content':message}],tokenize=False,
                    add_generation_prompt=True,enable_thinking=False)
                inputs = tokenizer(rendered,return_tensors='pt').to('cuda')
                ninput = inputs.input_ids.shape[1]
                torch.cuda.reset_peak_memory_stats()
                start = time.monotonic()
                sampling = dict(do_sample=False) if args.greedy else dict(do_sample=True,temperature=.7,top_p=.9)
                with torch.inference_mode():
                    output = model.generate(**inputs,max_new_tokens=8192,**sampling,
                        use_cache=True,pad_token_id=tokenizer.eos_token_id,
                        stopping_criteria=StoppingCriteriaList([Progress(ninput)]))
                torch.cuda.synchronize()
                tokens = output[0,ninput:].tolist()
                raw_path.write_text(tokenizer.decode(tokens,skip_special_tokens=True),encoding='utf-8')
                eos = model.generation_config.eos_token_id
                eos = eos if isinstance(eos,list) else [eos]
                generation = dict(repository=REPOSITORY,revision=REVISION,instruction=message,
                    prompt=prompt['prompt'],seed=seed,input_tokens=ninput,generated_tokens=len(tokens),
                    completed=bool(tokens and tokens[-1] in eos),seconds=round(time.monotonic()-start,3),
                    dtype='bfloat16',device=torch.cuda.get_device_name(0),
                    peak_allocated_gib=torch.cuda.max_memory_allocated()/1024**3,
                    options=dict(max_new_tokens=8192,**sampling),
                    versions=dict(torch=torch.__version__,transformers=transformers.__version__))
                dump(folder / 'generation.json',generation)
                del output, inputs
                torch.cuda.empty_cache()
            generation = json.loads((folder / 'generation.json').read_text(encoding='utf-8'))
            bricks,report = parse(raw_path.read_text(encoding='utf-8'))
            dump(folder / 'raw_report.json',report)
            valid = [b for b in bricks if (b['h'],b['w']) in DIMS and
                     0 <= b['x'] <= 48-b['h'] and 0 <= b['y'] <= 48-b['w'] and 0 <= b['z'] < 48]
            if valid:
                export(folder,'raw_geometry',valid)
            cells = set().union(*(footprint(b) for b in valid)) if valid else set()
            chosen = None
            solve_report = {}
            if generation['completed'] and report['geometry_valid'] and report['single_stud_component']:
                chosen = valid
                solve_report = {'method':'original_inference','shape_preserved':True}
            elif generation['completed'] and not report['format_errors'] and not report['out_of_bounds_bricks'] and report['voxel_components'] == 1:
                chosen, solve_report = retile(cells,args.retile_seconds)
            dump(folder / 'retile_report.json',solve_report)
            row.update(raw=report,generation=generation,retile=solve_report)
            if chosen:
                export(folder,'model',chosen)
                final,_ = audit(chosen)
                final['shape_preserved'] = set().union(*(footprint(b) for b in chosen)) == cells
                final['ldr_roundtrip_passed'] = True
                dump(folder / 'validation.json',final)
                row.update(status='geometry_passed_pending_visual_review',validation=final)
            else:
                row['status'] = 'failed_geometry_or_solver'
            manifest.append(row)
            dump(manifest_path,manifest)
            print('DONE',candidate_id,row['status'],report['brick_count'],'raw bricks',
                  report['stud_components'],'raw stud components',flush=True)
    print('ALL_JOBS_FINISHED',len(manifest),flush=True)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    main()
