"""Coverage-aware, matched-prompt comparison; no composite metric or imputed scores."""
import argparse,collections,csv,html,json,statistics
from pathlib import Path
from common import ROOT,dump,rows

METRICS=('pinv','vqa','pe','siglip2')
SYSTEMS=('BrickMore','BrickGPT','BrickNet')

def paired_scores(table,systems):
    matched=collections.defaultdict(dict)
    for row in table:
        if row['system'] in systems:
            cohort=matched[row['prompt_id']]
            if row['system'] in cohort:raise ValueError(f'Duplicate paired record: {row["prompt_id"]} {row["system"]}')
            cohort[row['system']]=row
    paired={}
    for metric in METRICS:
        eligible=[v for v in matched.values() if set(v)==set(systems)
                  and len({r['caption'] for r in v.values()})==1 and all(v[s][metric] is not None for s in systems)]
        baseline=systems[0]
        paired[metric]=dict(common_prompts=len(eligible),means={s:statistics.mean(v[s][metric] for v in eligible) if eligible else None for s in systems},
          differences={s+'_minus_'+baseline:statistics.mean(v[s][metric]-v[baseline][metric] for v in eligible) if eligible else None for s in systems[1:]})
    return paired

def make(manifest,out):
    inputs=rows(manifest);scores={name:{r['sample_id']:r for r in rows(out/(name+'.jsonl'))} for name in ['structure','vqa','pe','siglip2']};table=[]
    for row in inputs:
        sid=row['sample_id'];struct=scores['structure'].get(sid,{});value={k:row.get(k) for k in ['sample_id','system','model_id','variant','category','level','batch','prompt_id','primary','part_count','caption']}
        value.update(pinv=struct.get('pinv'),invalid_placements=struct.get('invalid_placements'),structure_status=struct.get('status','missing'))
        for metric in ['vqa','pe','siglip2']:value[metric]=scores[metric].get(sid,{}).get('max_score')
        table.append(value)
    def aggregate(seq):
        result={'records':len(seq)}
        for metric in METRICS:
            valid=[r[metric] for r in seq if r[metric] is not None]
            result[metric]={'n':len(valid),'missing':len(seq)-len(valid),'mean':statistics.mean(valid) if valid else None}
        valid=[r for r in seq if r['pinv'] is not None]
        result['pinv_micro']=sum(r['invalid_placements'] for r in valid)/sum(r['part_count'] for r in valid) if valid else None
        return result
    primary_rows=[r for r in table if r['primary']]
    primary={system:aggregate([r for r in primary_rows if r['system']==system]) for system in SYSTEMS}
    audit_path=ROOT/'Data/input_audit.json'
    audit=json.loads(audit_path.read_text(encoding='utf-8')) if audit_path.is_file() else {}
    cohort_definitions=audit.get('cohorts',{})
    grouped=collections.defaultdict(list)
    for row in table:
        batch=row['batch'] if cohort_definitions else None
        grouped[(row['system'],row['variant'],row['primary'],row['category'],row['level'],batch)].append(row)
    by_group=[dict(system=k[0],variant=k[1],primary=k[2],category=k[3],level=k[4],
                   **({'batch':k[5]} if cohort_definitions else {}),**aggregate(v)) for k,v in grouped.items()]
    paired=paired_scores(primary_rows,SYSTEMS)
    summary=dict(samples=len(table),primary=primary,paired=paired,by_category_level=by_group,
       protocol=dict(structure='pinv_file_order, original BrickNet 0.1.0 inset collision kernel; original generation order not verified; no fixed-edge exemptions',
          image_scores='Eight fixed views, max per model then arithmetic mean; no best-of-N sample selection',
          rendering='Shared actual inset part surfaces, orthographic CPU rasterizer, 512px, 25-degree elevation, 45-degree azimuth steps, uniform yellow',
          color='Uniform display color; no claim of generated-color accuracy',
          original_paper_reproduction=False,old_run_scores_mixed=False,
          primary=audit.get('primary_policy','Fixed same-prompt primary cohort')))
    batch_results={}
    for batch,definition in cohort_definitions.items():
        subset=[r for r in table if r['batch']==batch]
        if not subset:continue
        systems=definition['systems']
        batch_results[batch]=dict(expected_prompts=definition['prompts'],selected_prompts=len({r['prompt_id'] for r in subset}),
            systems={s:aggregate([r for r in subset if r['system']==s]) for s in systems},
            paired=paired_scores(subset,systems) if len(systems)>1 else {})
    if batch_results:summary['by_batch']=batch_results
    report=out/'report';report.mkdir(parents=True,exist_ok=True);dump(report/'summary.json',summary)
    def write_csv(path,values):
        if not values:return
        with path.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(values[0]));w.writeheader();w.writerows(values)
    write_csv(report/'scores.csv',table)
    def flatten(values,labels):
        for value in values:
            entry={k:value[k] for k in [*labels,'records','pinv_micro']}
            for metric in METRICS:
                entry[metric]=value[metric]['mean'];entry[metric+'_n']=value[metric]['n'];entry[metric+'_missing']=value[metric]['missing']
            yield entry
    group_labels=['system','variant','primary','category','level']+(['batch'] if cohort_definitions else [])
    write_csv(report/'by_category_level.csv',list(flatten(by_group,group_labels)))
    if batch_results:
        level_groups=collections.defaultdict(list)
        for r in table:level_groups[(r['batch'],r['system'],r['level'])].append(r)
        levels=[dict(batch=b,system=s,level=l,**aggregate(seq)) for (b,s,l),seq in sorted(level_groups.items())]
        write_csv(report/'by_batch_level.csv',list(flatten(levels,['batch','system','level'])))
    headers=['system','records','pinv','vqa','pe','siglip2']
    def show_table(system_values):
        body=''
        for system,value in system_values.items():
            cells=[system,str(value['records'])]+[('NA' if value[m]['mean'] is None else f'{value[m]["mean"]:.6f}')+f' (n={value[m]["n"]})' for m in METRICS]
            body+='<tr>'+''.join('<td>'+html.escape(c)+'</td>' for c in cells)+'</tr>'
        return '<table><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr>'+body+'</table>'
    if batch_results:
        tables=''
        for batch in sorted(batch_results,reverse=True):
            result=batch_results[batch]
            tables+=f'<h2>Group {batch} · {len(result["systems"])} systems</h2><p>{result["selected_prompts"]} prompts selected of {result["expected_prompts"]}.</p>'
            tables+=show_table(result['systems'])
            if result['paired']:
                tables+='<details><summary>Same-prompt paired scores</summary><pre>'+html.escape(json.dumps(result['paired'],indent=2))+'</pre></details>'
    else:
        tables=show_table(primary)+'<h2>Strict three-way paired results</h2><pre>'+html.escape(json.dumps(paired,indent=2))+'</pre>'
    page='<!doctype html><meta charset="utf-8"><title>BrickMore / BrickGPT / BrickNet comparison</title><style>body{font:16px system-ui;max-width:1200px;margin:30px auto;padding:0 20px;background:#f6f7fa;color:#152535}table{border-collapse:collapse;width:100%;background:white}td,th{padding:14px;border:1px solid #dce2e8;text-align:left}pre{white-space:pre-wrap;background:white;padding:20px;border-radius:12px}</style><h1>LEGO model comparison</h1><p>NA denotes unavailable scores. P_inv is lower-better. Image metrics are higher-better.</p>'+tables+'<h2>Protocol and limitations</h2><pre>'+html.escape(json.dumps(summary['protocol'],indent=2))+'</pre><p>Full rows: scores.csv. Category/level breakdown: by_category_level.csv.</p>'
    (report/'report.html').write_text(page,encoding='utf-8');print('REPORT '+str(report/'report.html'),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();make(a.manifest,a.out)
