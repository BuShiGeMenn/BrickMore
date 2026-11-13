"""Read returned journals, independently reconcile them, and summarize the fixed cohort."""
import argparse
import collections
import csv
import datetime
import hashlib
import html
import json
import math
import re
import statistics
import struct
from pathlib import Path

SYSTEMS = ('BrickMore', 'BrickGPT', 'BrickNet')
METRICS = ('pinv', 'vqa', 'pe', 'siglip2')
LABELS = {'pinv': 'P_inv（越低越好）', 'vqa': 'VQAScore', 'pe': 'PE', 'siglip2': 'SigLIP2'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def rows(path):
    return [json.loads(s) for s in path.read_text(encoding='utf-8-sig').splitlines() if s.strip()]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def close(a, b):
    return isinstance(a, (int, float)) and isinstance(b, (int, float)) and math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-12)


def summarize(seq):
    return dict(n=len(seq), **{m: statistics.mean(r[m] for r in seq) for m in METRICS},
                pinv_micro=sum(r['invalid_placements'] for r in seq) / sum(r['part_count'] for r in seq),
                zero_collision_models=sum(r['pinv'] == 0 for r in seq),
                mean_parts=statistics.mean(r['part_count'] for r in seq))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    a = parser.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    checks, failures = 0, []

    def check(ok, label):
        nonlocal checks
        checks += 1
        if not ok:
            failures.append(label)

    manifest = rows(a.input / 'selected_manifest.jsonl')
    canonical = rows(a.bundle / 'Data/manifest.jsonl')
    check(manifest == canonical, 'Returned input records differ from the packaged manifest')
    check(len(manifest) == 462, 'Expected 462 input records')
    ids = {r['sample_id'] for r in manifest}
    check(len(ids) == len(manifest), 'Duplicate input sample IDs')
    run_config = read(a.input / 'run_config.json')
    check(run_config['bundle_manifest_sha256'] == sha(a.bundle / 'Data/manifest.jsonl'), 'Packaged manifest SHA mismatch')
    check(run_config['sample_ids'] == [r['sample_id'] for r in manifest], 'Run selection mismatch')
    check(run_config['mode'] == 'full' and run_config['scope'] == 'all' and not run_config['cpu_only'], 'Not an all-record full run')
    progress = read(a.input / 'progress.json')
    check(progress['current_stage'] == 'finished', 'Run did not finish')
    for name, stage in progress['stages'].items():
        check(stage['status'] == 'completed' and stage['exit_code'] == 0 and stage['done'] == stage['total'], f'Incomplete stage: {name}')

    journals = {}
    journal_paths = {'structure': a.input / 'structure.jsonl', 'render': a.input / 'rendered/renders.jsonl',
                     **{m: a.input / (m + '.jsonl') for m in METRICS[1:]}}
    for name, path in journal_paths.items():
        records = rows(path)
        check(len(records) == 462, f'{name}: record count')
        check(len({r['sample_id'] for r in records}) == len(records), f'{name}: duplicate IDs')
        check({r['sample_id'] for r in records} == ids, f'{name}: coverage mismatch')
        journals[name] = {r['sample_id']: r for r in records}
        cfg = read(path.with_suffix('.config.json'))
        check(fingerprint({k: v for k, v in cfg.items() if k != 'signature'}) == cfg['signature'], f'{name}: config signature')
        check(all(r['config_signature'] == cfg['signature'] for r in records), f'{name}: mixed signatures')
        if name in METRICS[1:]:
            check(cfg['input_manifest_sha256'] == sha(journal_paths['render']), f'{name}: rendered manifest hash')
            check(cfg['preset'] == 'paper-text' and cfg['samples'] == 462 and cfg['view_evaluations'] == 3696, f'{name}: scoring preset/count')
            for file, checksum in cfg['sources'].items():
                check(sha(a.bundle / 'Scripts' / file) == checksum, f'{name}: source code provenance {file}')

    table, truncated, image_paths = [], collections.defaultdict(list), set()
    for row in manifest:
        sid = row['sample_id']
        s, r = journals['structure'][sid], journals['render'][sid]
        check(s['status'] == 'ok', f'{sid}: structure failed')
        check(s['n_actions'] == row['part_count'] and s['n_actions'] > 0, f'{sid}: action count')
        check(s['invalid_placements'] == len(set(s['collisions'])), f'{sid}: collision count')
        check(close(s['pinv'], s['invalid_placements'] / s['n_actions']), f'{sid}: P_inv denominator')
        check(all(0 <= x < s['n_actions'] for x in s['collisions']), f'{sid}: invalid collision index')
        check(s['metric'] == 'pinv_file_order' and not s['original_generation_order_verified'] and not s['fixed_edge_exemptions'], f'{sid}: structural protocol')
        check(all(r[k] == v for k, v in row.items()), f'{sid}: render metadata')
        check(hashlib.sha256(row['caption'].encode()).hexdigest() == row['caption_sha256'], f'{sid}: caption hash')
        check(len(r['view_paths']) == len(r['view_sha256']) == 8, f'{sid}: view count')
        ih = fingerprint({'row': r, 'actual_view_sha256': r['view_sha256']})
        for name, expected in zip(r['view_paths'], r['view_sha256']):
            path = (a.input / 'rendered' / name).resolve()
            check(path.is_relative_to((a.input / 'rendered').resolve()), f'{sid}: unsafe view path')
            check(sha(path) == expected, f'{sid}: image SHA {name}')
            data = path.read_bytes()[:24]
            check(data[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', data[16:24]) == (512, 512), f'{sid}: PNG format/size')
            image_paths.add(path)
        result = {**row, 'pinv': s['pinv'], 'invalid_placements': s['invalid_placements']}
        for metric in METRICS[1:]:
            score = journals[metric][sid]
            values = score['scores']
            check(score['status'] == 'ok' and len(values) == 8 and all(math.isfinite(x) for x in values), f'{sid}: {metric} finite scores')
            check(all((-1 if metric == 'pe' else 0) <= x <= 1 for x in values), f'{sid}: {metric} range')
            check(close(max(values), score['max_score']) and close(statistics.mean(values), score['mean_score']), f'{sid}: {metric} pooling')
            check(values[score['best_view']] == max(values), f'{sid}: {metric} best view')
            check(score['input_sha256'] == ih, f'{sid}: {metric} image/input fingerprint')
            check(score['view_sha256'] == r['view_sha256'] and score['caption'] == row['caption'], f'{sid}: {metric} caption/views')
            result[metric] = score['max_score']
            if any(d.get('text_truncated') for d in score['diagnostics']):
                truncated[metric].append(dict(sample_id=sid, primary=row['primary'], prompt_id=row['prompt_id'], system=row['system'],
                                              level=row['level'], tokens=max(d.get('text_tokens', 0) for d in score['diagnostics'])))
        table.append(result)
    check(len(image_paths) == 3696, 'Expected 3696 distinct images')
    check(len(list((a.input / 'rendered/views').rglob('*.png'))) == 3696, 'Unexpected/missing PNG files')

    with (a.input / 'report/scores.csv').open(encoding='utf-8-sig', newline='') as stream:
        csv_rows = list(csv.DictReader(stream))
    check(len(csv_rows) == 462 and {r['sample_id'] for r in csv_rows} == ids, 'CSV coverage')
    by_id = {r['sample_id']: r for r in table}
    for r in csv_rows:
        actual = by_id[r['sample_id']]
        check(all(close(float(r[m]), actual[m]) for m in METRICS), f'{r["sample_id"]}: CSV score disagreement')
        check(r['primary'] == str(actual['primary']), f'{r["sample_id"]}: CSV cohort disagreement')

    primary = [r for r in table if r['primary']]
    check(len(primary) == 342, 'Expected 342 primary records')
    matched = collections.defaultdict(dict)
    for r in primary:
        matched[r['prompt_id']][r['system']] = r
    check(len(matched) == 114, 'Expected 114 matched prompts')
    for pid, triplet in matched.items():
        check(set(triplet) == set(SYSTEMS) and len({r['caption'] for r in triplet.values()}) == 1, f'{pid}: unmatched systems/caption')
    check(len({r['category'] for r in primary}) == 21 and len({(r['category'], r['level']) for r in primary}) == 105, 'Category/Level coverage')
    overall = {s: summarize([r for r in primary if r['system'] == s]) for s in SYSTEMS}
    summary = read(a.input / 'report/summary.json')
    for system in SYSTEMS:
        check(summary['primary'][system]['records'] == 114, f'{system}: summary count')
        for m in METRICS:
            check(summary['primary'][system][m]['n'] == 114 and summary['primary'][system][m]['missing'] == 0, f'{system}: {m} summary coverage')
            check(close(summary['primary'][system][m]['mean'], overall[system][m]), f'{system}: {m} summary mean')
            check(summary['paired'][m]['common_prompts'] == 114 and close(summary['paired'][m]['means'][system], overall[system][m]), f'{system}: {m} paired summary')
        check(close(summary['primary'][system]['pinv_micro'], overall[system]['pinv_micro']), f'{system}: P_inv micro')

    def group(field):
        return {str(k): {s: summarize([r for r in primary if r[field] == k and r['system'] == s]) for s in SYSTEMS}
                for k in sorted({r[field] for r in primary})}

    by_level, by_category = group('level'), group('category')
    by_category_level = {f'{c}/L{l}': {s: summarize([r for r in primary if r['category'] == c and r['level'] == l and r['system'] == s]) for s in SYSTEMS}
                         for c, l in sorted({(r['category'], r['level']) for r in primary})}
    balanced = {s: {m: statistics.mean(g[s][m] for g in by_category_level.values()) for m in METRICS} for s in SYSTEMS}
    comparisons = {}
    for opponent in SYSTEMS[1:]:
        comparisons[opponent] = {}
        for m in METRICS:
            diffs = [triplet['BrickMore'][m] - triplet[opponent][m] for triplet in matched.values()]
            sign = -1 if m == 'pinv' else 1
            comparisons[opponent][m] = dict(mean_difference=statistics.mean(diffs),
                                            wins=sum(sign * d > 1e-12 for d in diffs),
                                            ties=sum(abs(d) <= 1e-12 for d in diffs),
                                            losses=sum(sign * d < -1e-12 for d in diffs))
    category_leads = {}
    for m in METRICS:
        category_leads[m] = {s: sum((min if m == 'pinv' else max)(g[t][m] for t in SYSTEMS) == g[s][m] for g in by_category.values()) for s in SYSTEMS}
    raw_pairs = []
    for r in primary:
        if r['system'] == 'BrickMore' and r['variant'] == 'stitched':
            other = by_id.get('brickmore__' + r['model_id'] + '__raw')
            if other and other['caption'] == r['caption']:
                raw_pairs.append((other, r))
    auxiliary = dict(records=len(table) - len(primary), brickmore_raw_vs_stitched_primary_pairs=len(raw_pairs),
                     paired_means={m: {'raw': statistics.mean(x[m] for x, y in raw_pairs), 'stitched': statistics.mean(y[m] for x, y in raw_pairs)} for m in METRICS} if raw_pairs else {})
    stages = {k: v['end'] - v['start'] for k, v in progress['stages'].items()}
    warnings = []
    for m, records in truncated.items():
        warnings.append(f'{m}: text truncation in {len(records)} records / {len({r["prompt_id"] for r in records if r["primary"]})} primary prompts')
    models = {m: read(a.input / (m + '.config.json'))['resolved_model']['model'] for m in METRICS[1:]}
    for name in ['structure', 'render', 'vqa', 'pe', 'siglip2']:
        text = (a.input / (name + '.log')).read_text(encoding='utf-8')
        hits = [line for line in text.splitlines() if re.search(r'Traceback \(most recent call last\)|CUDA out of memory|FileNotFoundError|RuntimeError:', line)]
        check(not hits, f'{name}: logged exceptions {hits[:2]}')
    audit = dict(passed=not failures, checks=checks, failures=failures, warnings=warnings,
                 archive_sha256=sha(a.archive), expected_records=462, primary_records=342,
                 matched_prompts=114, categories=21, category_level_groups=105,
                 image_files_verified=len(image_paths), journal_counts={k: len(v) for k, v in journals.items()},
                 source_scores_csv_sha256=sha(a.input / 'report/scores.csv'), models=models,
                 stage_elapsed_seconds=stages, total_stage_elapsed_seconds=progress['finished'] - progress['started'],
                 finished_utc=datetime.datetime.fromtimestamp(progress['finished'], datetime.timezone.utc).isoformat(),
                 truncation_records=dict(truncated))
    analysis = dict(overall=overall, by_level=by_level, by_category=by_category, by_category_level=by_category_level,
                    category_level_equal_weight=balanced, paired_comparisons=comparisons, category_leads_including_ties=category_leads,
                    auxiliary=auxiliary, protocol=summary['protocol'], audit=audit)
    add_diagnostics(analysis, primary)
    (a.out / '核查与汇总.json').write_bytes((json.dumps(analysis, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8'))
    print(json.dumps(dict(audit={k: v for k, v in audit.items() if k != 'truncation_records'}, overall=overall,
                          by_level=by_level, category_leads=category_leads, paired=comparisons, supplementary=auxiliary), ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit('AUDIT FAILED: ' + str(len(failures)))
    write_reports(a.out, analysis)


def add_diagnostics(analysis, primary):
    summary, subsets = {}, {}
    for metric, limit in [('pe', 72), ('siglip2', 64)]:
        records = analysis['audit']['truncation_records'].get(metric, [])
        unique = {r['prompt_id']: r for r in records if r['primary'] and r['system'] == 'BrickMore'}
        counts = collections.Counter(r['prompt_id'] for r in records if r['primary'])
        if any(n != 3 for n in counts.values()):
            raise ValueError('Truncation differs across matched systems: ' + metric)
        summary[metric] = dict(context_length=limit, all_records=len(records), primary_prompts=len(unique),
                               by_level=dict(sorted(collections.Counter(r['level'] for r in unique.values()).items())),
                               prompt_tokens={pid: r['tokens'] for pid, r in sorted(unique.items())})
        kept = [r for r in primary if r['prompt_id'] not in unique]
        subsets[metric] = dict(n_per_system=len(kept) // 3,
                               means={s: statistics.mean(r[metric] for r in kept if r['system'] == s) for s in SYSTEMS})
    analysis['truncation_summary'] = summary
    analysis['untruncated_subset_diagnostic'] = subsets


def write_reports(out, analysis):
    def value(m, x):
        return f'{x * 100:.2f}%' if m == 'pinv' else f'{x:.6f}'

    def md_table(headers, data):
        return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |'] +
                         ['| ' + ' | '.join(str(x) for x in row) + ' |' for row in data])

    overall = analysis['overall']
    overview = [[s, 114] + [value(m, overall[s][m]) for m in METRICS] for s in SYSTEMS]
    paragraphs = [
        '# BrickMore、BrickGPT、BrickNet 全量测评结果核查',
        '主对照采用 114 条相同 prompt，三个系统各 114 条；额外候选及 raw/stitched 对照独立保留。',
        '## 完整性与主要结果',
        f'全量 462 条、3696 张图片及四项评分均完整。已通过 {analysis["audit"]["checks"]:,} 项记录、哈希、配置及汇总一致性核查。原始评分与服务器报告的均值一致。',
        md_table(['系统', '主对照数量', 'P_inv（低优）', 'VQAScore（高优）', 'PE（高优）', 'SigLIP2（高优）'], overview),
        'BrickMore 在本次固定主对照的三项图文均值上均最高。P_inv 上，BrickMore 与 BrickGPT 均为零；不能据此区分二者。',
        'P_inv 主表采用每个模型比例的算术平均（macro）。BrickNet 按全部动作数加权的 micro 为 '
        + f'{overall["BrickNet"]["pinv_micro"] * 100:.2f}%。这两个分母不同，不混用。',
        md_table(['系统', '平均零件数', '无碰撞模型数（文件顺序）'],
                 [[s, f'{overall[s]["mean_parts"]:.1f}', f'{overall[s]["zero_collision_models"]}/114'] for s in SYSTEMS]),
        '## 与 BrickGPT 的同 prompt 配对比较',
        md_table(['指标', 'BrickMore − BrickGPT', '胜', '平', '负'],
                 [[LABELS[m], f'{analysis["paired_comparisons"]["BrickGPT"][m]["mean_difference"]:.6f}'] +
                  [analysis['paired_comparisons']['BrickGPT'][m][k] for k in ['wins', 'ties', 'losses']] for m in METRICS]),
        '胜平负按 114 条相同 prompt 逐条计算；差值绝对值不超过 1e-12 计为平。未增加显著性检验。',
        '## 按 Level 对比',
    ]
    for m in METRICS:
        paragraphs += ['### ' + LABELS[m], md_table(['Level', '每系统数量'] + list(SYSTEMS),
                                                   [[f'L{k}', g['BrickMore']['n']] + [value(m, g[s][m]) for s in SYSTEMS] for k, g in analysis['by_level'].items()])]
    paragraphs += ['## 按类别对比']
    for m in METRICS:
        paragraphs += ['### ' + LABELS[m], md_table(['类别', '每系统数量'] + list(SYSTEMS),
                                                   [[k, g['BrickMore']['n']] + [value(m, g[s][m]) for s in SYSTEMS] for k, g in analysis['by_category'].items()])]
    paragraphs += ['## 105 个类别×Level 等权的补充口径',
                   '主表按 114 条 prompt 等权，部分类别×Level 有多条 prompt。下面先在每个类别×Level 内平均，再对 105 组等权；这是口径核对，不替代主表。',
                   md_table(['系统'] + [LABELS[m] for m in METRICS], [[s] + [value(m, analysis['category_level_equal_weight'][s][m]) for m in METRICS] for s in SYSTEMS]),
                   '## 结果使用边界',
                   '- P_inv 是按文件导出顺序、原版 BrickNet inset 碰撞内核计算的无效放置比例；原始生成顺序未验证。零值不等于承重、连接性或整体物理稳定性已经验证。',
                   '- 图文分数使用 8 视角最大值，再对模型取平均；VQA、PE、SigLIP2 不是人工合格率或分类准确率。',
                   '- 所有系统使用统一黄色与同一网格渲染协议，无法评价原始配色；本次分数不与旧渲染协议的历史数字混合。',
                   '- BrickMore 主对照采用已提供的首个候选及优先 stitched 的最终版本。输入已有的人工筛选、后处理和生成过滤差异随数据保留，结论适用于这批交付模型。']
    if analysis['audit']['warnings']:
        paragraphs.append('## 文本截断诊断')
        for m, info in analysis['truncation_summary'].items():
            paragraphs.append(f'- {LABELS[m]} 的文本上下文上限为 {info["context_length"]} token；'
                              f'{info["primary_prompts"]}/114 条主对照 prompt 被截断，三个系统受影响的 prompt 相同。'
                              f'全量记录中共 {info["all_records"]} 条受到影响。')
        paragraphs.append('主要影响 L4/L5，SigLIP2 另有 1 条 L3。模型只评估截断后能读到的文本，不能据此认定完整长提示词中的所有细节均被核对。')
        union = sorted(set().union(*(set(x['prompt_tokens']) for x in analysis['truncation_summary'].values())))
        paragraphs.append(md_table(['prompt_id', 'PE token 数 / 上限 72', 'SigLIP2 token 数 / 上限 64'],
                                   [[pid] + [f'{analysis["truncation_summary"][m]["prompt_tokens"][pid]}/{analysis["truncation_summary"][m]["context_length"]}'
                                              if pid in analysis['truncation_summary'][m]['prompt_tokens'] else '未截断' for m in ['pe', 'siglip2']] for pid in union]))
        paragraphs += ['### 未截断子集的补充检查',
                       '下面仅用于查看剔除截断 prompt 后的均值方向，不替代 114 prompt 主表；子集的 Level 构成发生变化，不与主表当成同一个总体。',
                       md_table(['指标', '每系统数量'] + list(SYSTEMS),
                                [[LABELS[m], g['n_per_system']] + [f'{g["means"][s]:.6f}' for s in SYSTEMS] for m, g in analysis['untruncated_subset_diagnostic'].items()])]
    paragraphs += ['## 补充版本', f'额外 {analysis["auxiliary"]["records"]} 条记录独立于 342 条主对照。'
                   f'其中可配成同 caption 的 BrickMore 主候选 raw/stitched 对照有 {analysis["auxiliary"]["brickmore_raw_vs_stitched_primary_pairs"]} 对；补充分数不加入三模型主表。']
    paragraphs += ['## 来源', '源文件为用户提供的 Results.rar；本次只读核查 comparison_full，comparison_smoke 仅作为小样本记录保留。逐模型数据位于原报告 scores.csv，原始每视角分数及配置位于对应 JSONL/JSON。']
    text = '\n\n'.join(paragraphs) + '\n'
    (out / '三模型测评结果分析.md').write_bytes(text.encode('utf-8'))

    def html_table(headers, data):
        return '<table><thead><tr>' + ''.join('<th>' + html.escape(str(h)) + '</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + html.escape(str(c)) + '</td>' for c in row) + '</tr>' for row in data) + '</tbody></table>'

    sections = ['<h1>三模型测评结果核查</h1><p>114 条相同 prompt · 三个系统各 114 条主对照 · 全量 462 条模型版本</p>',
                '<p>四项评分及 3696 张图片均完整，逐条评分、配置、图片哈希与原报告汇总已核对。BrickMore 的三项图文均值最高；P_inv 与 BrickGPT 同为零。</p>',
                html_table(['系统', 'n', 'P_inv ↓', 'VQA ↑', 'PE ↑', 'SigLIP2 ↑'], overview),
                '<p>P_inv 以百分比展示；图文分数按原始量纲展示，不代表准确率。详细口径和限制见页面底部。</p>']
    for m in METRICS:
        sections.append('<h2>' + LABELS[m] + '</h2>')
        sections.append(html_table(['Level', '每系统 n'] + list(SYSTEMS), [[f'L{k}', g['BrickMore']['n']] + [value(m, g[s][m]) for s in SYSTEMS] for k, g in analysis['by_level'].items()]))
        sections.append('<details><summary>展开 21 个类别</summary>' + html_table(['类别', '每系统 n'] + list(SYSTEMS), [[k, g['BrickMore']['n']] + [value(m, g[s][m]) for s in SYSTEMS] for k, g in analysis['by_category'].items()]) + '</details>')
    sections.append('<h2>结果使用边界</h2><p>采用 8 视角最大值再平均。P_inv 按文件导出顺序测碰撞，未验证原始生成顺序，也不等于整体物理稳定性。统一黄色无法测配色准确性。保留输入已有筛选和后处理；本次结论适用于这批交付模型。未与旧渲染协议的数字混用。</p>')
    if analysis['audit']['warnings']:
        sections.append('<h2>文本截断</h2><ul>' + ''.join('<li>' + html.escape(f'{LABELS[m]}：上限 {v["context_length"]} token，{v["primary_prompts"]}/114 条主对照 prompt 发生截断，三个系统受影响的 prompt 相同。') + '</li>' for m, v in analysis['truncation_summary'].items()) + '</ul><p>主要影响 L4/L5。完整长提示词中的所有细节未必进入评分模型。具体 prompt 清单见同目录 Markdown 报告。</p>')
    page = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>三模型测评结果核查</title><style>body{font:16px/1.7 system-ui,"Microsoft YaHei",sans-serif;color:#172635;max-width:1100px;margin:36px auto;padding:0 22px}h1{font-size:28px}h2{margin-top:36px;font-size:21px}table{width:100%;border-collapse:collapse;margin:16px 0 24px;font-variant-numeric:tabular-nums}th{background:#edf1f5;text-align:right}td,th{padding:9px 14px;border-bottom:1px solid #dde3e9;text-align:right}td:first-child,th:first-child{text-align:left}p{max-width:1000px}details{margin-bottom:30px}summary{cursor:pointer;color:#205690}@media(max-width:650px){body{font-size:14px;padding:0 12px}td,th{padding:7px 5px}h1{font-size:23px}}</style>' + ''.join(sections) + '</html>'
    (out / '三模型测评结果分析.html').write_bytes(page.encode('utf-8'))


if __name__ == '__main__':
    main()
