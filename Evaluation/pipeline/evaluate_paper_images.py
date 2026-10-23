"""Eight-view VQA/PE/SigLIP2 with explicit paper-text, released-code and local presets."""
import argparse
import json
import re
import time
from pathlib import Path
from paper_common import (Journal, fingerprint, normalize_ids, packages, pooled, read_jsonl,
                          resolve_hf, sha256, source_hashes, write_json)
from prepare_paper_inputs import validated_views

PRESETS = {
    'paper-text': {'vqa':'Qwen/Qwen2.5-VL-7B-Instruct',
                  'pe':'timm/PE-Core-bigG-14-448',
                  'siglip2':'google/siglip2-giant-opt-patch16-384'},
    'released-code': {'vqa':'Qwen/Qwen2-VL-7B-Instruct',
                     'pe':'timm/PE-Core-bigG-14-448',
                     'siglip2':'google/siglip2-giant-opt-patch16-384'},
    'local': {'vqa':'Qwen/Qwen2-VL-2B-Instruct',
              'pe':'timm/PE-Core-B-16','siglip2':'google/siglip2-base-patch16-224'},
}


def build_question(caption):
    return 'Is this LEGO set '+re.sub(r'[.!?]+$', '', ' '.join(caption.split())).lower()+'?'


def single_yes_id(tokenizer):
    tokens = tokenizer.encode('Yes', add_special_tokens=False)
    if len(tokens) != 1 or tokenizer.decode(tokens) != 'Yes':
        raise ValueError('Yes is not exactly one round-tripping token; another scoring protocol is required')
    return tokens[0]


def yes_probability(logits, yes_id):
    # Full-vocabulary softmax, not Yes/No renormalization; preserve low probabilities.
    return logits.float().softmax(dim=-1)[...,yes_id]


def create_scorer(args, spec):
    import torch
    kw = {'revision':spec['revision'], 'local_files_only':args.offline}
    dtype = getattr(torch, args.dtype)
    if args.metric == 'vqa':
        from transformers import AutoConfig, AutoProcessor, Qwen2VLForConditionalGeneration, Qwen2_5_VLForConditionalGeneration
        from qwen_vl_utils import process_vision_info
        cfg = AutoConfig.from_pretrained(spec['model'], **kw)
        classes = {'qwen2_vl':Qwen2VLForConditionalGeneration,
                   'qwen2_5_vl':Qwen2_5_VLForConditionalGeneration}
        if cfg.model_type not in classes:
            raise ValueError(f'Unsupported VQA model type: {cfg.model_type}')
        extra = {'attn_implementation':'sdpa', 'dtype':dtype}
        if args.quantize_4bit:
            from transformers import BitsAndBytesConfig
            if not args.device.startswith('cuda'):
                raise ValueError('4-bit preset requires CUDA and a compatible bitsandbytes backend')
            extra.update(quantization_config=BitsAndBytesConfig(load_in_4bit=True,
                bnb_4bit_quant_type='nf4', bnb_4bit_compute_dtype=dtype), device_map={'':args.device})
        model = classes[cfg.model_type].from_pretrained(spec['model'], **kw, **extra).eval()
        if not args.quantize_4bit:
            model = model.to(args.device)
        pixel_kw = {}
        if args.min_pixels is not None:
            pixel_kw['min_pixels'] = args.min_pixels
        if args.max_pixels is not None:
            pixel_kw['max_pixels'] = args.max_pixels
        processor = AutoProcessor.from_pretrained(spec['model'], use_fast=False, **kw, **pixel_kw)
        yes_id = single_yes_id(processor.tokenizer)

        def compute(images, caption):
            question = build_question(caption)
            messages = [[{'role':'user','content':[{'type':'image','image':im},
                          {'type':'text','text':question}]}] for im in images]
            texts = [processor.apply_chat_template(m,tokenize=False,add_generation_prompt=True) for m in messages]
            visual = process_vision_info(messages)
            inputs = processor(text=texts, images=visual[0], videos=visual[1],
                               padding=True, return_tensors='pt').to(args.device)
            token_count = int(inputs.attention_mask.sum(dim=-1).max())
            max_positions = getattr(model.config,'max_position_embeddings',None)
            if max_positions and token_count+1 > max_positions:
                raise ValueError('VQA input exceeds model context; refusing implicit text truncation')
            outputs = model.generate(**inputs, max_new_tokens=1, do_sample=False,
                output_scores=True, return_dict_in_generate=True)
            values = yes_probability(outputs.scores[0], yes_id).cpu().tolist()
            return values, {'question':question,'input_tokens_max':token_count,
                'image_grid_thw':inputs.image_grid_thw.cpu().tolist()}
        details = {'model_type':cfg.model_type,'yes_token_id':yes_id,
                   'processor':processor.to_dict() if hasattr(processor,'to_dict') else str(type(processor)),
                   'generation_config':model.generation_config.to_dict()}
    elif args.metric == 'siglip2':
        from transformers import AutoModel, AutoProcessor
        model = AutoModel.from_pretrained(spec['model'], dtype=dtype, **kw).to(args.device).eval()
        processor = AutoProcessor.from_pretrained(spec['model'], use_fast=False, **kw)
        def compute(images, caption):
            count = len(processor.tokenizer(caption, truncation=False)['input_ids'])
            inputs = processor(images=images,text=[caption],padding='max_length',
                truncation=True,max_length=64,return_tensors='pt')
            inputs = {k:v.to(args.device,dtype=dtype) if v.is_floating_point() else v.to(args.device)
                      for k,v in inputs.items()}
            values = model(**inputs).logits_per_image[:,0].float().sigmoid().cpu().tolist()
            return values, {'text_tokens':count,'text_truncated':count>64}
        details = {'image_size':model.config.vision_config.image_size,'text_context_length':64}
    else:
        import open_clip
        from huggingface_hub import snapshot_download
        local = Path(spec['model'])
        if not local.is_dir():
            local = Path(snapshot_download(spec['model'],revision=spec['revision'],
                local_files_only=args.offline,
                allow_patterns=['*.json','*.txt','*.model','*.safetensors']))
        name = 'local-dir:'+local.resolve().as_posix()
        model,_,preprocess = open_clip.create_model_and_transforms(name)
        model = model.to(device=args.device,dtype=dtype).eval()
        tokenizer = open_clip.get_tokenizer(name)
        def compute(images, caption):
            count = len(tokenizer.encode(caption))+2
            pixels = torch.stack([preprocess(im) for im in images]).to(args.device,dtype=dtype)
            text = tokenizer([caption]).to(args.device)
            # Original PE script uses autocast on CUDA; retain FP32 reductions for precision.
            from contextlib import nullcontext
            context = torch.autocast('cuda',dtype=torch.float16) if args.device.startswith('cuda') else nullcontext()
            with context:
                a = model.encode_image(pixels,normalize=True)
                b = model.encode_text(text,normalize=True)
            a = torch.nn.functional.normalize(a.float(),dim=-1)
            b = torch.nn.functional.normalize(b.float(),dim=-1)
            return (a@b.T)[:,0].cpu().tolist(), {'text_tokens':count,'text_truncated':count>model.context_length}
        details = {'image_size':model.visual.image_size,'text_context_length':model.context_length}
    return compute, details


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--renders', required=True, type=Path, help='Existing renders.jsonl; views relative to its parent')
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--metric', required=True, choices=['vqa','pe','siglip2'])
    p.add_argument('--preset', choices=PRESETS, default='paper-text')
    p.add_argument('--model', help='Override repository or local directory; recorded as an adaptation')
    p.add_argument('--revision')
    p.add_argument('--dtype', choices=['float32','float16','bfloat16'])
    p.add_argument('--device', default='cuda:0')
    p.add_argument('--batch-size', type=int, default=1, help='View batch, not eight-image VQA conversation')
    p.add_argument('--min-pixels', type=int)
    p.add_argument('--max-pixels', type=int)
    p.add_argument('--quantize-4bit', action='store_true')
    p.add_argument('--offline', action='store_true')
    p.add_argument('--limit', type=int)
    p.add_argument('--dry-run', action='store_true', help='Validate images and show plan without model downloads')
    args = p.parse_args()
    if args.batch_size < 1 or (args.limit is not None and args.limit < 1):
        p.error('batch-size and limit must be positive')
    if args.quantize_4bit and args.metric != 'vqa':
        p.error('--quantize-4bit is only supported for VQA')
    args.model = args.model or PRESETS[args.preset][args.metric]
    args.dtype = args.dtype or ('float32' if args.metric=='pe' else 'bfloat16')
    if args.preset == 'local' and args.metric=='vqa' and args.max_pixels is None:
        args.max_pixels, args.min_pixels = 256*28*28, args.min_pixels or 64*28*28
    if args.min_pixels is not None and args.min_pixels < 1 or args.max_pixels is not None and args.max_pixels < 1:
        p.error('pixel budgets must be positive')
    if args.min_pixels and args.max_pixels and args.min_pixels > args.max_pixels:
        p.error('min-pixels exceeds max-pixels')
    rows = normalize_ids(read_jsonl(args.renders))
    if args.limit:
        rows = rows[:args.limit]
    if not rows:
        raise ValueError('No rendered samples')
    checked = []
    for row in rows:
        if not row.get('caption','').strip():
            raise ValueError('Missing original caption')
        paths, hashes = validated_views(row, args.renders.parent)
        checked.append((row,paths,hashes))
    plan = {'metric':args.metric,'preset':args.preset,'model':args.model,
        'requested_revision':args.revision,'dtype':args.dtype,'device':args.device,
        'view_batch_size':args.batch_size,'min_pixels':args.min_pixels,'max_pixels':args.max_pixels,
        'quantization':'bitsandbytes-nf4' if args.quantize_4bit else None,
        'samples':len(rows),'view_evaluations':len(rows)*8,'pooling':'max-of-8 then mean-over-models',
        'paper_code_model_discrepancy':'Qwen2.5-VL-7B in paper vs Qwen2-VL-7B in released code',
        'exact_paper_reproduction':False,
        'remaining_protocol_limits':['historical rendering match not verified',
                                    'paper/code VQA discrepancy not resolved'],
        'input_manifest_sha256':sha256(args.renders),'sources':source_hashes(__file__,Path(__file__).with_name('prepare_paper_inputs.py'))}
    if args.dry_run:
        print(json.dumps(plan,indent=2)); return
    import torch
    from PIL import Image
    torch.set_num_threads(4)
    if args.device.startswith('cuda') and not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    spec = resolve_hf(args.model,args.revision,args.offline)
    config = {**plan,'resolved_model':spec,
        'packages':packages(['torch','torchvision','transformers','open_clip_torch','timm',
                             'pillow','qwen-vl-utils','accelerate','bitsandbytes']),
        'device_name':torch.cuda.get_device_name(args.device) if args.device.startswith('cuda') else 'CPU'}
    # Check provenance before allocating the model.
    journal = Journal(args.out, config)
    compute, details = create_scorer(args,spec)
    write_json(args.out.with_suffix('.model.json'),details)
    if args.device.startswith('cuda'):
        torch.cuda.reset_peak_memory_stats(args.device)
    start = time.monotonic()
    for index,(row,paths,hashes) in enumerate(checked):
        ih = fingerprint({'row':row,'actual_view_sha256':hashes})
        if journal.cached(row['sample_id'],ih):
            continue
        scores, diagnostics = [], []
        with torch.inference_mode():
            for offset in range(0,8,args.batch_size):
                images = []
                for path in paths[offset:offset+args.batch_size]:
                    with Image.open(path) as im:
                        images.append(im.convert('RGB'))
                values, info = compute(images,row['caption'])
                scores.extend(values)
                diagnostics.append(info)
        journal.append({**{k:v for k,v in row.items() if k not in {'scores','max_score','mean_score'}},
            'metric':args.metric,'preset':args.preset,'status':'ok',**pooled(scores),
            'diagnostics':diagnostics},ih)
        print(f'{index+1}/{len(rows)} {row["sample_id"]} {max(scores):.6f}',flush=True)
    if args.device.startswith('cuda'):
        torch.cuda.synchronize(args.device)
    results = [journal.done[r['sample_id']] for r in rows]
    write_json(args.out.with_suffix('.summary.json'),{'metric':args.metric,'samples':len(results),
        'mean_of_max_scores':sum(r['max_score'] for r in results)/len(results),
        'elapsed_seconds_this_invocation':time.monotonic()-start,
        'peak_allocated_mib':torch.cuda.max_memory_allocated(args.device)/2**20 if args.device.startswith('cuda') else None,
        'config_signature':journal.signature})


if __name__ == '__main__':
    main()
