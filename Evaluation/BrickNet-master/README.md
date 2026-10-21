<div align="center">

# BrickNet: Graph-Backed Generative Brick Assembly

[Peter Kulits](https://kulits.github.io/) and [Cordelia Schmid](https://cordeliaschmid.github.io/)

CVPR 2026

[\[Project Page\]](https://kulits.github.io/BrickNet/) | [\[Models\]](https://huggingface.co/collections/kulits/bricknet)
</div>

This directory keeps only the **evaluation** parts of BrickNet:

- `src/bricknet/` — parse generated path text, realize it into parts, and collision-check it. This produces
  **P_inv**, the proportion of invalid placements (paper Table 3), as well as the connectivity / collision
  survival numbers of Table 2.
- `eval/` — the image–text metrics **PE**, **SigLIP 2** and **VQAScore** computed on object renders; the
  protocol (render shards, pooling, reported value) is in `eval/README.md`.

Generation and training code (`scripts/`) is not included.

## Install

```bash
pip install -e .                  # numpy, scipy, pybullet>=3.2.7, platformdirs
python -m bricknet fetch-meshes   # convex colliders (needed for collision checks)
```

The colliders are stored under `<data dir>/cvx/`, where the data dir is `$BRICKNET_DATA` if set, else the
platform user-data directory.

## P_inv — proportion of invalid placements

```bash
python -m bricknet score samples.jsonl scored.jsonl --workers 8
python -m bricknet score samples.jsonl scored.jsonl --no-collision   # parse only, no meshes needed
```

Input rows are JSONL with the generated path text under `path` (or `text`). Rows pass through with three
fields (re)written:

- `n_actions` — actions attempted in the text (one part per action),
- `invalid` — index of the first unparsable action, or `null`,
- `collisions` — indices of actions whose part collides under autoregressive placement (`null` with
  `--no-collision`).

The printed summary reports the fully parsable and the parsable-and-collision-free rates, plus the mean
number of actions before the first failure.

To look at a generated sample, convert path text to LDraw:

```bash
python -m bricknet path2ldr sample.txt -o model.ldr
python -m bricknet path2ldr out.jsonl -o models/    # one .ldr per generator output row
```

## Image–text metrics

`eval/pe.py`, `eval/siglip2.py` and `eval/vqascore.py` score render shard tarballs against captions; see
`eval/README.md`. They need extra packages on top of `requirements.txt`:
`torch transformers open_clip_torch qwen-vl-utils pillow tqdm`.

## Citation

```bibtex
@InProceedings{Kulits_2026_CVPR,
    author    = {Kulits, Peter and Schmid, Cordelia},
    title     = {BrickNet: Graph-Backed Generative Brick Assembly},
    booktitle = {Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)},
    month     = {June},
    year      = {2026},
    pages     = {39252-39261}
}
```
