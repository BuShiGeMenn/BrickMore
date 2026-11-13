"""Compose new prompts from documented training elements, preserving Level complexity."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/regenerate_5groups_reconstructed_20261107'
HANDOFF=Path('G:/桌面/BrickMore_交接包_20261030/待重新生成_5组_现有提示词.json')
CAR_BASE=('A streamlined car has a curved-roof cabin and four separate wheels. '
          'The cabin stands over the main body, while the wheels attach in front and rear pairs on its two sides. '
          'Rounded solid surfaces carry the connected parts. '
          'Across the whole car, width is about 0.68 of front-to-back length and height is about 0.69 of width.')
PROMPTS={
    'camera_L2':('A rounded camera carries a circular lens at the front. The barrel connects to its body, '
                 'the grip is on the right side, and the shutter and viewfinder sit on top.'),
    'car_L4':CAR_BASE,
    'car_L5':(CAR_BASE+' The body and cabin are red, the windows are light blue, and the four wheels are near black, '
              'with continuous color regions. A front view reveals the functional parts; side and overhead views '
              'show their depth, connections and arrangement.'),
    'guitar_L1':'A guitar with a rounded, waisted body, a narrow neck and a distinct headstock.',
    'vessel_L1':'A boat with a rounded hull, bow, stern, deck and an open interior.',
}
ZH={
    'camera_L2':'一台圆角相机，正面带圆镜头。镜筒连接机身，握柄在右侧，快门和取景器位于顶部。',
    'car_L4':'一辆流线汽车，有弧顶驾驶舱和四个独立车轮。驾驶舱位于主体车身上方，前后轮对分居两侧并连接车身。圆润的实体表面承载相接的部件。整车宽度约为前后长度的 0.68 倍，高度约为宽度的 0.69 倍。',
    'car_L5':'一辆流线汽车，有弧顶驾驶舱和四个独立车轮。驾驶舱位于主体车身上方，前后轮对分居两侧并连接车身。圆润的实体表面承载相接的部件。整车宽度约为前后长度的 0.68 倍，高度约为宽度的 0.69 倍。车身和驾驶舱为红色，车窗为浅蓝色，四轮为近黑色，各部位采用连续色区。正视显示功能部件，侧视和俯视显示其厚度、连接及布局。',
    'guitar_L1':'一把吉他，琴身圆润收腰，带细长琴颈和清晰的琴头。',
    'vessel_L1':'一艘船，圆润船壳带艏、艉、甲板和内部开口。',
}
RULES={1:'基础轮廓与主要部件；不添加比例、配色或逐部件连接细则。',
       2:'基础轮廓，加部件位置与连接关系；不添加比例与配色。',
       4:'基础结构、连续曲面与部件连接，加 dataset 中的实际比例；不添加配色。',
       5:'包含 L1–L4 信息，再加训练中真实存在的部件配色与观察视角。'}


def main():
    source=json.loads(HANDOFF.read_text(encoding='utf-8-sig'))
    plan=deepcopy(source)
    plan.update(schema_version=3,prompt_count=5,
        description='Newly constructed wording for all five groups; dataset captions used as evidence only, never copied into the model prompt.',
        prompt_policy='new_wording_from_documented_training_elements_and_level_rules; no_verbatim_dataset_prompts',
        previous_generation_review='Original-prompt batch rejected by user; verbatim-dataset batch retained as reference only')
    sample_captions=[]
    for file in (ROOT/'Train/samples/models').glob('*/*/prompts.json'):
        sample_captions += [p['captionEn'] for p in json.loads(file.read_text(encoding='utf-8'))]
    tree=ast.parse((ROOT/'Train/programs/captions.py').read_text(encoding='utf-8'))
    base=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
              and any(isinstance(t,ast.Name) and t.id=='BASE' for t in n.targets))
    for group in plan['groups']:
        key,cat,level=group['group'],group['category'],group['level']
        path=next((ROOT/'Train/samples/models'/cat).glob('*/prompts.json'))
        record=next(p for p in json.loads(path.read_text(encoding='utf-8')) if p['promptLevel']==level)
        text=PROMPTS[key]
        assert text not in sample_captions
        # Original generated dataset captions all begin with their category's fixed BASE sentence.
        assert not any(text.startswith(values[1]) for values in base.values())
        evidence=dict(reference_file=path.relative_to(ROOT).as_posix(),
            reference_file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            reference_record_id=record['recordId'],reference_caption=record['captionEn'],
            required_parts=record['requiredParts'],prompt_level=level,fact_groups=list(range(1,level+1)),
            level_rule=RULES[level],newly_constructed=True,exact_caption_match=False,
            original_caption_prefix_match=False,
            geometry_source='Train/programs/geometry.py',caption_level_source='Train/programs/captions.py')
        if cat=='car':
            evidence['measured_ratios']=dict(width_to_depth=.68,height_to_width=.69)
            if level==5:
                evidence['documented_part_colors']=dict(body='red',cabin='red',window='glass/light blue',wheel='black/near black')
        group['original_prompts']=group['prompts']
        group['prompts']=[dict(candidate_id=f'reconstructed-{cat}-L{level}-v1',
            is_current_model=False,source_zh='重新构造，参考训练元素与同级模板',
            prompt=text,prompt_zh=ZH[key],evidence=evidence)]
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'revised_prompts.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 五组重构提示词','',
        '五条均重新构造措辞，不直接采用 dataset 原始 caption。dataset 文本仅保留为分级与元素证据，不送入模型。',
        'car L3 与 piano L5 保持原人工选择；前两批均不计入本次推荐。','']
    for group in plan['groups']:
        prompt=group['prompts'][0]
        lines += [f"## {group['group']}",'',prompt['prompt'],'',prompt['prompt_zh'],'',
                  'Level 规则：'+RULES[group['level']],'',
                  f"训练证据：`{prompt['evidence']['reference_file']}` · `{prompt['evidence']['reference_record_id']}`",'']
    (OUT/'revised_prompts.md').write_text('\n'.join(lines),encoding='utf-8')
    (OUT/'revised_prompts.txt').write_text('\n'.join(line.lstrip('# ').replace('`','') for line in lines),encoding='utf-8')
    old=ROOT/'output/regenerate_5groups_dataset_20261107/manifest.json'
    if old.exists():
        records=json.loads(old.read_text(encoding='utf-8'))
        for record in records:
            record['status']='reference_only_verbatim_dataset_prompt'
        old.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    print('SAVED',OUT/'revised_prompts.md',flush=True)
    for group in plan['groups']:
        print(group['group'],group['prompts'][0]['prompt'],flush=True)


if __name__=='__main__':
    main()
