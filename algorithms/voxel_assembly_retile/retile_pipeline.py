"""Versioned single-model exports and independent readback for local retiling."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import time

import retile_core as core
import relaxed_pipeline as legacy
import modular_gravity as physics

VERSION='quality_local_bridge_retile_delivery_v1'
HERE=Path(__file__).resolve().parent
REPO=HERE.parent.parent


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def code_hashes():
    paths=[]
    for name in ('voxel_assembly_b','voxel_assembly_q2','voxel_assembly_q3','voxel_assembly_q4','voxel_assembly_relaxed'):
        paths.extend(p for p in (HERE.parent/name).rglob('*.py') if not p.name.startswith('test_') and 'reports' not in p.parts)
    paths.extend([HERE/'retile_core.py',HERE/'retile_pipeline.py'])
    return {p.relative_to(REPO).as_posix():digest(p) for p in sorted(set(paths))}


def dump(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def target_value(source,cells,repair):
    value=core.base.strict.old.target_value(source,cells,repair)
    if value['derivedGeometry']:value['modelId']=value['modelId'].replace('_q2_','_q6_')
    return value


def read_baseline(folder,source):
    """Check real files/geometry; never reuse an unchecked success flag."""
    folder=Path(folder);report=json.loads((folder/'report.json').read_bytes())
    if report['sourceFileSha256']!=digest(source):raise ValueError('Baseline belongs to different source bytes')
    for name,expected in report['outputFileSha256'].items():
        if Path(name).name!=name or digest(folder/name)!=expected:raise ValueError('Baseline file hash changed')
    if digest(folder/'source.model.json')!=digest(source):raise ValueError('Baseline source copy changed')
    original=core.base.q.a.dataset_model(json.loads(Path(source).read_bytes()))[0].cells
    cells=core.base.q.a.dataset_model(json.loads((folder/'target.model.json').read_bytes()))[0].cells
    assembly=json.loads((folder/'assembly.json').read_bytes());bricks=assembly['bricks']
    first=core.base.audit(bricks,cells);second=legacy.graph_readback(bricks,cells)
    if any(first[k]!=second[k] for k in second) or first!=report['geometryValidation']:
        raise ValueError('Baseline actual geometry differs from its report')
    if not core.base.strict.m.repair_audit(original,cells,.02)['passed']:raise ValueError('Baseline exceeds unchanged repair gate')
    suffix='' if first['passed'] else '.draft'
    if core.base.q.a.parse_ldr((folder/f'model{suffix}.ldr').read_text(encoding='utf-8'))!=bricks:raise ValueError('Baseline LDraw differs')
    txt=[core.base.q.a.Placement.parse(line) for line in (folder/f'model{suffix}.txt').read_text().splitlines() if line.strip()]
    if [tuple(getattr(b,k) for k in ('h','w','x','y','z')) for b in txt]!=[tuple(b[k] for k in ('h','w','x','y','z')) for b in bricks]:raise ValueError('Baseline TXT differs')
    gate=json.loads((folder/'additions_only_evidence.json').read_bytes())
    gate_cells=core.base.q.a.dataset_model(gate['target'])[0].cells
    return dict(bricks=bricks,targetCells=cells,additionsOnlyEvidence=dict(bricks=gate['bricks'],targetCells=gate_cells,passed=gate['geometryPassed'],auditor=gate['auditor']))


def verify(folder,source_path=None):
    folder=Path(folder);report=json.loads((folder/'report.json').read_bytes())
    if report['algorithmVersion']!=VERSION:raise ValueError('Wrong local-retiling output version')
    expected_files={'source.model.json','target.model.json','assembly.json','validation.json','physics.json','additions_only_evidence.json'}
    suffix='' if report['status']=='success' else '.draft'
    expected_files.update({f'model{suffix}.txt',f'model{suffix}.ldr'})
    if report.get('sourcePromptFileSha256') is not None:expected_files.add('source.prompts.json')
    if set(report['outputFileSha256'])!=expected_files:raise ValueError('Output file inventory differs')
    for name,expected in report['outputFileSha256'].items():
        if Path(name).name!=name or digest(folder/name)!=expected:raise ValueError('Output file SHA differs')
    if digest(folder/'source.model.json')!=report['sourceFileSha256']:raise ValueError('Original copy changed')
    if source_path is not None and digest(source_path)!=report['sourceFileSha256']:raise ValueError('Original source changed')
    source=json.loads((folder/'source.model.json').read_bytes());target=json.loads((folder/'target.model.json').read_bytes())
    original=core.base.q.a.dataset_model(source)[0].cells;cells=core.base.q.a.dataset_model(target)[0].cells
    repair=core.base.strict.m.repair_audit(original,cells,.02)
    if not repair['passed'] or repair!=report['repairAudit'] or target!=target_value(source,cells,repair):raise ValueError('Derived target or repair gate differs')
    assembly=json.loads((folder/'assembly.json').read_bytes());raw=assembly['bricks']
    if assembly['policy']!=core.base.POLICY or assembly['algorithmVersion']!=VERSION or assembly['modelId']!=target['modelId'] or assembly['sourceModelId']!=source['modelId']:raise ValueError('Assembly identity or geometry policy differs')
    first=core.base.audit(raw,cells);second=legacy.graph_readback(raw,cells)
    if any(first[k]!=second[k] for k in second) or first!=report['geometryValidation'] or first!=json.loads((folder/'validation.json').read_bytes()):raise ValueError('Independent geometry readback differs')
    if report['status']!=('success' if first['passed'] else 'draft') or assembly['status']!=report['status']:raise ValueError('Incorrect success label')
    if not first['exactCoverage']:raise ValueError('Retiling draft must cover its complete target')
    if core.base.q.a.parse_ldr((folder/f'model{suffix}.ldr').read_text(encoding='utf-8'))!=raw:raise ValueError('Actual LDraw differs from JSON')
    txt=[core.base.q.a.Placement.parse(line) for line in (folder/f'model{suffix}.txt').read_text().splitlines() if line.strip()]
    if [tuple(getattr(b,k) for k in ('h','w','x','y','z')) for b in txt]!=[tuple(b[k] for k in ('h','w','x','y','z')) for b in raw]:raise ValueError('Actual TXT differs from JSON')
    gate=json.loads((folder/'additions_only_evidence.json').read_bytes())
    if gate!=report['additionsOnlyGate'] or gate['sourceFileSha256']!=report['sourceFileSha256']:raise ValueError('Additions-only evidence differs')
    gate_cells=core.base.q.a.dataset_model(gate['target'])[0].cells
    if set(original)-set(gate_cells) or not core.base.q.repair_audit(original,gate_cells,.02)['passed']:raise ValueError('Additions-only evidence changes protected input')
    auditor=core.base.q.independent_audit if gate['auditor']=='strict_q4' else core.base.audit if gate['auditor']=='relaxed_modular' else None
    if auditor is None or auditor(gate['bricks'],gate_cells)['passed']!=gate['geometryPassed']:raise ValueError('Incorrect additions-only verdict')
    if repair['removedVoxelCount'] and gate['geometryPassed']:raise ValueError('Deletion without actual additions failure')
    physical=json.loads((folder/'physics.json').read_bytes())
    if report['physics']!=core.base.strict.physics_summary(physical):raise ValueError('Physical summary differs')
    if first['passed'] and report['options']['physicsSeconds']>0:physics.verify(raw,cells,physical)
    elif physical['status'] not in ('not_attempted_geometry_only','not_evaluated_geometry_failed') or physical['gravityEquilibriumPassed'] or physical['layerPrefixGravityPassed']:raise ValueError('Incorrect skipped physical verdict')
    if report['qualityScreenedSuccess']!=(first['passed'] and physical['layerPrefixGravityPassed']):raise ValueError('Incorrect physical pass flag')
    if report['modelId']!=source['modelId'] or report['targetModelId']!=target['modelId']:raise ValueError('Report model identity differs')
    if report['sourcePromptFileSha256'] is not None and digest(folder/'source.prompts.json')!=report['sourcePromptFileSha256']:raise ValueError('Original prompt bytes changed')
    for value in (report,assembly,physical):
        if value.get('staticVerified') is not None or value.get('fullPhysics') is not False:raise ValueError('Unsupported physical certification')
    if report.get('semanticVerified') is not False:raise ValueError('Unsupported semantic certification')
    return report


def run_one(source_path,out,seconds=8.,physics_seconds=5.,baseline_folder=None):
    source_path=Path(source_path);out=Path(out)
    if not math.isfinite(physics_seconds) or physics_seconds<0:raise ValueError('physicsSeconds must be finite and nonnegative')
    options=dict(seconds=seconds,physicsSeconds=physics_seconds,ratio=.02)
    if out.exists():
        report=verify(out,source_path)
        if report['options']!=options or report['sourceCodeSha256']!=code_hashes():raise ValueError('Existing output belongs to different code or options')
        return report
    source=json.loads(source_path.read_bytes());original=core.base.q.a.dataset_model(source)[0].cells
    baseline=read_baseline(baseline_folder,source_path) if baseline_folder is not None else None
    selected=core.optimize(original,seconds=seconds,baseline=baseline)
    raw=selected['bricks'];cells=selected['targetCells'];repair=selected['repairAudit'];validation=core.base.audit(raw,cells)
    status='success' if validation['passed'] else 'draft';target=target_value(source,cells,repair)
    if validation['passed'] and physics_seconds>0:physical=physics.screen(raw,cells,physics_seconds)
    else:physical=dict(status='not_attempted_geometry_only' if validation['passed'] else 'not_evaluated_geometry_failed',gravityEquilibriumPassed=False,layerPrefixGravityPassed=False,assumptions=physics.g.ASSUMPTIONS,staticVerified=None,fullPhysics=False)
    evidence=selected.get('additionsOnlyEvidence')
    if evidence is None:evidence=dict(bricks=raw,targetCells=cells,passed=validation['passed'],auditor='relaxed_modular')
    gate_cells=evidence['targetCells'];gate_repair=core.base.q.repair_audit(original,gate_cells,.02)
    if not gate_repair['passed']:raise ValueError('Selected optimizer supplied an invalid additions-only gate')
    gate=dict(bricks=evidence['bricks'],target=target_value(source,gate_cells,gate_repair),geometryPassed=evidence['passed'],auditor=evidence.get('auditor','relaxed_modular'),sourceFileSha256=digest(source_path),boundedFailureNotImpossibility=True)
    out.mkdir(parents=True)
    shutil.copyfile(source_path,out/'source.model.json')
    prompt=source_path.with_name('source.prompts.json' if source_path.name=='source.model.json' else 'prompts.json')
    if prompt.is_file():shutil.copyfile(prompt,out/'source.prompts.json')
    dump(out/'target.model.json',target)
    dump(out/'assembly.json',dict(algorithmVersion=VERSION,modelId=target['modelId'],sourceModelId=source['modelId'],status=status,policy=core.base.POLICY,bricks=raw,staticVerified=None,fullPhysics=False))
    dump(out/'validation.json',validation);dump(out/'physics.json',physical);dump(out/'additions_only_evidence.json',gate)
    suffix='' if validation['passed'] else '.draft'
    (out/f'model{suffix}.txt').write_text(''.join(core.base.q.a.Placement(**{k:b[k] for k in ('h','w','x','y','z')}).to_txt() for b in raw),encoding='utf-8')
    (out/f'model{suffix}.ldr').write_text(core.base.q.a.to_ldr(dict(status=status,bricks=[{k:b[k] for k in ('h','w','x','y','z')} for b in raw]),cells),encoding='utf-8')
    report=dict(algorithmVersion=VERSION,optimizerVersion=core.VERSION,modelId=source['modelId'],targetModelId=target['modelId'],category=source.get('category'),status=status,
                sourceFileSha256=digest(source_path),sourcePromptFileSha256=digest(prompt) if prompt.is_file() else None,sourceCodeSha256=code_hashes(),options=options,
                repairAudit=repair,geometryValidation=validation,additionsOnlyGate=gate,searchAttempts=selected['searchAttempts'],elapsedSeconds=selected['elapsedSeconds'],
                retainedBaseline=selected['retainedBaseline'],physics=core.base.strict.physics_summary(physical),qualityScreenedSuccess=validation['passed'] and physical['layerPrefixGravityPassed'],
                promptBindingStatus='original_geometry_preserved' if cells==original else 'original_only_not_revalidated',semanticVerified=False,staticVerified=None,fullPhysics=False,
                outputFileSha256={p.name:digest(p) for p in sorted(out.iterdir())})
    dump(out/'report.json',report)
    return verify(out,source_path)


def main():
    parser=argparse.ArgumentParser(description='Repair monochrome LEGO interfaces by retiling old bricks and local added cells.')
    sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run');run.add_argument('source',type=Path);run.add_argument('--out',required=True,type=Path);run.add_argument('--seconds',type=float,default=8.);run.add_argument('--physics-seconds',type=float,default=5.);run.add_argument('--baseline',type=Path)
    check=sub.add_parser('verify');check.add_argument('folder',type=Path)
    args=parser.parse_args()
    if args.command=='verify':report=verify(args.folder)
    else:report=run_one(args.source,args.out,args.seconds,args.physics_seconds,args.baseline)
    print(json.dumps({k:report[k] for k in ('modelId','status','geometryValidation','repairAudit','physics')},ensure_ascii=False,indent=2))
    return 0 if report['status']=='success' else 2


if __name__=='__main__':raise SystemExit(main())
