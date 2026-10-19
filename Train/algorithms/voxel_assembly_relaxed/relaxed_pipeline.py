"""Portable modular outputs; geometry passes and uncalibrated physics stay separate."""
import json
from pathlib import Path
import shutil
import time

import relaxed_core as r
import modular_gravity as physics
q=r.q;strict=r.strict
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent
VERSION='quality_relaxed_modular_grounded_delivery_v1'
_HASHES=None


def hashes():
    if _HASHES is not None:return _HASHES
    return {**strict.hashes(),**{p.relative_to(ROOT).as_posix():q.a.file_sha(p) for p in sorted(HERE.glob('*.py'))}}


def target_value(source,cells,repair):
    value=strict.old.target_value(source,cells,repair)
    if value['derivedGeometry']:value['modelId']=value['modelId'].replace('_q2_','_q5_')
    return value


def graph_readback(bricks,target):
    """Second independent whole-file occupancy + explicit adjacency BFS auditor."""
    occupied={};issues=[];adj=[set() for _ in bricks];ground=set()
    dimensions=set(q.a.dimensions_for_library('extended'))
    for i,b in enumerate(bricks):
        if any(type(b.get(k)) is not int for k in ('h','w','x','y','z','color')):
            issues.append('invalid_fields');continue
        if (b['h'],b['w']) not in dimensions or not 0<=b['color']<=0xffffff or not (0<=b['x']<=48-b['h'] and 0<=b['y']<=48-b['w'] and 0<=b['z']<48):
            issues.append('invalid_bounds_catalog_or_color');continue
        if b['z']==0:ground.add(i)
        for p in q.a.Placement(**{k:b[k] for k in ('h','w','x','y','z')}).cells():
            if p in occupied:issues.append('collision')
            occupied[p]=(i,b['color'])
    for (x,y,z),(i,c) in occupied.items():
        upper=occupied.get((x,y,z+1))
        if upper and upper[0]!=i:adj[i].add(upper[0]);adj[upper[0]].add(i)
    remaining=set(range(len(bricks)));groups=[]
    while remaining:
        i=min(remaining);remaining.remove(i);todo=[i];group={i}
        while todo:
            for other in adj[todo.pop()]:
                if other in remaining:remaining.remove(other);todo.append(other);group.add(other)
        groups.append(group)
    grounded=sum(bool(group&ground) for group in groups)
    if not groups or grounded!=len(groups):issues.append('ungrounded_component')
    if any(b['z'] and not adj[i] for i,b in enumerate(bricks)):issues.append('no_vertical_stud')
    actual={p:c for p,(_,c) in occupied.items()}
    if actual!=target:issues.append('shape_or_color_mismatch')
    return dict(passed=not issues,studComponentCount=len(groups),groundedComponentCount=grounded)


def verify(folder,source_path=None):
    folder=Path(folder);report=json.loads((folder/'report.json').read_bytes())
    if report['algorithmVersion']!=VERSION or report['geometryTier']!='relaxed_modular_grounded_not_physical_certification':raise ValueError('wrong modular tier')
    for name,digest in report['outputFileSha256'].items():
        if Path(name).name!=name or q.a.file_sha(folder/name)!=digest:raise ValueError('modular artifact SHA differs')
    if source_path is not None and q.a.file_sha(source_path)!=report['sourceFileSha256']:raise ValueError('original changed')
    if q.a.file_sha(folder/'source.model.json')!=report['sourceFileSha256']:raise ValueError('source copy changed')
    source=json.loads((folder/'source.model.json').read_bytes());target=json.loads((folder/'target.model.json').read_bytes())
    original,_=q.a.dataset_model(source);model,_=q.a.dataset_model(target)
    repair=strict.m.repair_audit(original.cells,model.cells,.02)
    if not repair['passed'] or repair!=report['repairAudit'] or target!=target_value(source,model.cells,repair):raise ValueError('modular repair/derived identity differs')
    value=json.loads((folder/'assembly.json').read_bytes());raw=value['bricks']
    if value['policy']!=r.POLICY or value['modelId']!=target['modelId'] or report['targetModelId']!=target['modelId'] or report['modelId']!=source['modelId']:raise ValueError('modular identity/policy differs')
    validation=r.audit(raw,model.cells);second=graph_readback(raw,model.cells)
    if any(validation[k]!=second[k] for k in second):raise ValueError('independent modular auditors disagree')
    suffix='' if validation['passed'] else '.draft'
    txt=[q.a.Placement.parse(line) for line in (folder/f'model{suffix}.txt').read_text().splitlines() if line.strip()]
    ldr=q.a.parse_ldr((folder/f'model{suffix}.ldr').read_text())
    if [tuple(getattr(b,k) for k in ('h','w','x','y','z')) for b in txt]!=[tuple(b[k] for k in ('h','w','x','y','z')) for b in raw] or ldr!=raw:raise ValueError('modular actual TXT/LDR readback differs')
    if validation!=report['geometryValidation'] or validation!=json.loads((folder/'validation.json').read_bytes()):raise ValueError('modular validation differs')
    if report['status']!=('success' if validation['passed'] else 'draft') or value['status']!=report['status']:raise ValueError('false modular success')
    gate=json.loads((folder/'additions_only_evidence.json').read_bytes());gate_cells=q.a.dataset_model(gate['target'])[0].cells
    if gate!=report['additionsOnlyGate'] or gate['sourceFileSha256']!=report['sourceFileSha256'] or not q.repair_audit(original.cells,gate_cells,.02)['passed']:raise ValueError('modular additions evidence differs')
    gate_pass=(q.independent_audit if gate['auditor']=='strict_q4' else r.audit)(gate['bricks'],gate_cells)['passed']
    if gate_pass!=gate['geometryPassed'] or repair['removedVoxelCount'] and gate_pass:raise ValueError('removal before actual additions failure')
    if {tuple(p) for p in report['addedInternalXYZ']}!=set(model.cells)-set(original.cells) or {tuple(p) for p in report['removedInternalXYZ']}!=set(original.cells)-set(model.cells):raise ValueError('modular repair history differs')
    physical=json.loads((folder/'physics.json').read_bytes())
    if report['physics']!=strict.physics_summary(physical):raise ValueError('modular physical summary differs')
    if validation['passed'] and report['sourceCodeSha256'].get('algorithms/voxel_assembly_relaxed/modular_gravity.py')!=physical.get('geometryGuardAdapterSha256'):
        raise ValueError('physical adapter not bound to reported source generation')
    if validation['passed']:physics.verify(raw,model.cells,physical)
    elif physical['status']!='not_evaluated_geometry_failed' or physical['gravityEquilibriumPassed']:raise ValueError('invalid draft physics')
    if report['qualityScreenedSuccess']!=(validation['passed'] and physical['layerPrefixGravityPassed']):raise ValueError('false modular physical pass')
    if any(v.get('fullPhysics') is not False or v.get('staticVerified') is not None for v in (report,value,physical)):raise ValueError('unsupported physical certification')
    if report.get('semanticVerified') is not False:raise ValueError('unsupported semantic certification')
    return report


def worker(task):
    job,dataset,out,options=task;folder=Path(out)/'models'/job['category']/job['modelId']
    source_path=Path(dataset)/job['modelPath']/'model.json'
    if folder.exists():return verify(folder,source_path)
    source=json.loads(source_path.read_bytes());original,_=q.a.dataset_model(source);started=time.monotonic()
    if source['modelId']!=job['modelId'] or q.a.exact_hash({(x,z,y):c for (x,y,z),c in original.cells.items()})!=job['exactOccupancyHash']:
        raise ValueError('modular source manifest identity/occupancy binding differs')
    prior_path=Path(job['priorStrictFolder']);prior=None
    if (prior_path/'report.json').exists():
        if json.loads((prior_path/'report.json').read_bytes())['status']=='success':prior=strict.verify(prior_path,source_path)
    if prior is not None:
        raw=json.loads((prior_path/'assembly.json').read_bytes())['bricks']
        cells=q.a.dataset_model(json.loads((prior_path/'target.model.json').read_bytes()))[0].cells
        gate=json.loads((prior_path/'additions_only_evidence.json').read_bytes());gate={**gate,'auditor':'strict_q4'}
        attempts=[dict(stage='retained_actual_strict_success',priorReportSha256=q.a.file_sha(prior_path/'report.json'))]
        origin='retained_strict_q4_success'
    elif job['baselineStatus']=='success':
        if q.a.file_sha(Path(job['baselinePath'])/'report.json')!=job['baselineReportSha256']:raise ValueError('original baseline report changed')
        retained=strict.old.retain_baseline(Path(job['baselinePath']),source,source_path)
        raw=retained['bricks'];cells=retained['targetCells']
        gate=dict(auditor='strict_q4',bricks=raw,target=target_value(source,cells,q.repair_audit(original.cells,cells,.02)),geometryPassed=True,sourceFileSha256=q.a.file_sha(source_path))
        attempts=[dict(stage='retained_original_published_success')];origin='retained_original_published_success'
    else:
        selected=r.optimize(original.cells,options['seconds']);raw=selected['bricks'];cells=selected['targetCells'];attempts=selected['searchAttempts']
        evidence=selected.get('additionsOnlyEvidence',dict(bricks=raw,targetCells=cells,passed=r.audit(raw,cells)['passed']))
        gate=dict(auditor='relaxed_modular',bricks=evidence['bricks'],target=target_value(source,evidence['targetCells'],q.repair_audit(original.cells,evidence['targetCells'],.02)),
                  geometryPassed=evidence['passed'],sourceFileSha256=q.a.file_sha(source_path),boundedFailureNotImpossibility=True)
        origin='new_relaxed_ground_flow'
    repair=strict.m.repair_audit(original.cells,cells,.02);validation=r.audit(raw,cells)
    if not repair['passed']:raise ValueError('modular worker edit quality exceeded')
    target=target_value(source,cells,repair);status='success' if validation['passed'] else 'draft'
    physical=physics.screen(raw,cells,options['physicsSeconds']) if validation['passed'] else dict(status='not_evaluated_geometry_failed',gravityEquilibriumPassed=False,layerPrefixGravityPassed=False,assumptions=physics.g.ASSUMPTIONS,fullPhysics=False,staticVerified=None)
    folder.mkdir(parents=True);shutil.copyfile(source_path,folder/'source.model.json')
    q.a.dump(folder/'target.model.json',target)
    q.a.dump(folder/'assembly.json',dict(algorithmVersion=VERSION,modelId=target['modelId'],sourceModelId=source['modelId'],status=status,policy=r.POLICY,bricks=raw,fullPhysics=False,staticVerified=None))
    suffix='' if status=='success' else '.draft'
    (folder/f'model{suffix}.txt').write_text(''.join(q.a.Placement(**{k:b[k] for k in ('h','w','x','y','z')}).to_txt() for b in raw),encoding='utf8')
    (folder/f'model{suffix}.ldr').write_text(q.a.to_ldr(dict(status=status,bricks=[{k:b[k] for k in ('h','w','x','y','z')} for b in raw]),cells),encoding='utf8')
    q.a.dump(folder/'physics.json',physical);q.a.dump(folder/'validation.json',validation);q.a.dump(folder/'additions_only_evidence.json',gate)
    report=dict(algorithmVersion=VERSION,geometryTier='relaxed_modular_grounded_not_physical_certification',modelId=source['modelId'],targetModelId=target['modelId'],category=job['category'],status=status,
                sourceFileSha256=q.a.file_sha(source_path),sourceCodeSha256=hashes(),options=options,repairAudit=repair,geometryValidation=validation,
                additionsOnlyGate=gate,addedInternalXYZ=[list(p) for p in sorted(set(cells)-set(original.cells))],removedInternalXYZ=[list(p) for p in sorted(set(original.cells)-set(cells))],
                searchAttempts=attempts,origin=origin,physics=strict.physics_summary(physical),qualityScreenedSuccess=validation['passed'] and physical['layerPrefixGravityPassed'],
                promptBindingStatus='original_geometry_preserved' if cells==original.cells else 'original_only_not_revalidated',fullPhysics=False,staticVerified=None,semanticVerified=False,
                elapsedSeconds=time.monotonic()-started,outputFileSha256={p.name:q.a.file_sha(p) for p in sorted(folder.iterdir())})
    q.a.dump(folder/'report.json',report);return verify(folder,source_path)
