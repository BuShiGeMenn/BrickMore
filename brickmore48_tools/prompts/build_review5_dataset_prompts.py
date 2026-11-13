"""Use the actual dataset caption at the requested level for the four authorized rewrites."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HANDOFF = Path('G:/桌面/BrickMore_交接包_20261030/待重新生成_5组_现有提示词.json')
OUT = ROOT / 'output/regenerate_5groups_dataset_20261107'
TARGETS = {'camera_L2':2,'car_L5':5,'guitar_L1':1,'vessel_L1':1}


def main():
    original = json.loads(HANDOFF.read_text(encoding='utf-8-sig'))
    plan = deepcopy(original)
    plan.update(schema_version=2,description='Four authorized replacements using actual dataset captions at the same level; car L4 uses the unchanged supplied alternative.',
                prompt_policy='dataset_exact_caption_for_four_authorized_rewrites; car_L4_verbatim_supplied_alternative',
                prompt_count=5,previous_generation_review='All five previous candidates rejected by the user')
    for group in plan['groups']:
        if group['group'] in TARGETS:
            cat = group['category']
            source = next((ROOT / 'Train/samples/models' / cat).glob('*/prompts.json'))
            rows = json.loads(source.read_text(encoding='utf-8'))
            row = next(r for r in rows if r['promptLevel'] == TARGETS[group['group']])
            prompt = dict(candidate_id=f"dataset-{cat}-L{row['promptLevel']}-m0001",is_current_model=False,
                source_zh='dataset 原始同级 caption',prompt=row['captionEn'],prompt_zh=row['captionZh'],
                evidence=dict(source_file=source.relative_to(ROOT).as_posix(),
                    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    record_id=row['recordId'],model_id=row['modelId'],prompt_level=row['promptLevel'],
                    prompt_type=row['promptType'],fact_groups=row['factGroups'],
                    required_parts=row['requiredParts'],exact_caption_match=True))
        else:
            assert group['group'] == 'car_L4'
            prompt = deepcopy(group['prompts'][1])
            prompt['evidence'] = dict(source_file=str(HANDOFF),policy='existing alternative, verbatim; no rewrite authorized')
        group['original_prompts'] = group['prompts']
        group['prompts'] = [prompt]
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT / 'revised_prompts.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    text = ['# 第二批提示词：dataset 同级原文','',
        '第一批五个候选均已由用户判为不合格，另行保留，不计入本批。',
        'camera L2、car L5、guitar L1、vessel L1 直接采用 dataset 对应 Level 的实际 caption。',
        'car L4 使用原交接文件同级备选原文，未改写。car L3 与 piano L5 保留。','',
        'Level 规则：L1=基础外形；L2=增加部件与连接；L3=增加几何；L4=增加实测比例；L5=增加训练配色和观察视角。',
        '本批使用确定性解码先验证训练分布内的文本；后续有需要再按相同提示词换种子。','']
    for group in plan['groups']:
        prompt = group['prompts'][0]
        text += [f"## {group['group']}",'',prompt['prompt'],'',prompt['prompt_zh'],'']
        if 'record_id' in prompt['evidence']:
            text += [f"来源：`{prompt['evidence']['source_file']}` · `{prompt['evidence']['record_id']}`",'']
    (OUT / 'revised_prompts.md').write_text('\n'.join(text),encoding='utf-8')
    rejected = ROOT / 'output/regenerate_5groups_20261107/manifest.json'
    previous = json.loads(rejected.read_text(encoding='utf-8'))
    for row in previous:
        row['status'] = 'rejected_by_user'
        row['visual_review'] = dict(decision='rejected',reviewer='user',note='Previous generated candidates all unqualified')
    rejected.write_text(json.dumps(previous,ensure_ascii=False,indent=2),encoding='utf-8')
    print('SAVED',OUT / 'revised_prompts.json')
    for group in plan['groups']:
        print(group['group'],group['prompts'][0]['prompt'])


if __name__ == '__main__':
    main()
