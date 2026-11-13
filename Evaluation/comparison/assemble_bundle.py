"""Stage portable scripts, instructions and immutable checksums around the audited data."""
import argparse,json,shutil,tarfile
from pathlib import Path
from common import sha

SOURCE=Path(__file__).resolve().parent
WORKSPACE=SOURCE.parents[1]
CPU='''bricknet==0.1.0
numpy==2.2.6
scipy==1.15.3
meshlib==3.1.4.297
platformdirs==4.4.0
numba==0.61.2
llvmlite==0.44.0
pillow==11.3.0
'''
GPU='''torch>=2.6,<2.9
torchvision>=0.21,<0.24
transformers==4.57.1
accelerate==1.10.1
qwen-vl-utils==0.0.14
open_clip_torch==3.2.0
timm==1.0.22
pillow>=11.3
sentencepiece>=0.2.0
protobuf>=5
'''
ENV='''#!/usr/bin/env bash
export PYTHONUTF8=1 PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 TBB_NUM_THREADS=1
export PYTHONFAULTHANDLER=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
if [[ -f "$BRICKMORE_BUNDLE_ROOT/environment.local.sh" ]]; then
  source "$BRICKMORE_BUNDLE_ROOT/environment.local.sh"
elif [[ "${BRICKMORE_LOAD_OLD_RUNTIME:-1}" == 1 && -f /mnt/brickmore-data/brickmore-jrd-20261025/use-runtime.sh ]]; then
  set +u
  source /mnt/brickmore-data/brickmore-jrd-20261025/use-runtime.sh
  set -u
fi
cd "$BRICKMORE_BUNDLE_ROOT"
if [[ -n "${GPU_PYTHON:-}" ]]; then BRICKMORE_LAUNCHER="$GPU_PYTHON"
elif [[ -n "${BRICKMORE_ENV:-}" && -x "$BRICKMORE_ENV/bin/python" ]]; then BRICKMORE_LAUNCHER="$BRICKMORE_ENV/bin/python"
else BRICKMORE_LAUNCHER="$(command -v python3 || command -v python)"; fi
export BRICKMORE_LAUNCHER
'''
RUN='''#!/usr/bin/env bash
set -Eeuo pipefail
BRICKMORE_BUNDLE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$BRICKMORE_BUNDLE_ROOT/Scripts/environment.sh"
if [[ "${1:-}" == fetch ]]; then shift; exec "$BRICKMORE_LAUNCHER" -X utf8 Scripts/fetch.py "$@"; fi
exec "$BRICKMORE_LAUNCHER" -X utf8 Scripts/run_comparison.py "$@"
'''
SETUP='''#!/usr/bin/env bash
set -Eeuo pipefail
BRICKMORE_BUNDLE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$BRICKMORE_BUNDLE_ROOT/Scripts/environment.sh"
mkdir -p .runtime Downloads/wheels Downloads/models
if "$BRICKMORE_LAUNCHER" -X utf8 Scripts/doctor.py; then exit 0; fi
if "$BRICKMORE_LAUNCHER" -c 'import json,sys; r=json.load(open(".runtime/environment.json"))["roles"]; sys.exit(0 if not r["structure"] or not r["render"] else 1)'; then
  if [[ "${1:---offline}" == --online ]]; then "$BRICKMORE_LAUNCHER" Scripts/fetch.py wheels; fi
  if ! compgen -G 'Downloads/wheels/*.whl' >/dev/null; then
    echo 'CPU dependencies missing. On the connected transfer host run: python Scripts/fetch.py wheels'
    echo 'Copy Downloads/wheels back into this folder and rerun: bash setup.sh --offline'; exit 2
  fi
  "$BRICKMORE_LAUNCHER" -X utf8 Scripts/verify_downloads.py Downloads/wheels
  BRICKMORE_CPU_BASE="$(command -v python3.12 || true)"
  if [[ -z "$BRICKMORE_CPU_BASE" ]]; then BRICKMORE_CPU_BASE="$BRICKMORE_LAUNCHER"; fi
  "$BRICKMORE_CPU_BASE" -c 'import sys; assert sys.version_info[:2]==(3,12), "Offline CPU wheels require Python 3.12"'
  if [[ ! -x .runtime/cpu/bin/python ]]; then "$BRICKMORE_CPU_BASE" -m venv .runtime/cpu; fi
  .runtime/cpu/bin/python -m pip install --no-index --find-links Downloads/wheels -r requirements-cpu.txt
  export CPU_PYTHON="$BRICKMORE_BUNDLE_ROOT/.runtime/cpu/bin/python"
fi
if [[ "${1:---offline}" == --online ]]; then
  BRICKMORE_MISSING_MODELS="$("$BRICKMORE_LAUNCHER" -c 'import json; d=json.load(open(".runtime/environment.json")); print(" ".join(m for m in ["vqa","pe","siglip2"] if d.get("roles",{}).get("gpu") and not d.get("models",{}).get(m,{}).get("ok")))')"
  if [[ -n "$BRICKMORE_MISSING_MODELS" ]]; then "$BRICKMORE_LAUNCHER" Scripts/fetch.py models --metrics $BRICKMORE_MISSING_MODELS; fi
fi
"$BRICKMORE_LAUNCHER" -X utf8 Scripts/doctor.py
'''
README='''# BrickMore / BrickGPT / BrickNet：四项服务器测评包

本包用于“电脑 → 向日葵堡垒机 → 内网服务器”的手动传输流程。本次没有连接服务器，也没有把历史分数当成新结果。

## 数据与对照口径

- 114 条相同英文 prompt（A/B 各 57），覆盖 21 类、105 个正式类别×Level 组。
- 主对照 342 条：三个系统各 114 条。BrickMore 在跑分前固定使用 A/B 清单第一个 model_ids，优先最终 stitched，否则 raw；不按分数挑最好样本。
- 全量 462 条：BrickMore 234、BrickGPT 114、BrickNet 114。额外候选、raw/stitched 对照、4 个未归档等级汽车试作保留为补充数据。交接目录的重复副本、未引用历史淘汰文件不重复计数。
- 原目录 `BrickGPT/A_ldr_57.zip`、`B_ldr_57.zip` 实际是 BrickNet，已根据生成总结正确标注；外层“BrickGPT原版”数据是 BrickGPT。
- 324 种真实零件的原版 inset 碰撞网格和统一渲染网格已随包携带，无需内网下载完整零件库。
- 部分 Raw GLB 为无节点名的程序化方砖网格：采用完整 12 三角形砖体、20 种合法尺寸和全部剩余顶面凸点包络校验恢复；1900 项带节点 GLB 的局部边界也已独立核对。水平格距统一为 20 LDU、砖高 24 LDU；相关源显示高度约定的转换在逐条记录中保留。

## 首次上传和环境检查

上传 `.tar.gz` 与同名 `.sha256` 到新的独立目录，不覆盖旧评测。

```bash
sha256sum -c brickmore-three-models-four-scores-20261110.tar.gz.sha256
tar -xzf brickmore-three-models-four-scores-20261110.tar.gz
cd BrickMoreComparison
bash run.sh verify
bash run.sh doctor
bash setup.sh --offline
bash run.sh dry-run
```

自动尝试复用原 `/mnt/brickmore-data/brickmore-jrd-20261025/use-runtime.sh` 中的环境与 HF 缓存。不会自动升级已有 GPU 环境，也不会在评分时偷偷联网下载。

若自动定位不适用，复制 `environment.local.sh.example` 为 `environment.local.sh`，填入现有解释器和缓存路径。也可对每次命令传入 `--gpu-python`、`--structure-python`、`--render-python`。

Doctor 检查：解释器与依赖、BrickNet 0.1.0、CUDA/GPU 空闲显存、324 种零件资源、三项评分模型配置及权重分片。输出 `.runtime/environment.json`，缺失时停止在重计算之前。

## 内网缺失项：在联网中转端补齐

把测评包也解压在联网电脑/堡垒机。以下下载器仅用 Python 标准库，支持 Windows 和 Linux；完整文件校验后跳过，`.part` 会保留，断网后指数退避重试、HTTP Range 续传，最终校验 SHA-256 / Git blob hash。

```bash
# Linux x86_64、CPython 3.12 的完整 CPU wheel 集；可在 Windows 下载
python Scripts/fetch.py wheels

# 只补 doctor 列出的缺失大模型；已有服务器缓存无需重复下载
python Scripts/fetch.py models --metrics vqa pe siglip2
# 如需替代端点，可追加 --endpoint https://hf-mirror.com
```

把生成的 `Downloads/wheels/` 和缺失的 `Downloads/models/<指标>/` 原样转入内网解压目录，再执行 `bash setup.sh --offline`。大模型权重未包含在主上传包中；三个模型合计可能占用数十 GB，确认缺失后再补。

GPU 依赖如需新装，在匹配的联网 Linux/WSL Python 环境生成二进制 wheel 下载计划（同样用持久断点下载器下载实际 payload）：

```bash
python Scripts/fetch.py pip-plan --python /path/to/python3.12
```

然后转入 `Downloads/gpu_wheels/`，用目标 GPU 解释器运行 `python Scripts/verify_downloads.py Downloads/gpu_wheels`，再用 `python -m pip install --no-index --find-links Downloads/gpu_wheels -r requirements-gpu.txt`。保留原有可用 Torch/CUDA，不要无版本限制升级环境。Windows 的 CPU wheel 模式不能代替完整 Linux GPU 依赖解析。

## 小样本、全量与终端进度

```bash
bash run.sh smoke --workers 1
tmux new -s brickmore_compare
bash run.sh full --workers 1
```

Smoke 使用六条覆盖三模型、GLB/LDR 与新旧结构的记录，共 48 视角。全量默认为 462 条、3696 张图；若只跑严格配对主实验，用新的输出目录：

```bash
bash run.sh full --scope primary --workers 1 --out Results/comparison_primary
```

终端显示当前阶段、完成数、百分比、耗时、ETA、当前模型或视角。初始化加载时 ETA 显示 `--`，同时持续心跳；每阶段完整输出保存在对应 `.log`，总体状态在 `progress.json`。

```bash
bash run.sh status --watch
tail -f Results/comparison_full/vqa.log
```

流程：输入校验 → 环境检查 → P_inv → 八视角渲染 → VQA → PE → SigLIP2 → 分类/等级及严格三方配对汇总。
Ctrl+B 后按 D 离开 tmux；Ctrl+C 会停止任务。中断后用**相同命令、相同 `--out` 和配置**续跑，已完成记录校验后复用。更改输入、作用范围或配置时须用新的输出目录，防止混分。

仅做 CPU 预检查可用 `bash run.sh smoke --cpu-only`；它不代表三项 GPU 评分通过。

## 输出与回传

```bash
bash run.sh export
# 自定义目录则加 --out Results/comparison_primary
```

回传 `Results/comparison_full-results.tar.gz` 和同名校验文件。解压后打开 `report/report.html`；逐模型、分类/Level、严格同 prompt 三方比较分别保存在 `report/scores.csv`、`by_category_level.csv`、`summary.json`。

## 指标边界

- P_inv 明确为 `pinv_file_order`：使用原版 BrickNet 0.1.0、inset 网格、逐记录顺序放置的无效比例。GLB/LDR 导出顺序不冒充已验证的原始生成顺序；三种模型均不使用 FixedEdge 免碰撞豁免。保留 macro/micro，缺网格/计算失败为 NA，不补零。
- VQA 使用 Qwen2.5-VL-7B-Instruct；PE 为 PE-Core-bigG-14-448；SigLIP2 为 giant-opt-patch16-384。八视角取最大值，再对模型平均；保留每视角值和截断诊断，不合成未经验证的“综合分”。
- 三模型全部使用同一真实零件网格、相机、灯光与统一黄色。该 CPU 渲染协议是适配版本，不能与旧服务器/论文数字直接混合；统一颜色也不能验证原始配色准确性。
- 生成阶段的稳定性标签保留，不以“是否通过生成过滤”再筛测评样本；图文分数、碰撞分数均不能自动认定人工外形合格或物理稳定。

## 旧服务器数据定位摘要（来自历史聊天，未连接复核）

原四项包：`brickmore-eval630-four-scores-20261027.tar.gz`，630 候选、1243 版本（Raw 620、Stitched 623）。
历史全量目录：`/mnt/brickmore-data/brickmore-jrd-20261025/uploads/eval630-20261027/BrickMoreEval630/Results/eval630_full_v2/`。
更早 918 模型三项图文目录：`/mnt/brickmore-data/brickmore-jrd-20261025/BrickMore/Results/server_paper_full_20261026/`。
P_inv 后来另做过 917/918 GLB 结构结果。旧包、旧结果在当前工作区并不完整，本次没有据此虚构现存服务器文件或重用其分数。
'''

def stage(out):
    scripts=out/'Scripts';scripts.mkdir(exist_ok=True)
    for p in SOURCE.glob('*.py'):
        if p.name not in {'build_inputs.py','assemble_bundle.py'}:shutil.copy2(p,scripts/p.name)
    for name in ['paper_common.py','prepare_paper_inputs.py','evaluate_paper_images.py']:
        shutil.copy2(WORKSPACE/'Evaluation/pipeline'/name,scripts/name)
    p=scripts/'paper_common.py';text=p.read_text(encoding='utf-8')
    marker="    opener = lzma.open if Path(path).suffix == '.xz' else open"
    assert marker in text
    text=text.replace(marker,"    if Path(path).suffix != '.xz':\n        from common import rows as recoverable_rows\n        return recoverable_rows(path)\n"+marker)
    marker='            stream.flush()\n        self.done[sid] = row'
    assert marker in text
    text=text.replace(marker,'            stream.flush()\n            os.fsync(stream.fileno())\n        self.done[sid] = row')
    p.write_text(text,encoding='utf-8')
    p=scripts/'evaluate_paper_images.py';text=p.read_text(encoding='utf-8')
    old="processor.to_dict() if hasattr(processor,'to_dict') else str(type(processor))"
    assert old in text
    text=text.replace(old,"{'class':type(processor).__name__, 'tokenizer_class':type(processor.tokenizer).__name__, 'image_processor_class':type(processor.image_processor).__name__}")
    marker='    compute, details = create_scorer(args,spec)'
    skip='''    all_cached = all(journal.cached(row['sample_id'], fingerprint({'row':row,'actual_view_sha256':hashes})) for row,paths,hashes in checked)
    if all_cached:
        print(f'{len(rows)}/{len(rows)} CACHED_ALL',flush=True)
        return
'''
    assert marker in text;text=text.replace(marker,skip+marker);p.write_text(text,encoding='utf-8')
    files={'run.sh':RUN,'setup.sh':SETUP,'Scripts/environment.sh':ENV,'requirements-cpu.txt':CPU,'requirements-gpu.txt':GPU,'README_服务器运行.md':README,
        'environment.local.sh.example':'# Copy to environment.local.sh and edit only if auto-detection fails.\n# export GPU_PYTHON=/path/to/gpu-env/bin/python\n# export CPU_PYTHON=/path/to/cpu-env/bin/python\n# export RENDER_PYTHON=/path/to/render-env/bin/python\n# export HF_HOME=/path/to/existing/huggingface\n# export BRICKMORE_LOAD_OLD_RUNTIME=0\n'}
    # Windows text-mode writes translate LF back to CRLF. Write bytes so Linux
    # shell options and variable values never acquire a trailing carriage return.
    for name,content in files.items():(out/name).write_bytes(content.replace('\r\n','\n').encode('utf-8'))

def pack(out):
    excluded={'Results','Downloads','.runtime','__pycache__'}
    files=[p for p in out.rglob('*') if p.is_file() and not any(part in excluded for part in p.relative_to(out).parts) and p.name!='CHECKSUMS.sha256']
    (out/'CHECKSUMS.sha256').write_bytes(''.join(sha(p)+'  '+p.relative_to(out).as_posix()+'\n' for p in sorted(files)).encode('utf-8'))
    archive=WORKSPACE/'Deploy/brickmore-three-models-four-scores-20261110.tar.gz'
    with tarfile.open(archive,'w:gz',compresslevel=6) as tar:
        for p in sorted(files+[out/'CHECKSUMS.sha256']):
            info=tar.gettarinfo(str(p),arcname='BrickMoreComparison/'+p.relative_to(out).as_posix());info.mode=0o755 if p.suffix=='.sh' else 0o644
            with p.open('rb') as stream:tar.addfile(info,stream)
    archive.with_name(archive.name+'.sha256').write_bytes((sha(archive)+'  '+archive.name+'\n').encode('ascii'))
    shutil.copy2(out/'README_服务器运行.md',WORKSPACE/'Deploy/README_三模型四项测评_20261110.md')
    print('PACKAGED',archive,archive.stat().st_size,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--stage-only',action='store_true');a=p.parse_args();stage(a.out.resolve())
    if not a.stage_only:pack(a.out.resolve())
