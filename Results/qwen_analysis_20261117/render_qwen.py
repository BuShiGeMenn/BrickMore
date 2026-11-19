import json
from html import escape as e
from pathlib import Path as P
from urllib.parse import quote
root = P(r'D:\BrickMore\Qwen_Comparision\Results')
raw = P(r'D:\BrickMore\Results\qwen_analysis_20261117\analysis_work.json').read_text(encoding='utf-8')
d = json.loads(raw)
assert d['qa']['status']=='PASS' and not d['qa']['failures']
a,b = (d['groups'][c] for c in 'AB')
full = d['full_run']
c = d['supplement_brickmore_A']
mat = c['brickmore_matched']
meta = d['generator_identity']['A']
from functools import partial
def pct(x,dec=2): return f'{100*x:.{dec}f}%'
def f(x): return f'{x:.6f}' if x>=.0001 else f'{x:.4g}'
def cols(g,measure='mean'):
    return [pct(g['pinv'][measure]), *(f(g[k][measure]) for k in ('vqa','pe','siglip2'))] if g['n'] else ['—']*4
def table(headers,rows):
    return '<div class="scroll"><table><thead><tr>'+''.join('<th scope="col">'+str(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+f'<th scope="row">{r[0]}</th>'+''.join(f'<td>{h}</td>' for h in r[1:])+'</tr>' for r in rows)+'</tbody></table></div>'
metrics=['P<sub>inv</sub> ↓','VQAScore ↑','PE ↑','SigLIP2 ↑']
summary_tbl=table(['测评输入','四项齐全 / 计划','覆盖率',*metrics],[
    ['A · Qwen3-1.7B 基础版', f"{a['n']} / {a['expected']}",pct(a['n']/a['expected']),*cols(a)],
    ['B · Qwen1.7b LDR', f"{b['n']} / {b['expected']}",pct(b['n']/b['expected']),*cols(b)]])
detail=table(['分组','积木数均值 / 中位数','零碰撞样本','P<sub>inv</sub> 微平均'],
    [[f'{k} 组',f"{g['parts_mean']:.2f} / {g['parts_median']:g}",f"{g['no_collision']} / {g['n']}",f"{g['invalid']:,} / {g['parts']:,} = {pct(g['pinv_micro'])}"] for k,g in zip('AB',[a,b])])
detail_dist=table(['分组','统计量',*metrics],[[k,v,*cols(g,h)] for k,g in zip('AB',[a,b])
    for h,v in [('median','中位数'),('q1','下四分位数'),('q3','上四分位数')]])
level_tbl=table(['Level','A 覆盖',*metrics,'B 覆盖',*metrics],
    [[f'L{i}',f"{aa['n']}/{aa['expected']}",*cols(aa),f"{bb['n']}/{bb['expected']}",*cols(bb)]
     for i,(aa,bb) in enumerate(zip(a['levels'].values(),b['levels'].values()),1)])
cat_tbl=table(['类别','A 覆盖',*metrics,'B 覆盖',*metrics],
    [[e(name),f"{aa['n']}/{aa['expected']}",*cols(aa),f"{bb['n']}/{bb['expected']}",*cols(bb)]
     for name,aa in a['categories'].items() for bb in [b['categories'][name]]])
matched_tbl=table(['同一组 80 条提示词','样本',*metrics,'P<sub>inv</sub> 微平均'],
    [['Qwen A · 可解析片段',a['n'],*cols(a),pct(a['pinv_micro'])],
     ['BrickMore A · 送评模型',mat['n'],*cols(mat),pct(mat['pinv_micro'])]])
b_clusters=b['render_groups']['clusters']
cluster_tbl=table(['代表样本','样本数','涉及类别数','积木数'],
    [[e(g['representative']),g['size'],len(g['categories']),e('、'.join(g['part_counts']))] for g in b_clusters])
both=sum(g['size'] for g in b_clusters[:2])
time_s=round(full['total_elapsed_s'])
part_small=sum(b['parts_distribution'].get(x,0) for x in ('7','8'))
run='Results/qwen_A_B'
figs=[]
for cc in b_clusters[:2]:
    img=run+'/rendered/'+cc['representative_view_paths'][2]
    assert (root/img).is_file()
    figs.append(f'''<figure><a href="{quote(img)}"><img width="512" height="512" src="{quote(img)}" alt="B 组参考渲染 {e(cc['representative'])}"></a><figcaption><strong>{cc['size']} 条</strong> · {len(cc['categories'])} 类 · {e(cc['representative'])}（代表样本）</figcaption></figure>''')
qa=d['qa']
base_source=e(c['archive'])
scorer_labels=table(['指标','评分模型','快照版本'],[[label,e(d['scorers'][k]['repo']),f"<code>{e(d['scorers'][k]['revision'])}</code>"] for k,label in [('vqa','VQAScore'),('pe','PE'),('siglip2','SigLIP2')]])
pe_a=sum(a['truncated']['pe'].values())
pe_b=sum(b['truncated']['pe'].values())
sig_a=sum(a['truncated']['siglip2'].values())
sig_b=sum(b['truncated']['siglip2'].values())
ctx=d['scorers']['text_context_length']
qa_name='Qwen_AB_评分核查.json'
html=f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Qwen 积木生成 · 四项评分分析</title>
<style>
:root{{color-scheme:light;--ink:#18233b;--muted:#52627b;--accent:#174b73;--line:#d8e2ed;--bg:#eef3f9;--paper:#fff}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 "Microsoft YaHei","PingFang SC",system-ui,sans-serif}}main{{max-width:1100px;margin:auto;padding:32px 22px 56px}}header,section{{background:var(--paper);border:1px solid var(--line);border-radius:15px;padding:26px;margin-bottom:18px}}header{{background:#17324d;color:#fff}}header p{{color:#e0edf7;max-width:900px}}.eyebrow{{font-size:.82rem;font-weight:700;letter-spacing:.09em;color:#cde4f9}}h1,h2,h3{{line-height:1.3;margin:0 0 .55em}}h1{{font-size:clamp(1.65rem,4vw,2.5rem)}}h2{{font-size:1.33rem}}h3{{margin-top:1em;font-size:1.04rem}}p{{margin:.6em 0}}.chips{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:20px 0 0}}.chip{{border:1px solid #7494af;border-radius:10px;padding:12px;background:#234462}}.chip b{{display:block;font-size:1.4rem;font-variant-numeric:tabular-nums}}.chip small{{font-size:.83rem;color:#ecf4fa}}.scroll{{overflow-x:auto;margin:.8rem 0}}table{{width:100%;border-collapse:collapse;font-size:.89rem;font-variant-numeric:tabular-nums}}td,th{{padding:9px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}}thead th{{background:#eef4fa;font-weight:700}}td:first-child,th:first-child{{text-align:left}}tbody th{{font-weight:600}}tbody tr:nth-child(even){{background:#f8fafc}}.muted,figcaption,footer{{color:var(--muted);font-size:.9rem}}.note{{border-left:4px solid #4d7297;padding:9px 13px;background:#eef5fc;border-radius:2px}}a{{color:#145983}}details{{margin:.8em 0}}summary{{color:var(--accent);font-weight:700;cursor:pointer}}.figs{{display:grid;grid-template-columns:repeat(2,minmax(0,240px));gap:14px;margin:1em 0}}figure{{margin:0}}img{{width:100%;height:auto;aspect-ratio:1;border:1px solid var(--line);border-radius:10px;display:block}}figcaption{{margin-top:4px}}code{{font-family:Consolas,monospace;word-break:break-all}}.paths{{overflow-wrap:anywhere}}.links li{{margin:.25em 0}} @media(max-width:570px){{main{{padding:12px}}header,section{{padding:17px}}.chips{{gap:6px}}.chip{{padding:8px}}.chip small{{font-size:.72rem}}}} @media print{{body{{background:#fff}}main{{width:100%;padding:0}}section,header{{break-inside:avoid}}header{{background:#fff;color:#18233b}}header p,.eyebrow,.chip small{{color:#18233b}}.chip{{background:#fff}}}}
</style>
</head>
<body><main>
<header>
<div class="eyebrow">测评结果 · 2026-11-17</div>
<h1>Qwen 积木生成 · 四项评分分析</h1>
<p>A 组的主要问题是输出无法解析或未通过原始几何校验；B 组虽然全部取得分数，但大量不同提示词对应同一外形。两组提示词不同，应分别解读。</p>
<div class="chips">
<div class="chip"><b>{a['n']} / {a['expected']}</b><small>A 组可评分片段</small></div>
<div class="chip"><b>{b['n']} / {b['expected']}</b><small>B 组四项齐全</small></div>
<div class="chip"><b>{b['render_groups']['unique']} 套</b><small>B 组独立八视角渲染</small></div>
</div>
</header>

<section id="overview">
<h2>四项评分与覆盖率</h2>
{summary_tbl}
<p class="muted">表内为每条样本等权平均。三项图文指标先取每个样本 8 个视角的最高分，再对样本求平均。全量批次共 {full['scored']}/{full['expected']} 条四项齐全（{pct(full['scored']/full['expected'])}），核对了 {full['images']:,} 张视角图和 {full['per_view_semantic_scores']:,} 个逐视角图文分数。小样本的 {full['smoke_count_excluded']} 条未计入。</p>
{detail}
<details><summary>展开分布：中位数与四分位数</summary>{detail_dist}</details>
</section>

<section id="input-a">
<h2>A 组：只评到可解析片段</h2>
<ul>
<li>原始记录标注模型为 <strong>Qwen/Qwen3-1.7B 基础版（未微调）</strong>。{a['expected']} 条原始输出里，{meta['upstream_geometry_valid_true']} 条通过原始几何校验；{a['expected']-meta['upstream_completed']} 条另标为生成未完成。</li>
<li><strong>{a['input_status']['no_placement']} 条</strong>未检出符合严格格式的积木摆放记录；另有 <strong>{a['input_status']['unsupported_part']} 条</strong>（A35_L4、A37_L2）用了当前共享零件库不支持的 4×4 零件。其分数保留为空，报告仅统计其余 {a['n']} 条可解析片段。</li>
<li>这 {a['n']} 条的 P<sub>inv</sub> 宏平均为 <strong>{pct(a['pinv']['mean'])}</strong>，微平均为 <strong>{pct(a['pinv_micro'])}</strong>。两者的差距说明，按积木摆放次数加权后，碰撞问题更突出。</li>
<li>SigLIP2 均值受单个样本影响较大：<strong>{a['score_maxima']['siglip2']['prompt_id']}</strong> 贡献了该组分数总和的 {pct(a['score_top_one_share']['siglip2'],1)}，该组中位数只有 {f(a['siglip2']['median'])}。</li>
</ul>
</section>

<section id="input-b">
<h2>B 组：分数齐全，外形高度重复</h2>
<p>对每条样本按视角顺序比较 8 张 PNG 的 SHA-256，{b['n']} 条只得到 <strong>{b['render_groups']['unique']} 套</strong>不同渲染；{b['render_groups']['repeated_samples']} 条（{pct(b['render_groups']['repeated_samples']/b['n'])}）至少与另一条完全一致。最常见的两套合计 <strong>{both} 条（{pct(both/b['n'])}）</strong>。最常见的一套跨全部 21 个类别，例如 <code>B01_L1</code> 篮子、<code>B17_L4</code> 相机和 <code>B19_L1</code> 汽车。</p>
<div class="figs">{''.join(figs)}</div>
<p class="muted">图为两套最常见渲染的同一方位，颜色由测评统一设置。按零件编号和位姿另行核对，忽略颜色和记录顺序，B 组也只有 {b['geometry_groups']['unique']} 种不同的积木摆放组合。</p>
<p>有 {part_small} 条（{pct(part_small/b['n'])}）只用了 7 或 8 块。{b['no_collision']} 条在记录的装配顺序下没有检出碰撞，P<sub>inv</sub> 宏平均为 {pct(b['pinv']['mean'])}；结合重复率，低碰撞率不能用来判断模型是否符合提示词或能否稳定搭建。VQAScore 与 SigLIP2 的中位数分别为 {f(b['vqa']['median'])}、{f(b['siglip2']['median'])}。</p>
<p class="muted">输入档案为 <code>Qwen1.7b.zip</code>。LDR 未记录生成权重或微调状态，无法确认 B 与 A 是否使用同一生成权重。</p>
<details><summary>展开 B 组 12 套渲染的分布</summary>{cluster_tbl}</details>
</section>

<section id="levels">
<h2>按提示词复杂度查看</h2>
<p>每个 Level 的计划样本数为 A 组 52 条、B 组 53 条。下表先列 A 组覆盖与四项均值，再列 B 组。A 的覆盖率随 Level 变化，适合查看瓶颈，不宜把观察到的变化全归因于提示词复杂度。</p>
{level_tbl}
<p>B 组 VQAScore 从 L2 的 {f(b['levels']['2']['vqa']['mean'])} 降到 L5 的 {f(b['levels']['5']['vqa']['mean'])}。与此同时，PE 和 SigLIP2 也有文本长度限制：PE（{ctx['pe']} token）截断 A 组 {pe_a} 条、B 组 {pe_b} 条；SigLIP2（{ctx['siglip2']} token）截断 A 组 {sig_a} 条、B 组 {sig_b} 条。B 组 L4、L5 的 106 条提示词全部被 SigLIP2 截断，不能用其分数验证完整长提示词的所有细节。</p>
<details><summary>展开 21 类的覆盖与四项均值</summary>{cat_tbl}</details>
</section>

<section id="brickmore">
<h2>补充对照：BrickMore 与 Qwen A 的 80 条共同提示词</h2>
<p>补充结果来自先前的 <code>BrickMore_A260_20261117.rar</code>。按同一组、提示词 ID、原文、类别和 Level 配对；评分模型、渲染设置及共同零件的网格与碰撞体一致。BrickMore A 的四项评分覆盖 260/260；下表仅比较 Qwen A 有分数的 80 条。</p>
{matched_tbl}
<p>同样的 80 条中，BrickMore 的 VQAScore、PE、SigLIP2 分别在 <strong>{c['brickmore_semantic_wins']['vqa']}、{c['brickmore_semantic_wins']['pe']}、{c['brickmore_semantic_wins']['siglip2']} 条</strong>更高。P<sub>inv</sub> 的均值也较低，但 BrickMore 使用提供的原始积木序列，Qwen 用由输出片段转换出的 LDraw 文件顺序，碰撞率受顺序和输出完整度影响。80 条中 BrickMore 原始几何校验标为通过的有 {c['brickmore_upstream_geometry_valid']['matched']} 条；Qwen 为 0 条。</p>
<p class="note">报告模型对比时，把「四项评分覆盖率」和「共同提示词上的分数」同时列出。A 组其余 180 条无法做成对评分；B 组应先确认生成权重和批量输出是否复用了同一模板，再用于同提示词的横向比较。本包没有可直接并入的 BrickGPT 或 BrickNet 评分。</p>
<details><summary>展开 BrickMore A 的全部 260 条均值</summary>{table(['输入','样本数',*metrics], [['BrickMore A · 全部送评',c['brickmore_all']['n'],*cols(c['brickmore_all'])]])}<p class="muted">全量结果用于描述 BrickMore A 自身；与 Qwen 配对时以上面的 80 条为准。</p></details>
</section>

<section id="provenance">
<h2>评分口径与核查来源</h2>
<p><strong>P<sub>inv</sub></strong> 是指定装配顺序下被判为碰撞的摆放次数占比，越低越好；宏平均按样本等权，微平均按摆放次数计。<strong>VQAScore</strong> 用模型首个回答 token 为 Yes 的概率；<strong>PE</strong> 用图文向量的余弦相似度；<strong>SigLIP2</strong> 用图文 logit 的 sigmoid 值。三个图文分数各自解读，不能直接当成准确率或合并成百分制。渲染为同一套正交参数、512×512、8 个固定角度与统一黄色。</p>
<p><strong>回传文件与分数核查：</strong>本地 {d['extracted_files']:,} 个回传文件与 RAR 解包副本的 SHA-256 一致。核对了阶段退出状态、提示词映射、图片摘要、逐视角分数和服务器汇总；主测评耗时约 {time_s//60} 分 {time_s%60} 秒。审计共通过 {qa['checks_passed']:,} 项检查，0 项失败。</p>
<ul class="links">
<li><a href="{run}/report/report.html">服务器原始全量报告</a> · <a href="{run}/report/scores.csv">345 条分数</a> · <a href="{run}/report/coverage_and_scores.csv">525 条覆盖和分数</a></li>
<li><a href="{quote(qa_name)}">评分核查 JSON</a>（含缺测 ID、重复渲染分组和补充对照数据）</li>
</ul>
<details><summary>展开评分模型快照及文件摘要</summary>
{scorer_labels}
<p class="paths">回传来源：<code>{e(d['source_archive'])}</code><br>SHA-256：<code>{e(d['source_archive_sha256'])}</code></p>
<p class="paths">补充来源：<code>{base_source}</code><br>SHA-256：<code>{e(c['sha256'])}</code></p>
</details>
</section>
</main></body></html>'''
(root/qa_name).write_text(raw,encoding='utf-8')
(root/'Qwen_AB_四项评分分析.html').write_text(html,encoding='utf-8')

