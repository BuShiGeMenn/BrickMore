"""Inventory available scripts, source inputs and runtime dependencies; no model loading."""
import argparse
import json
from collections import Counter
from pathlib import Path
from paper_common import packages, sha256, write_json

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = {
    'structure_kernel': 'Evaluation/BrickNet-master/src/bricknet/score.py',
    'released_vqa': 'Evaluation/BrickNet-master/eval/vqascore.py',
    'released_pe': 'Evaluation/BrickNet-master/eval/pe.py',
    'released_siglip2': 'Evaluation/BrickNet-master/eval/siglip2.py',
    'generation_and_retry': 'Evaluation/pipeline/generate_paper_samples.py',
    'structure_and_survival': 'Evaluation/pipeline/evaluate_structure.py',
    'paper_image_scoring': 'Evaluation/pipeline/evaluate_paper_images.py',
    'render_and_tar_adapter': 'Evaluation/pipeline/prepare_paper_inputs.py',
    'perplexity': 'Evaluation/pipeline/evaluate_perplexity.py',
    'report': 'Evaluation/pipeline/report_paper_eval.py',
    'isolated_setup': 'Evaluation/pipeline/setup_paper_environment.cmd',
}


def audit(root=ROOT):
    scripts = {key: {'path': value, 'exists': (root/value).is_file(),
                     'sha256': sha256(root/value) if (root/value).is_file() else None}
               for key, value in REQUIRED.items()}
    model_files = list((root/'Model').rglob('*')) if (root/'Model').exists() else []
    extensions = Counter(p.suffix.lower() for p in model_files if p.is_file())
    structure = [str(p.relative_to(root)) for p in model_files
                 if p.is_file() and p.suffix.lower() in {'.ldr', '.mpd', '.jsonl', '.npz', '.txt'}]
    return {'scripts': scripts, 'missing_scripts': [k for k,v in scripts.items() if not v['exists']],
            'model_extensions': dict(extensions), 'potential_structure_inputs': structure,
            'packages': packages(['bricknet','meshlib','numpy','scipy','platformdirs','torch',
                                  'transformers','accelerate','peft','qwen-vl-utils','open_clip_torch',
                                  'bricknet-render','bpy']),
            'limitations': ['GLB is not generated BrickNet path text.',
                'Official 512 validation samples require data access.',
                'Original collision numbers require bricknet 0.1.0 + inset meshes.',
                'Paper says Qwen2.5-VL-7B; released eval code uses Qwen2-VL-7B.',
                'The published P_inv macro/micro aggregation is not specified in available code.']}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path)
    args = p.parse_args()
    result = audit()
    if args.out:
        write_json(args.out, result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
