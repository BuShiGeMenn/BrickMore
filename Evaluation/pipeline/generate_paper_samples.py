"""Qwen3 PT/SFT generation with parse-only rejection/retry for conditional evaluation."""
import argparse
import hashlib
import json
from pathlib import Path
from paper_common import (Journal, fingerprint, load_bricknet, load_causal, normalize_ids,
                          packages, read_jsonl, resolve_hf, sha256, source_hashes, write_json)


def trial_seed(seed, sid, attempt):
    return (seed + int.from_bytes(hashlib.sha256(f'{sid}:{attempt}'.encode()).digest()[:4],'little')) % 2**32


def retry_sample(row, generate, parse, attempts, accepted, config, max_attempts, conditional):
    """Persist every attempt, including the valid attempt before writing selected output."""
    sid, ih = row['sample_id'], fingerprint(row)
    cached = accepted.cached(sid, ih)
    if cached:
        return cached
    for attempt in range(max_attempts if conditional else 1):
        aid = f'{sid}__attempt{attempt}'
        ah = fingerprint({'input':row,'attempt':attempt})
        trial = attempts.cached(aid, ah)
        if trial is None:
            text = generate(row,attempt)
            result = parse(text)
            trial = {'sample_id':aid,'generation_sample_id':sid,'attempt':attempt,
                'text':text,'parse_ok':result['parse_ok'],'parse_error':result.get('parse_error'),
                'parts':result['parts']}
            attempts.append(trial,ah)
        # Collision failures are deliberately never rejected.
        if not conditional or trial['parse_ok']:
            result = {**row,'text':trial['text'],'parse_ok':trial['parse_ok'],
                      'parse_error':trial['parse_error'],'parts':trial['parts'],
                      'attempts_used':attempt+1,'status':'generated',
                      'generation_config_signature':accepted.signature}
            accepted.append(result,ih)
            return result
    return None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=['conditional','unconditional'], default='conditional')
    p.add_argument('--prompts', type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--model', required=True)
    p.add_argument('--revision')
    p.add_argument('--lora', action='append', default=[], help='PT first, then SFT; merged in this order')
    p.add_argument('--lora-revision', action='append', default=[])
    p.add_argument('--num-samples', type=int, default=65536)
    p.add_argument('--n-per-prompt', type=int, default=1)
    p.add_argument('--max-attempts', type=int, default=50, help='Finite safety cap; exhaustion is reported incomplete')
    p.add_argument('--sampling', choices=['ns','as'], default='ns')
    p.add_argument('--temperature', type=float, default=1.0)
    p.add_argument('--max-new-tokens', type=int, default=4096)
    p.add_argument('--parts', type=int, default=100)
    p.add_argument('--seed', type=int, default=20261024)
    p.add_argument('--dtype', choices=['bfloat16','float16','float32'], default='bfloat16')
    p.add_argument('--device', default='cuda:0')
    p.add_argument('--bricknet-version', choices=['0.1.0','0.1.1'], default='0.1.0')
    p.add_argument('--offline', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    if min(args.num_samples,args.n_per_prompt,args.max_attempts,args.max_new_tokens,args.parts) < 1:
        p.error('Counts must be positive')
    if args.temperature <= 0:
        p.error('temperature must be positive')
    if args.lora_revision and len(args.lora_revision)!=len(args.lora):
        p.error('Supply one lora-revision per lora, or omit all')
    if args.mode=='conditional':
        if not args.prompts:
            p.error('--prompts required for conditional mode')
        prompts = normalize_ids(read_jsonl(args.prompts))
        work = []
        for row in prompts:
            if not row.get('caption','').strip():
                raise ValueError('Missing caption')
            for k in range(args.n_per_prompt):
                sid = row['sample_id'] if args.n_per_prompt==1 else row['sample_id']+f'__rep{k}'
                work.append({**row,'sample_id':sid,'sample':k})
    else:
        work = [{'sample_id':f'unconditional_{i:06d}','id':i,'sample':0} for i in range(args.num_samples)]
    if not work:
        raise ValueError('No prompts')
    plan = {'mode':args.mode,'model':args.model,'lora_in_order':args.lora,'requested_samples':len(work),
        'sampling':args.sampling,'temperature':args.temperature,
        'top_k':20 if args.sampling=='ns' else 0,'top_p':0.95 if args.sampling=='ns' else 1.0,
        'max_new_tokens':args.max_new_tokens,'target_parts':args.parts if args.mode=='unconditional' else None,
        'max_parse_attempts':args.max_attempts if args.mode=='conditional' else 1,'seed':args.seed,
        'dtype':args.dtype,'device':args.device,'input_sha256':sha256(args.prompts) if args.prompts else None,
        'sources':source_hashes(__file__),'rejection_policy':'parse-only; never filter collisions',
        'exact_paper_reproduction':False,'known_difference':'finite retry cap; seeded single-sample generation'}
    if args.dry_run:
        print(json.dumps(plan,indent=2)); return
    import torch
    from transformers import LogitsProcessor, LogitsProcessorList
    bricknet = load_bricknet(args.bricknet_version)
    spec = resolve_hf(args.model,args.revision,args.offline)
    revisions = args.lora_revision or [None]*len(args.lora)
    adapters = [resolve_hf(name,rev,args.offline) for name,rev in zip(args.lora,revisions)]
    config = {**plan,'model_spec':spec,'adapter_specs':adapters,'bricknet_version':bricknet.__version__,
        'packages':packages(['torch','transformers','peft','accelerate','bricknet']),
        'work_sha256':fingerprint(work)}
    accepted = Journal(args.out,config)
    attempts = Journal(args.out.with_name(args.out.stem+'.attempts.jsonl'),config)
    model, tokenizer = load_causal(spec,adapters,args.dtype,args.device,args.offline)
    newline = tokenizer.encode('\n',add_special_tokens=False)
    if len(newline)!=1:
        raise ValueError('Official newline stopping assumes a single newline token')
    eos = tokenizer.eos_token_id
    if eos is None:
        raise ValueError('Tokenizer has no EOS token')
    class StopAtParts(LogitsProcessor):
        def __init__(self, prompt_length):
            self.prompt_length = prompt_length
        def __call__(self, input_ids, scores):
            count = (input_ids[:,self.prompt_length:]==newline[0]).sum(dim=1)
            done = count >= 2*args.parts-1
            scores[~done,eos] = float('-inf')
            scores[done] = float('-inf')
            scores[done,eos] = 0
            return scores
    def generate(row,attempt):
        torch.manual_seed(trial_seed(args.seed,row['sample_id'],attempt))
        ids = (tokenizer.encode(row['caption'],add_special_tokens=False)+newline
               if args.mode=='conditional' else tokenizer.encode('a',add_special_tokens=False))
        inputs = torch.tensor([ids],device=args.device)
        processors = LogitsProcessorList([StopAtParts(len(ids))]) if args.mode=='unconditional' else None
        with torch.inference_mode():
            output = model.generate(inputs,attention_mask=torch.ones_like(inputs),
                max_new_tokens=args.max_new_tokens,do_sample=True,temperature=args.temperature,
                top_k=plan['top_k'],top_p=plan['top_p'],pad_token_id=eos,logits_processor=processors)
        generated = tokenizer.decode(output[0,len(ids):],skip_special_tokens=True)
        return generated if args.mode=='conditional' else 'a'+generated
    def parse(text):
        result = bricknet.parse_sample(text if text.endswith('\n') else text+'\n')
        return {'parse_ok':result.error is None and bool(result.tree.parts),
                'parse_error':result.error,'parts':len(result.tree.parts)}
    missing = []
    for i,row in enumerate(work):
        result = retry_sample(row,generate,parse,attempts,accepted,config,args.max_attempts,args.mode=='conditional')
        if result is None:
            missing.append(row['sample_id'])
        print(f'{i+1}/{len(work)} {row["sample_id"]}: {"selected" if result else "retry cap exhausted"}',flush=True)
    write_json(args.out.with_suffix('.summary.json'),{'requested':len(work),'written':len(accepted.done),
        'total_logged_attempts':len(attempts.done),'retry_exhausted':missing,'complete':not missing,
        'config_signature':accepted.signature})
    if missing:
        raise RuntimeError(f'{len(missing)} prompts exhausted retry cap; outputs are incomplete, not a full evaluation')


if __name__ == '__main__':
    main()
