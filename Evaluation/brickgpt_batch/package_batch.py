"""Build a Linux-friendly deployment archive for A prompts 130 through 260."""

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import urllib.request

from checkpoints import atomic_write, file_hash, save_json

HERE = Path(__file__).resolve().parent
UPSTREAM = '9c53c7cb65f9de0df89562cc74b2d2e270fbcab4'
UPSTREAM_URL = 'https://github.com/AvaLovelace1/BrickGPT'
STEM = 'brickgpt-A130-A260-20261115'
WHEELS = {
    'peft-0.17.1-py3-none-any.whl': ('49/fe/a2da1627aa9cb6310b6034598363bd26ac301c4a99d21f415b1b2855891e',
                                   '3d129d64def3d74779c32a080d2567e5f7b674e77d546e3585138216d903f99e'),
    'accelerate-1.10.1-py3-none-any.whl': ('5f/a0/d9ef19f780f319c21ee90ecfef4431cbeeca95bec7f14071785c17b6029b',
                                         '3621cff60b9a27ce798857ece05e2b9f56fcc71631cfb31ccf71f0359c311f11'),
    'networkx-3.4.2-py3-none-any.whl': ('b9/54/dd730b32ea14ea797530a4479b2ed46a6fb250f682a9cfb997e968bf0261',
                                       'df5d4365b724cf81b8c6a7312509d0c22386097011ad1abe274afd5e9d3bbc5f'),
}

RUN = '''#!/usr/bin/env bash
set -Eeuo pipefail
PACKAGE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PACKAGE_ROOT"
OLD_RUNTIME=/mnt/brickmore-data/brickmore-jrd-20261025/use-runtime.sh
if [[ "${BRICKGPT_LOAD_OLD_RUNTIME:-1}" == 1 && -r "$OLD_RUNTIME" ]]; then
    set +u
    source "$OLD_RUNTIME"
    set -u
    cd "$PACKAGE_ROOT"
fi
PY="${BRICKGPT_PYTHON:-}"
if [[ -z "$PY" ]]; then
    if [[ -n "${BRICKMORE_ENV:-}" && -x "$BRICKMORE_ENV/bin/python" ]]; then
        PY="$BRICKMORE_ENV/bin/python"
    elif [[ -x /mnt/brickmore-data/brickmore-jrd-20261025/runtime/envs/paper/bin/python ]]; then
        PY=/mnt/brickmore-data/brickmore-jrd-20261025/runtime/envs/paper/bin/python
    else
        PY=python3
    fi
fi
export PYTHONUTF8=1 PYTHONUNBUFFERED=1
mkdir -p .runtime/tmp
export TMPDIR="$PWD/.runtime/tmp"
if [[ "${1:-}" == deps ]]; then
    "$PY" Scripts/batch.py verify
    exec "$PY" -m pip --disable-pip-version-check install --no-index --no-deps --target "$PWD/.runtime/deps" VendorsWheels/*.whl
fi
exec "$PY" Scripts/batch.py "$@"
'''

SETUP = '''#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ "${1:-}" == --offline ]]; then shift; fi
bash run.sh doctor "$@"
'''

README = '''# BrickGPT A 组第 130–260 条服务器生成包

本包使用已确认的两端包含范围，共 131 条提示词。第 130 条是 A26 单反相机 L5，第 260 条是 A52 拖船 L5。`Data/prompts.json` 保留原始英文文本、源文件行号、对象编号、Level 和输出文件名。

## 手动上传和环境检查

将 `.tar.gz` 和 `.sha256` 一起上传到数据分区的新目录，例如 `/mnt/brickmore-data/brickmore-jrd-20261025/uploads/brickgpt-a130-a260-20261115`。在上传目录运行：

```bash
df -hT .
sha256sum -c brickgpt-A130-A260-20261115.tar.gz.sha256 && tar -xzf brickgpt-A130-A260-20261115.tar.gz && cd BrickGPT_A130_A260
bash setup.sh --offline
```

脚本优先复用上次的服务器 `paper` Python 环境。`doctor` 检查 Python、CUDA、空闲显存、可用空间、推理依赖、权重文件和分词器。报告保存在 `.runtime/environment.json`。检查期间禁用联网。

如果报告只缺 `peft`、`accelerate` 或 `networkx`，可使用包里的离线 wheel：

```bash
bash run.sh deps
bash setup.sh --offline
```

wheel 安装在本包 `.runtime/deps`。如果缺 PyTorch、Transformers 或其他底层依赖，请设置 `BRICKGPT_PYTHON` 为具备这些依赖的 CUDA Python 解释器，再次执行检查。

## 检查和复用模型权重

预检会检查 `Downloads/models`、Hugging Face 缓存（含已保存的 commit 快照）、历史运行目录及常见本地合并权重目录。复用方式有两种：

- 原版 BrickGPT 已合并的 Llama 3.2 1B 权重。若预检找不到现有目录，在同一终端运行 `export BRICKGPT_MERGED=/实际路径/brickgpt_merged`，然后重跑检查。
- 官方 `AvaLovelace/BrickGPT` LoRA 加上 `meta-llama/Llama-3.2-1B-Instruct` 基座。外部目录可用 `BRICKGPT_BASE`、`BRICKGPT_ADAPTER` 指定。包内默认路径是 `Downloads/models/base`、`Downloads/models/adapter`。

有 `ENVIRONMENT READY` 就可运行小样本。若缺权重，优先核对旧机器或其他数据分区是否已有所需文件。

## 补下载权重

服务器能访问 Hugging Face 时，在包目录运行：

```bash
bash run.sh download
```

默认只下载未找到的组件。终端显示文件序号、进度、速度、ETA 和重连次数。已完成文件校验后跳过，半截文件和下载信息保存在 `.part`、`.part.json`。断网或 Ctrl+C 后用同样的命令续传。下载完成后再运行 `bash setup.sh --offline`。

内网服务器无法访问 Hugging Face 时，将本包也解压到联网电脑。用 PowerShell 或 Bash 在包目录运行：

```text
python Scripts/batch.py download --component adapter
python Scripts/batch.py download --component base
```

只运行缺失组件对应的命令。将补好的 `Downloads/models/adapter` 或 `Downloads/models/base` 整个目录转入服务器的对应路径。公网适配器和分词器合计约 31 MB，基座约 2.5 GB。仅在缺基座时，需要用已获授权的 Hugging Face 账号登录联网电脑的 HF CLI，或用该账号的只读 token 设置 `HF_TOKEN`。Token 只需在联网下载环境使用。[Llama 基座授权页](https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct)

## 生成、续跑与导出

环境检查通过后，在当前包目录执行：

```bash
bash run.sh smoke
bash run.sh full
```

`smoke` 跑第 130 条。它的结果会被 `full` 复用。模型载入和单条生成期间有终端心跳，生成完每条会立即保存，终端显示完成数、百分比与 ETA。首个模型完成后才有 ETA。

有 `tmux` 时可先执行 `tmux new -s brickgpt131`，再在会话内运行 `bash run.sh full`。按 `Ctrl+B` 再按 `D` 可离开会话，重新登录后用 `tmux attach -t brickgpt131` 查看。也可以在包目录另开终端执行 `bash run.sh status --watch`。

中断后使用相同命令、模型路径、设备和输出目录继续。已完成的 LDR 会做哈希核对。空结果、碰撞或越界输出会换种子重试，默认每条每次最多 3 个种子。若仍未得到有效 LDR，提示词会保持待处理，再执行 `full` 可从下一个种子继续。默认从种子 42 开始。

沿用历史 A/B 运行记录的配置：20 格空间，每轮最多新增 200 块，最多 8 次回退，使用连通性检查。LDR 采用官方导出颜色。可查看每条 `records/*.json` 中的 `connected` 和重试记录。

完整运行显示 `FINISHED full` 和 `131/131` 后执行：

```bash
bash run.sh export
```

LDR 在 `Results/brickgpt_A130_A260/ldr/`。导出文件是 `Results/brickgpt_A130_A260-results.tar.gz` 和同名校验文件，含 131 个 LDR、逐条生成记录、原始砖块文本和汇总。

官方代码：[BrickGPT](https://github.com/AvaLovelace1/BrickGPT)。官方适配器：[AvaLovelace/BrickGPT](https://huggingface.co/AvaLovelace/BrickGPT)。本包附带的第三方源码修订和修改说明见 `Vendor/PROVENANCE.json`。
'''


def parse_input(path):
    rows = []
    category = None
    current = None
    for line_number, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        if match := re.match(r'^## ([a-z]+)（', line):
            category = match[1]
        if match := re.match(r'^\*\*A(\d+) · (.+?)\*\*', line):
            current = int(match[1]), match[2]
        if match := re.fullmatch(r'- `L([1-5])`[：:][ \t]*(.+)', line):
            number, object_name = current
            level = int(match[1])
            ordinal = len(rows) + 1
            if ordinal != (number - 1) * 5 + level or not category:
                raise ValueError(f'Unexpected object/level order on line {line_number}')
            rows.append({'ordinal': ordinal, 'prompt_id': f'A{ordinal:03d}_{category}_A{number:02d}_L{level}',
                         'source_line': line_number, 'object_number': number, 'object': object_name,
                         'category': category, 'level': level, 'caption': match[2]})
    if len(rows) != 260:
        raise ValueError(f'Expected 260 source prompts, found {len(rows)}')
    selected = rows[129:260]
    if len(selected) != 131 or selected[0]['source_line'] != 232 or selected[-1]['source_line'] != 464:
        raise ValueError('Unexpected boundaries for the provided dataset')
    return selected


def put_text(path, content):
    atomic_write(path, content.replace('\r\n', '\n').encode('utf-8'))


def replace_once(path, before, after):
    text = path.read_text(encoding='utf-8')
    if text.count(before) != 1:
        raise ValueError(f'Unexpected upstream code at {path}')
    put_text(path, text.replace(before, after))


def stage_vendor(root, source):
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if commit != UPSTREAM:
        raise ValueError(f'Expected BrickGPT upstream {UPSTREAM}, got {commit}')
    vendor = root / 'Vendor'
    dst = vendor / 'src/brickgpt'
    shutil.copytree(source / 'src/brickgpt', dst, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('render_bricks.py', 'infer.py', 'prepare_finetuning_dataset.py', '__pycache__'))
    shutil.copyfile(source / 'LICENSE', vendor / 'LICENSE')
    llm = dst / 'models/llm.py'
    replace_once(llm,
                 "def __init__(self, model_name: str, device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):",
                 "def __init__(self, model_name: str, device: str = 'cuda' if torch.cuda.is_available() else 'cpu', *, tokenizer=None, model=None):")
    replace_once(llm, 'self.tokenizer = AutoTokenizer.from_pretrained(model_name)\n        self.model = AutoModelForCausalLM.from_pretrained(model_name).to(device)',
                 'self.tokenizer = tokenizer if tokenizer is not None else AutoTokenizer.from_pretrained(model_name)\n'
                 '        self.model = model if model is not None else AutoModelForCausalLM.from_pretrained(model_name).to(device)')
    engine = dst / 'models/brickgpt.py'
    replace_once(engine, 'def __init__(self, cfg: BrickGPTConfig):', 'def __init__(self, cfg: BrickGPTConfig, *, llm=None):')
    replace_once(engine, 'self.llm = LLM(cfg.model_name_or_path, self.device)',
                 'self.llm = llm if llm is not None else LLM(cfg.model_name_or_path, self.device)')
    stability = dst / 'stability_analysis/stability_analysis.py'
    replace_once(stability, 'import gurobipy as gp\nfrom gurobipy import GRB\n', '')
    replace_once(stability, '    model = gp.Model("stability_analysis")',
                 '    import gurobipy as gp\n    from gurobipy import GRB\n\n    model = gp.Model("stability_analysis")')
    save_json(vendor / 'PROVENANCE.json', {'source': UPSTREAM_URL, 'commit': commit, 'license': 'MIT',
              'changes': ['Injected offline model and tokenizer into the original BrickGPT generator',
                          'Imported Gurobi lazily so the connectivity-based mode needs no solver',
                          'Included only source needed for generation and LDraw export']})


def pack(args):
    root = args.deploy / 'build/brickgpt_20261115/BrickGPT_A130_A260'
    root.mkdir(parents=True, exist_ok=True)
    (root / 'Scripts').mkdir(exist_ok=True)
    for name in ('checkpoints.py', 'batch.py'):
        shutil.copyfile(HERE / name, root / 'Scripts' / name)
    put_text(root / 'run.sh', RUN)
    put_text(root / 'setup.sh', SETUP)
    put_text(root / 'README_服务器运行.md', README)
    save_json(root / 'Data/prompts.json', parse_input(args.prompts))
    save_json(root / 'Data/source.json', {'file': args.prompts.name, 'sha256': file_hash(args.prompts),
              'selection': [130, 260], 'inclusive': True, 'count': 131})
    stage_vendor(root, args.upstream)
    for name, (location, digest) in WHEELS.items():
        path = root / 'VendorsWheels' / name
        if not path.is_file() or file_hash(path) != digest:
            with urllib.request.urlopen(f'https://files.pythonhosted.org/packages/{location}/{name}', timeout=45) as stream:
                atomic_write(path, stream.read())
        if file_hash(path) != digest:
            raise ValueError(f'Invalid wheel hash: {name}')
    files = [p for p in sorted(root.rglob('*')) if p.is_file() and p.name != 'CHECKSUMS.sha256'
             and not set(p.relative_to(root).parts) & {'Results', 'Downloads', '.runtime', '__pycache__'}]
    checksum_path = root / 'CHECKSUMS.sha256'
    put_text(checksum_path, ''.join(f'{file_hash(p)}  {p.relative_to(root).as_posix()}\n' for p in files))
    archive = args.deploy / (STEM + '.tar.gz')
    tmp = archive.with_suffix('.tmp')
    with tarfile.open(tmp, 'w:gz', compresslevel=6) as tar:
        for path in [checksum_path] + files:
            name = path.relative_to(root).as_posix()
            if name.endswith('.sh') and b'\r' in path.read_bytes():
                raise ValueError(f'Non-LF shell script: {name}')
            info = tar.gettarinfo(str(path), arcname=f'{root.name}/{name}')
            info.mode = 0o755 if name.endswith('.sh') else 0o644
            with path.open('rb') as stream:
                tar.addfile(info, stream)
    tmp.replace(archive)
    put_text(args.deploy / (archive.name + '.sha256'), f'{file_hash(archive)}  {archive.name}\n')
    shutil.copyfile(root / 'README_服务器运行.md', args.deploy / 'README_BrickGPT_A130_A260.md')
    print(f'PACKAGED {archive} {archive.stat().st_size} bytes', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prompts', type=Path, required=True)
    parser.add_argument('--upstream', type=Path, required=True)
    parser.add_argument('--deploy', type=Path, required=True)
    pack(parser.parse_args())
