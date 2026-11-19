"""Regenerate failed comparison prompts with the archived seed ladder and refine."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import hashlib
from pathlib import Path
import sys
import time
import urllib.request

import refine_comparison as core

MODEL = core.ROOT / 'downloads/BrickGPT-Qwen3-1.7B-BrickMore-48'
SEEDS = (7, 2027, 555, 888, 104, 2026, 42, 104729)


def generate_llamacpp(tokenizer, row, seed, folder, server_url):
    if (folder/'generation.json').exists() and (folder/'raw.txt').exists():
        previous = core.read(folder/'generation.json')
        if previous['prompt'] != row['caption'] or previous['seed'] != seed:
            raise ValueError('Cached candidate identity differs')
        return
    folder.mkdir(parents=True,exist_ok=True)
    partial = folder/'partial.txt'
    if partial.exists():
        partial.rename(folder/f'interrupted_{time.time_ns()}.txt')
    instruction = core.review.instruction(row['caption'])
    rendered = tokenizer.apply_chat_template([
        {'role':'system','content':'You are a helpful assistant.'},
        {'role':'user','content':instruction}],tokenize=False,
        add_generation_prompt=True,enable_thinking=False)
    options = dict(n_predict=8192,seed=seed,temperature=.7,top_p=.9,top_k=20,
                   min_p=0.,samplers=['temperature','top_k','top_p'],
                   cache_prompt=False,stream=True)
    request = urllib.request.Request(server_url+'/completion',
        data=json.dumps(dict(options,prompt=rendered)).encode(),
        headers={'Content-Type':'application/json'})
    started = time.monotonic()
    last_print = started
    final = None
    chunks = 0
    print('GENERATE',row['prompt_id'],'seed',seed,'llama.cpp BF16',flush=True)
    with partial.open('w',encoding='utf-8',newline='\n') as output:
        with urllib.request.urlopen(request,timeout=1800) as response:
            for line in response:
                if not line.startswith(b'data: '):
                    continue
                event = json.loads(line[6:].decode('utf-8'))
                output.write(event.get('content',''))
                chunks += 1
                if time.monotonic()-last_print > 20:
                    output.flush()
                    last_print = time.monotonic()
                    print('TOKENS',row['prompt_id'],seed,chunks,
                          'elapsed_s',round(last_print-started),flush=True)
                if event.get('stop'):
                    final = event
                    break
    if final is None:
        raise RuntimeError('Inference stream ended before final status')
    partial.replace(folder/'raw.txt')
    core.dump(folder/'generation.json',dict(prompt_id=row['prompt_id'],prompt=row['caption'],
        instruction=instruction,repository=core.review.REPOSITORY,revision=core.review.REVISION,
        seed=seed,completed=final.get('stop_type')=='eos',
        generated_tokens=final.get('tokens_predicted'),input_tokens=final.get('timings',{}).get('prompt_n'),
        seconds=round(time.monotonic()-started,3),dtype='bfloat16 GGUF weights',
        kv_cache='q8_0 K and V',backend='llama.cpp b12359 CUDA',options=options,
        rendered_prompt_sha256=hashlib.sha256(rendered.encode()).hexdigest(),
        timings=final.get('timings'),stop_type=final.get('stop_type'),
        generation_settings=final.get('generation_settings')))


def refine_saved_candidate(folder):
    report_path = folder/'candidate_result.json'
    if report_path.exists():
        return core.read(report_path)
    generation = core.read(folder/'generation.json')
    text = (folder/'raw.txt').read_text(encoding='utf-8')
    bricks, parsed = core.review.parse(text)
    cells, normalization = core.normalize(bricks)
    value = dict(status='rejected', generation=generation, parsed=parsed,
                 normalization=normalization, attempts=[])
    core.dump(folder/'parsed.json', dict(bricks=bricks, report=parsed))
    chosen = None
    if not generation['completed']:
        value['reason'] = 'generation_did_not_reach_EOS'
    elif not cells:
        value['reason'] = 'no_usable_brick_placements'
    elif len(core.voxel_components(cells)) != 1:
        value['reason'] = 'disconnected_target'
    elif core.independent_audit(bricks,cells)['passed']:
        chosen = [{k:b[k] for k in core.GEOMETRY_KEYS} for b in bricks]
        value['method'] = 'regenerated_original_already_connected'
    else:
        for seconds in (12,60,180):
            print('REFINE',folder.parent.parent.name,folder.name,seconds,flush=True)
            chosen, details = core.solve_existing_cuts(cells,seconds)
            value['attempts'].append(details)
            if chosen:
                value['method'] = details['method']
                break
            if details.get('certified_infeasible'):
                value['reason'] = 'certified_unconnectable_preserving_target'
                break
            chosen, details = core.solve(cells,seconds)
            value['attempts'].append(details)
            if chosen:
                value['method'] = details['method']
                break
            if details.get('certified_infeasible'):
                value['reason'] = 'certified_unconnectable_preserving_target'
                break
    if chosen:
        core.review.export(folder,'refined',chosen)
        final = core.review.assembly.parse_ldr((folder/'refined.ldr').read_text(encoding='utf-8'))
        checked = core.independent_audit(final,cells)
        if not checked['passed']:
            raise ValueError('Regenerated final export audit failed')
        value.update(status='passed',validation=checked,refined_bricks=len(chosen),
            output_sha256={f:core.sha(folder/f) for f in ('raw.txt','generation.json','refined.ldr','refined.txt','refined.json')})
    core.dump(report_path,value)
    return value


def generate_one(model, tokenizer, row, seed, folder):
    import torch
    import transformers

    generation_file = folder/'generation.json'
    if generation_file.exists() and (folder/'raw.txt').exists():
        previous = core.read(generation_file)
        if previous['prompt'] != row['caption'] or previous['seed'] != seed:
            raise ValueError('Cached generation prompt or seed differs')
        return
    folder.mkdir(parents=True,exist_ok=True)
    transformers.set_seed(seed)
    instruction = core.review.instruction(row['caption'])
    rendered = tokenizer.apply_chat_template([
        {'role':'system','content':'You are a helpful assistant.'},
        {'role':'user','content':instruction}],tokenize=False,
        add_generation_prompt=True,enable_thinking=False)
    inputs = tokenizer(rendered,return_tensors='pt').to('cuda')
    ninput = inputs.input_ids.shape[1]
    started = time.monotonic()

    class Progress(transformers.StoppingCriteria):
        def __init__(self):
            self.last = started

        def __call__(self,input_ids,scores,**kwargs):
            if time.monotonic()-self.last > 20:
                self.last = time.monotonic()
                print('TOKENS',row['prompt_id'],seed,input_ids.shape[1]-ninput,
                      'elapsed_s',round(self.last-started),flush=True)
            return False

    torch.cuda.reset_peak_memory_stats()
    print('GENERATE',row['prompt_id'],'seed',seed,flush=True)
    with torch.inference_mode():
        output = model.generate(**inputs,max_new_tokens=8192,do_sample=True,
            temperature=.7,top_p=.9,top_k=20,use_cache=True,pad_token_id=tokenizer.eos_token_id,
            stopping_criteria=transformers.StoppingCriteriaList([Progress()]))
    torch.cuda.synchronize()
    tokens = output[0,ninput:].tolist()
    eos = model.generation_config.eos_token_id
    eos = eos if isinstance(eos,list) else [eos]
    (folder/'raw.txt').write_text(tokenizer.decode(tokens,skip_special_tokens=True),encoding='utf-8')
    core.dump(generation_file,dict(prompt_id=row['prompt_id'],prompt=row['caption'],
        instruction=instruction,repository=core.review.REPOSITORY,revision=core.review.REVISION,
        seed=seed,completed=bool(tokens and tokens[-1] in eos),generated_tokens=len(tokens),
        input_tokens=ninput,seconds=round(time.monotonic()-started,3),dtype='bfloat16',
        options=dict(max_new_tokens=8192,do_sample=True,temperature=.7,top_p=.9,top_k=20),
        device=torch.cuda.get_device_name(),peak_allocated_gib=torch.cuda.max_memory_allocated()/2**30,
        torch_version=torch.__version__,transformers_version=transformers.__version__))
    del output,inputs
    torch.cuda.empty_cache()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=core.DEFAULT_OUT)
    parser.add_argument('--backend',choices=['transformers','llamacpp'],default='transformers')
    parser.add_argument('--server-url',default='http://127.0.0.1:18089')
    args = parser.parse_args()
    out = args.out.resolve()
    manifest = core.read(out/'input_manifest.json')
    selections_path = out/'regeneration_selections.json'
    selections = core.read(selections_path) if selections_path.exists() else {}
    exhausted_path = out/'regeneration_exhausted.json'
    exhausted = core.read(exhausted_path) if exhausted_path.exists() else {}
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import scipy

    actual_hash = core.sha(MODEL/'model.safetensors')
    expected_hash = (MODEL/'model.sha256').read_text().split()[0]
    if actual_hash != expected_hash:
        raise ValueError('Local generation weights SHA256 differs')
    torch.set_num_threads(2)
    tokenizer = AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
    previous_provenance = out/'regeneration_provenance.json'
    previous = core.read(previous_provenance) if previous_provenance.exists() else {}
    if previous:
        core.dump(out/'run_history'/f'regeneration_provenance_{time.time_ns()}.json',previous)
    model = None
    if args.backend == 'transformers':
        print('LOAD_MODEL',MODEL,flush=True)
        model = AutoModelForCausalLM.from_pretrained(MODEL,local_files_only=True,
            torch_dtype=torch.bfloat16,attn_implementation='sdpa',device_map={'':'cuda'},
            low_cpu_mem_usage=True).eval()
        device = torch.cuda.get_device_name()
    else:
        import urllib.request
        with urllib.request.urlopen(args.server_url+'/health',timeout=30) as response:
            if json.load(response)['status'] != 'ok':
                raise RuntimeError('Local CUDA inference server is not ready')
        device = previous.get('device','local NVIDIA CUDA device')
    core.dump(out/'regeneration_provenance.json',dict(
        repository=core.review.REPOSITORY,revision=core.review.REVISION,
        model_weights_sha256=actual_hash,source_code_sha256=core.sha(__file__),
        refinement_code_sha256=core.sha(core.__file__),seeds=list(SEEDS),
        torch_version=torch.__version__,transformers_version=transformers.__version__,
        scipy_version=scipy.__version__,device=device,backend=args.backend,
        gguf_sha256=core.sha(MODEL/'brickmore-bf16.gguf') if args.backend=='llamacpp' else None,
        kv_cache='q8_0 K and V' if args.backend=='llamacpp' else 'bfloat16',
        runtime_source='https://github.com/ggml-org/llama.cpp/releases/tag/b12359' if args.backend=='llamacpp' else None,
        user_policy='Regenerate infeasible outputs using original unchanged prompts and keep all raw outputs.',
        original_inputs_replaced=False))
    print('MODEL_READY',device,args.backend,flush=True)
    while True:
        available = []
        for row in manifest:
            result_path = out/'records'/row['prompt_id']/'result.json'
            if result_path.exists():
                result = core.read(result_path)
                if result['status'] in ('infeasible_preserving_target','solver_budget_exhausted'):
                    available.append((row,result))
        pending = [(r,original) for r,original in available
                   if r['prompt_id'] not in selections and r['prompt_id'] not in exhausted]
        if not pending:
            status = core.read(out/'summary.json')
            if status['finished']:
                break
            print('WAITING_FOR_REFINEMENT',status['completed'],len(selections),'rescued',flush=True)
            time.sleep(20)
            continue
        for row, original in pending:
            pid = row['prompt_id']
            reports = []
            for seed in SEEDS:
                folder = out/'records'/pid/'regeneration'/f'seed{seed}'
                if args.backend == 'llamacpp':
                    generate_llamacpp(tokenizer,row,seed,folder,args.server_url)
                else:
                    generate_one(model,tokenizer,row,seed,folder)
                checked = refine_saved_candidate(folder)
                reports.append(dict(seed=seed,status=checked['status'],
                                    reason=checked.get('reason'),folder=folder.relative_to(out).as_posix()))
                print('CANDIDATE',pid,seed,checked['status'],checked.get('reason'),flush=True)
                if checked['status'] == 'passed':
                    selections[pid] = dict(prompt_id=pid,seed=seed,caption=row['caption'],
                        baseline_status=original['status'],folder=folder.relative_to(out).as_posix(),
                        ldr_path=(folder/'refined.ldr').relative_to(out).as_posix(),
                        refined_bricks=checked['refined_bricks'],validation=checked['validation'],
                        normalization=checked['normalization'],output_sha256=checked['output_sha256'])
                    core.dump(selections_path,selections)
                    break
            else:
                exhausted[pid] = reports
                core.dump(exhausted_path,exhausted)
            progress = dict(rescued=len(selections),exhausted=list(exhausted),
                            known_baseline_failures=len(available),active=None,finished=False)
            core.dump(out/'regeneration_progress.json',progress)
            print('REGEN_PROGRESS',progress,flush=True)
    progress = dict(rescued=len(selections),exhausted=list(exhausted),finished=True)
    core.dump(out/'regeneration_progress.json',progress)
    print('REGENERATION_FINISHED',progress,flush=True)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    main()
