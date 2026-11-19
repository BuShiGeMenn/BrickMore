"""Descriptive robustness tables from existing records (V1.6, E-3/E-4). No new runs.
scores.csv: per-prompt scores; pe.jsonl / siglip2.jsonl: per-view text_truncated flags."""
import csv, json, collections, sys
rows=[r for r in csv.DictReader(open('scores.csv',encoding='utf-8')) if r['primary']=='True']
S=['BrickForma','BrickGPT','BrickNet']; M=['vqa','pe','siglip2']
mean=lambda xs: sum(xs)/len(xs)
out={}
# per level
lv=collections.defaultdict(lambda: collections.defaultdict(list)); nlev=collections.Counter()
for r in rows:
    for m in M: lv[(int(r['level']),r['system'])][m].append(float(r[m]))
    if r['system']=='BrickForma': nlev[int(r['level'])]+=1
out['per_level']={f"L{l}":{'n':nlev[l],**{s:{m:mean(lv[(l,s)][m]) for m in M} for s in S}} for l in range(1,6)}
# equal weight per category-level group
g=collections.defaultdict(lambda: collections.defaultdict(list))
for r in rows:
    for m in M: g[(r['category'],r['level'],r['system'])][m].append(float(r[m]))
groups=sorted({(r['category'],r['level']) for r in rows})
out['group_equal']={'n_groups':len(groups),**{s:{m:mean([mean(g[(c,l,s)][m]) for c,l in groups]) for m in M} for s in S}}
# untruncated subsets
for met,f in [('pe','pe.jsonl'),('siglip2','siglip2.jsonl')]:
    tr={}
    for line in open(f):
        x=json.loads(line)
        if not x['primary']: continue
        t=any(dd.get('text_truncated') for dd in x['diagnostics'])
        tr.setdefault(x['prompt_id'],set()).add(t)
    assert all(len(v)==1 for v in tr.values())
    keep={p for p,v in tr.items() if not list(v)[0]}
    out[f'untruncated_{met}']={'n':len(keep),**{s:mean([float(r[met]) for r in rows if r['system']==s and r['prompt_id'] in keep]) for s in S}}
json.dump(out,open('robustness.json','w'),indent=2)
print(json.dumps(out,indent=1))
