"""Coverage-aware, matched-prompt comparison; no composite metric or imputed scores."""
import argparse,collections,csv,html,json,statistics
from pathlib import Path
from common import dump,rows

def make(manifest,out):
    inputs=rows(manifest);scores={name:{r['sample_id']:r for r in rows(out/(name+'.jsonl'))} for name in ['structure','vqa','pe','siglip2']};table=[]
    for row in inputs:
        sid=row['sample_id'];struct=scores['structure'].get(sid,{});value={k:row.get(k) for k in ['sample_id','system','model_id','variant','category','level','batch','prompt_id','primary','part_count','caption']}
        value.update(pinv=struct.get('pinv'),invalid_placements=struct.get('invalid_placements'),structure_status=struct.get('status','missing'))
        for metric in ['vqa','pe','siglip2']:value[metric]=scores[metric].get(sid,{}).get('max_score')
        table.append(value)
    def aggregate(seq):
        result={'records':len(seq)}
        for metric in ['pinv','vqa','pe','siglip2']:
            valid=[r[metric] for r in seq if r[metric] is not None]
            result[metric]={'n':len(valid),'missing':len(seq)-len(valid),'mean':statistics.mean(valid) if valid else None}
        valid=[r for r in seq if r['pinv'] is not None]
        result['pinv_micro']=sum(r['invalid_placements'] for r in valid)/sum(r['part_count'] for r in valid) if valid else None
        return result
    primary={system:aggregate([r for r in table if r['system']==system and r['primary']]) for system in ['BrickMore','BrickGPT','BrickNet']}
    grouped=collections.defaultdict(list)
    for row in table:grouped[(row['system'],row['variant'],row['primary'],row['category'],row['level'])].append(row)
    by_group=[dict(system=k[0],variant=k[1],primary=k[2],category=k[3],level=k[4],**aggregate(v)) for k,v in grouped.items()]
    matched=collections.defaultdict(dict)
    for row in table:
        if row['primary']:matched[row['prompt_id']][row['system']]=row
    paired={}
    for metric in ['pinv','vqa','pe','siglip2']:
        eligible=[v for v in matched.values() if len(v)==3 and all(v[s][metric] is not None for s in primary)]
        paired[metric]=dict(common_prompts=len(eligible),means={s:statistics.mean(v[s][metric] for v in eligible) if eligible else None for s in primary},
          differences={s+'_minus_BrickMore':statistics.mean(v[s][metric]-v['BrickMore'][metric] for v in eligible) if eligible else None for s in ['BrickGPT','BrickNet']})
    summary=dict(samples=len(table),primary=primary,paired=paired,by_category_level=by_group,
       protocol=dict(structure='pinv_file_order, original BrickNet 0.1.0 inset collision kernel; original generation order not verified; no fixed-edge exemptions',
          image_scores='Eight fixed views, max per model then arithmetic mean; no best-of-N sample selection',
          rendering='Shared actual inset part surfaces, orthographic CPU rasterizer, 512px, 25-degree elevation, 45-degree azimuth steps, uniform yellow',
          color='Uniform display color; no claim of generated-color accuracy',
          original_paper_reproduction=False,old_run_scores_mixed=False,
          primary='114 matched prompts x three systems; fixed first supplied BrickMore candidate and final/stitched preference; raw counterparts and extra candidates are supplementary'))
    report=out/'report';report.mkdir(parents=True,exist_ok=True);dump(report/'summary.json',summary)
    def write_csv(path,values):
        if not values:return
        with path.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(values[0]));w.writeheader();w.writerows(values)
    write_csv(report/'scores.csv',table)
    flat=[]
    for value in by_group:
        entry={k:value[k] for k in ['system','variant','primary','category','level','records','pinv_micro']}
        for metric in ['pinv','vqa','pe','siglip2']:
            entry[metric]=value[metric]['mean'];entry[metric+'_n']=value[metric]['n'];entry[metric+'_missing']=value[metric]['missing']
        flat.append(entry)
    write_csv(report/'by_category_level.csv',flat)
    headers=['system','records','pinv','vqa','pe','siglip2'];body=''
    for system,value in primary.items():
        cells=[system,str(value['records'])]+[('NA' if value[m]['mean'] is None else f'{value[m]["mean"]:.6f}')+f' (n={value[m]["n"]})' for m in headers[2:]]
        body+='<tr>'+''.join('<td>'+html.escape(c)+'</td>' for c in cells)+'</tr>'
    page='<!doctype html><meta charset="utf-8"><title>BrickMore / BrickGPT / BrickNet comparison</title><style>body{font:16px system-ui;max-width:1200px;margin:30px auto;padding:0 20px;background:#f6f7fa;color:#152535}table{border-collapse:collapse;width:100%;background:white}td,th{padding:14px;border:1px solid #dce2e8;text-align:left}pre{white-space:pre-wrap;background:white;padding:20px;border-radius:12px}</style><h1>Three-system LEGO comparison</h1><p>Primary: fixed matched prompts. NA is unavailable, never zero. P_inv is lower-better; image metrics are higher-better.</p><table><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr>'+body+'</table><h2>Protocol and limitations</h2><pre>'+html.escape(json.dumps(summary['protocol'],indent=2))+'</pre><h2>Strict three-way paired results</h2><pre>'+html.escape(json.dumps(paired,indent=2))+'</pre><p>Full rows: scores.csv; category/level breakdown: by_category_level.csv.</p>'
    (report/'report.html').write_text(page,encoding='utf-8');print('REPORT '+str(report/'report.html'),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();make(a.manifest,a.out)
