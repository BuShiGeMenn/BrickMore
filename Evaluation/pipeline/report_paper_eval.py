"""Join metrics without inventing missing values; report groups and matched raw/stitched deltas."""
import argparse
import csv
import html
import json
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path
from paper_common import keyed, normalize_ids, read_jsonl, sha256, write_json


def mean(values):
    return statistics.mean(values) if values else None


def summarize(rows, names):
    result = {'samples':len(rows)}
    for name in names:
        values = [r[name] for r in rows if r.get(name) is not None]
        result[name] = {'n':len(values),'coverage':len(values)/len(rows) if rows else 0,
                        'mean':mean(values)}
    return result


def matched_pairs(rows, names):
    groups = defaultdict(dict)
    for row in rows:
        if row.get('candidate_id') and row.get('variant') in {'raw','stitched'}:
            key = (row.get('package',''),row['candidate_id'])
            if row['variant'] in groups[key]:
                raise ValueError(f'Duplicate paired candidate variant: {key}')
            groups[key][row['variant']] = row
    pairs = []
    for (package,candidate), versions in groups.items():
        if set(versions) != {'raw','stitched'}:
            continue
        raw,stitched = versions['raw'],versions['stitched']
        if raw.get('caption') != stitched.get('caption'):
            raise ValueError(f'Paired captions differ: {candidate}')
        pairs.append({'package':package,'candidate_id':candidate,
            **{name:stitched[name]-raw[name] if raw.get(name) is not None and stitched.get(name) is not None
                        else None for name in names}})
    return pairs


def write_csv(path, rows, fields):
    with path.open('w',encoding='utf-8-sig',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore')
        writer.writeheader(); writer.writerows(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True,type=Path)
    p.add_argument('--images',action='append',default=[],help='Distinct column name=metric.jsonl; repeat for each scorer')
    p.add_argument('--structure',type=Path)
    p.add_argument('--out',required=True,type=Path)
    args = p.parse_args()
    rows = normalize_ids(read_jsonl(args.manifest))
    indexed = keyed(rows)
    names,provenance = [],{}
    inputs = []
    for value in args.images:
        name,sep,path = value.partition('=')
        if (not sep or not re.fullmatch('[A-Za-z][A-Za-z0-9_]*',name) or name in names
                or name == 'pinv' or any(name in row for row in rows)):
            raise ValueError('Use unique metric column names, e.g. vqa_qwen2vl_2b=path.jsonl')
        names.append(name); inputs.append((name,Path(path),'max_score'))
    if args.structure:
        names.append('pinv_per_model'); inputs.append(('pinv_per_model',args.structure,'pinv'))
    for name,path,field in inputs:
        records = keyed(normalize_ids(read_jsonl(path)))
        extras = set(records)-set(indexed)
        if extras:
            raise ValueError(f'{path}: {len(extras)} sample IDs absent from report manifest')
        signatures = {r.get('config_signature') for r in records.values()}
        if len(signatures)>1:
            raise ValueError(f'{path}: mixed configurations')
        configs = [path.with_suffix('.config.json'),path.with_name(path.stem+'_config.json')]
        config_path = next((x for x in configs if x.is_file()),None)
        provenance[name] = {'path':str(path.resolve()),'sha256':sha256(path),
            'configuration':json.loads(config_path.read_text(encoding='utf-8')) if config_path else None}
        for sid,row in indexed.items():
            record = records.get(sid)
            value = record.get(field) if record else None
            if value is not None and (not isinstance(value,(int,float)) or not math.isfinite(value)):
                raise ValueError(f'{path}: non-finite score for {sid}')
            # Caption/model hashes must agree if present in both inputs.
            if record:
                for key in ['caption','model_sha256']:
                    if key in row and key in record and row[key]!=record[key]:
                        raise ValueError(f'{sid}: mismatched {key} across metrics')
            row[name] = value
    if not names:
        raise ValueError('Supply at least one metric')
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row.get('variant','unknown'),row.get('category','unknown'),row.get('level','unknown'))].append(row)
    groups = [{'variant':v,'category':c,'level':l,**summarize(items,names)}
              for (v,c,l),items in sorted(grouped.items())]
    pairs = matched_pairs(rows,names)
    args.out.mkdir(parents=True,exist_ok=True)
    structure_summary_path = args.structure.with_suffix('.summary.json') if args.structure else None
    summary = {'structure_aggregation':json.loads(structure_summary_path.read_text(encoding='utf-8'))
        if structure_summary_path and structure_summary_path.exists() else None,
        'overall':summarize(rows,names),'by_variant':{
        v:summarize([r for r in rows if r.get('variant','unknown')==v],names)
        for v in sorted({r.get('variant','unknown') for r in rows})},
        'groups':groups,'paired_stitched_minus_raw':summarize(pairs,names),
        'provenance':provenance,'exact_paper_reproduction':False,
        'interpretation':'Show coverage; do not compare unpaired means as a stitching effect. '
            'Do not combine semantic similarity and collision validity into an unvalidated total.'}
    write_json(args.out/'summary.json',summary)
    fields = ['sample_id','package','candidate_id','category','level','variant','caption',*names]
    write_csv(args.out/'scores.csv',rows,fields)
    write_csv(args.out/'paired_changes.csv',pairs,['package','candidate_id',*names])
    headers = ''.join('<th>'+html.escape(n)+'</th>' for n in fields)
    body = ''.join('<tr>'+''.join('<td>'+html.escape(str(r.get(n,'')) if r.get(n) is not None else 'NA')+'</td>'
                                for n in fields)+'</tr>' for r in rows)
    document = '<!doctype html><meta charset="utf-8"><title>BrickNet evaluation</title><style>body{font:14px sans-serif;margin:24px}table{border-collapse:collapse}td,th{border:1px solid #ddd;padding:6px}th{position:sticky;top:0;background:#eee}pre{white-space:pre-wrap}</style><h1>BrickNet evaluation</h1><p>NA means unavailable. Each metric retains its own model/protocol. P_inv aggregation and historical reproduction limits are recorded in the source configuration.</p><pre>'+html.escape(json.dumps({k:v for k,v in summary.items() if k not in {'groups','provenance'}},ensure_ascii=False,indent=2))+'</pre><table><thead><tr>'+headers+'</tr></thead><tbody>'+body+'</tbody></table>'
    (args.out/'report.html').write_text(document,encoding='utf-8')


if __name__ == '__main__':
    main()
