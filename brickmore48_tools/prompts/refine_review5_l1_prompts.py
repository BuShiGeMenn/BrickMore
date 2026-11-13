"""Keep the documented category terms while independently reconstructing L1 wording."""
from copy import deepcopy
import json
from pathlib import Path

BASE=Path(__file__).resolve().parents[2]/'output/regenerate_5groups_reconstructed_20261107'
updates={
 'guitar_L1':('A rounded waist guitar whose curved body leads into a slender neck topped by a headstock.',
              '一把圆润收腰的吉他，弧形琴身向上接入细长琴颈，顶端为琴头。'),
 'vessel_L1':('A rounded monohull boat, its bow and stern framing a deck with an open interior.',
              '一艘圆壳单体船，艏艉之间是带内部开口的甲板。'),
}
plan=json.loads((BASE/'revised_prompts.json').read_text(encoding='utf-8'))
for group in plan['groups']:
    if group['group'] not in updates:
        continue
    text,zh=updates[group['group']]
    prompt=deepcopy(group['prompts'][0])
    prompt.update(candidate_id=f"reconstructed-{group['category']}-L1-v2",prompt=text,prompt_zh=zh)
    prompt['evidence'].update(refinement='Retain the documented category phrase; independently reconstruct the rest of the sentence.',
                              exact_caption_match=False,newly_constructed=True)
    assert text!=prompt['evidence']['reference_caption']
    assert not text.startswith(prompt['evidence']['reference_caption'])
    if len(group['prompts'])==1:
        group['prompts'].append(prompt)
    else:
        group['prompts'][1]=prompt
plan['prompt_count']=sum(len(group['prompts']) for group in plan['groups'])
(BASE/'revised_prompts.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
records=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
for row in records:
    if row['group']=='guitar_L1' and row['id'].endswith('_P1_G'):
        row.update(status='rejected_visual_shape',visual_review=dict(decision='rejected',
                   reason_zh='未形成可辨认的吉他琴身、琴颈和琴头轮廓。'))
    if row['group']=='vessel_L1' and row['id'].endswith('_P1_G'):
        row.update(status='rejected_geometry',visual_review=dict(decision='rejected',
                   reason_zh='保形重铺在预算内未能得到单一凸点连通结构。'))
(BASE/'manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
text=(BASE/'revised_prompts.md').read_text(encoding='utf-8')
text+='\n## L1 修订候选（v2）\n\n保留训练中的类别短语，后续措辞重新构造；原 v1 结果不推荐。\n\n'
for key,(en,zh) in updates.items():
    text+=f'### {key}\n\n{en}\n\n{zh}\n\n'
(BASE/'revised_prompts.md').write_text(text,encoding='utf-8')
(BASE/'revised_prompts.txt').write_text('\n'.join(line.lstrip('# ').replace('`','') for line in text.splitlines()),encoding='utf-8')
print('Saved two reconstructed L1 refinements')
