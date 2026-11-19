"""Paired significance re-analysis of the existing per-prompt scores (V1.6, U5).

Input : scores.csv (copied unchanged from
        Results/three_model_comparison_20261111/intake/Results/comparison_full/report/scores.csv)
Rows  : primary=True only -> one output per system per prompt (114 prompts x 3 systems).
Pairing: by prompt_id (same caption text across systems).
Tests : two-sided exact sign test (binomial, ties dropped) and two-sided Wilcoxon
        signed-rank test (scipy default method='auto', zero_method='wilcox'; with n=114 > 50
        scipy uses the normal approximation without continuity correction) on per-prompt differences BrickForma - opponent.
Family: 3 metrics (vqa, pe, siglip2) x 2 opponents (BrickGPT, BrickNet) = 6 tests,
        Holm-Bonferroni correction applied separately within the sign-test family and
        within the Wilcoxon family. P_inv is not tested.
"""
import csv, json, sys, hashlib, collections
import numpy as np
from scipy import stats
import scipy

path = sys.argv[1] if len(sys.argv) > 1 else 'scores.csv'
sha = hashlib.sha256(open(path, 'rb').read()).hexdigest()
rows = [r for r in csv.DictReader(open(path, newline='', encoding='utf-8')) if r['primary'] == 'True']
by = collections.defaultdict(dict)
for r in rows:
    assert r['system'] not in by[r['prompt_id']], 'duplicate primary row'
    by[r['prompt_id']][r['system']] = r
prompts = sorted(by)
assert all(len(by[p]) == 3 for p in prompts)

def holm(ps):
    m = len(ps); order = sorted(range(m), key=lambda i: ps[i]); adj = [0.0]*m; run = 0.0
    for k, i in enumerate(order):
        run = max(run, min(1.0, (m-k)*ps[i])); adj[i] = run
    return adj

res = []
for opp in ['BrickGPT', 'BrickNet']:
    for met in ['vqa', 'pe', 'siglip2']:
        a = np.array([float(by[p]['BrickForma'][met]) for p in prompts])
        b = np.array([float(by[p][opp][met]) for p in prompts])
        d = a - b
        wins, losses, ties = int((d > 0).sum()), int((d < 0).sum()), int((d == 0).sum())
        sign_p = stats.binomtest(wins, wins + losses, 0.5, alternative='two-sided').pvalue
        w = stats.wilcoxon(a, b, alternative='two-sided')
        res.append(dict(opponent=opp, metric=met, n=len(prompts), wins=wins, losses=losses, ties=ties,
                        mean_brickforma=float(a.mean()), mean_opponent=float(b.mean()),
                        median_diff=float(np.median(d)), sign_p=float(sign_p),
                        wilcoxon_W=float(w.statistic), wilcoxon_p=float(w.pvalue)))
for key in ['sign_p', 'wilcoxon_p']:
    for r, adj in zip(res, holm([r[key] for r in res])):
        r[key + '_holm'] = adj
out = dict(input=path, input_sha256=sha, scipy=scipy.__version__, numpy=np.__version__,
           n_prompts=len(prompts), results=res)
json.dump(out, open('significance.json', 'w'), indent=2)
print(f"input sha256 {sha}; scipy {scipy.__version__}; n={len(prompts)} paired prompts")
print(f"{'opponent':9} {'metric':8} {'W/L/T':10} {'sign p':>10} {'Holm':>10} {'Wilcoxon W':>11} {'p':>10} {'Holm':>10}")
for r in res:
    print(f"{r['opponent']:9} {r['metric']:8} {r['wins']}/{r['losses']}/{r['ties']:<5} {r['sign_p']:10.3g} {r['sign_p_holm']:10.3g} {r['wilcoxon_W']:11.1f} {r['wilcoxon_p']:10.3g} {r['wilcoxon_p_holm']:10.3g}")
