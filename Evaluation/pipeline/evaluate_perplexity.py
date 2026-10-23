"""Token-weighted PT or caption-conditional path perplexity with overlapping windows."""
import argparse
import json
import math
from pathlib import Path
from paper_common import (Journal, fingerprint, load_causal, normalize_ids, packages, read_jsonl,
                          resolve_hf, sha256, source_hashes, write_json)


def tokenize_sample(tokenizer, path, caption=None):
    prefix = caption+'\n' if caption is not None else ''
    text = prefix+path
    if tokenizer.is_fast:
        data = tokenizer(text,add_special_tokens=False,return_offsets_mapping=True)
        ids = data['input_ids']
        mask = [end>len(prefix) for start,end in data['offset_mapping']]
    else:
        ids = tokenizer.encode(text,add_special_tokens=False)
        head = tokenizer.encode(prefix,add_special_tokens=False)
        if ids[:len(head)] != head:
            raise ValueError('Tokenizer prefix boundary merged; need a fast tokenizer with offsets')
        mask = [i>=len(head) for i in range(len(ids))]
    return ids,mask


def sliding_nll(model, ids, target_mask, window, stride, device):
    import torch
    import torch.nn.functional as F
    if not 0 < stride < window:
        raise ValueError('Need 0 < stride < window to preserve preceding context for each target')
    total, count, previous_end = 0.0,0,0
    for begin in range(0,len(ids),stride):
        end = min(begin+window,len(ids))
        if end <= previous_end:
            break
        inputs = torch.tensor([ids[begin:end]],device=device)
        with torch.inference_mode():
            logits = model(input_ids=inputs,attention_mask=torch.ones_like(inputs),use_cache=False).logits
        # Count every target once, with a preceding token; prefix tokens are never scored.
        positions = [j for j in range(1,end-begin)
                     if begin+j >= previous_end and target_mask[begin+j]]
        for offset in range(0,len(positions),128):
            selected = positions[offset:offset+128]
            if selected:
                total += F.cross_entropy(logits[0,[j-1 for j in selected]].float(),
                    inputs[0,selected],reduction='sum').double().item()
                count += len(selected)
        previous_end = end
        if end == len(ids):
            break
    return total,count


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True,type=Path)
    p.add_argument('--out', required=True,type=Path)
    p.add_argument('--model', required=True)
    p.add_argument('--revision')
    p.add_argument('--lora',action='append',default=[])
    p.add_argument('--lora-revision',action='append',default=[])
    p.add_argument('--conditional',action='store_true',help='Mask caption and separator; score path tokens only')
    p.add_argument('--window',type=int,default=4096)
    p.add_argument('--stride',type=int,default=2048)
    p.add_argument('--include-eos',action='store_true')
    p.add_argument('--dtype',choices=['bfloat16','float16','float32'],default='bfloat16')
    p.add_argument('--device',default='cuda:0')
    p.add_argument('--offline',action='store_true')
    p.add_argument('--dry-run',action='store_true')
    args = p.parse_args()
    if not 0 < args.stride < args.window:
        p.error('Need 0 < stride < window')
    if args.lora_revision and len(args.lora_revision)!=len(args.lora):
        p.error('Supply one lora-revision per lora')
    rows = normalize_ids(read_jsonl(args.input))
    if not rows or any(not isinstance(r.get('path',r.get('text')),str) for r in rows):
        raise ValueError('Need ground-truth path/text records, not GLB or generated samples')
    if args.conditional and any(not r.get('caption','').strip() for r in rows):
        raise ValueError('Conditional PPL requires caption on each ground-truth path')
    plan = {'metric':'conditional_path_perplexity' if args.conditional else 'path_perplexity',
        'model':args.model,'lora_in_order':args.lora,'window':args.window,'stride':args.stride,
        'include_eos':args.include_eos,'dtype':args.dtype,'device':args.device,'samples':len(rows),
        'input_sha256':sha256(args.input),'sources':source_hashes(__file__),
        'exact_paper_reproduction':False,
        'protocol_limit':'Original held-out path selection, window, EOS and tokenization details need confirmation'}
    if args.dry_run:
        print(json.dumps(plan,indent=2)); return
    spec = resolve_hf(args.model,args.revision,args.offline)
    revisions = args.lora_revision or [None]*len(args.lora)
    adapters = [resolve_hf(n,r,args.offline) for n,r in zip(args.lora,revisions)]
    journal = Journal(args.out,{**plan,'model_spec':spec,'adapter_specs':adapters,
        'packages':packages(['torch','transformers','peft'])})
    model,tokenizer = load_causal(spec,adapters,args.dtype,args.device,args.offline)
    context = getattr(model.config,'max_position_embeddings',None)
    if context and args.window>context:
        raise ValueError('Window exceeds model context')
    for row in rows:
        ih = fingerprint(row)
        if journal.cached(row['sample_id'],ih):
            continue
        ids,mask = tokenize_sample(tokenizer,row.get('path',row.get('text')),
                                  row['caption'] if args.conditional else None)
        if args.include_eos:
            if tokenizer.eos_token_id is None:
                raise ValueError('No EOS token')
            ids.append(tokenizer.eos_token_id); mask.append(True)
        nll,tokens = sliding_nll(model,ids,mask,args.window,args.stride,args.device)
        if not tokens:
            raise ValueError(f'{row["sample_id"]}: no scored path tokens')
        journal.append({'sample_id':row['sample_id'],'status':'ok','nll':nll,
            'scored_tokens':tokens,'input_tokens':len(ids),
            'perplexity':math.exp(nll/tokens) if nll/tokens<700 else None},ih)
    nll = sum(r['nll'] for r in journal.done.values())
    count = sum(r['scored_tokens'] for r in journal.done.values())
    write_json(args.out.with_suffix('.summary.json'),{'samples':len(rows),'nll':nll,
        'scored_tokens':count,'mean_token_nll':nll/count,
        'perplexity':math.exp(nll/count) if nll/count<700 else None,
        'aggregation':'exp(sum NLL / sum scored tokens), not mean sample perplexity',
        'config_signature':journal.signature})


if __name__ == '__main__':
    main()
