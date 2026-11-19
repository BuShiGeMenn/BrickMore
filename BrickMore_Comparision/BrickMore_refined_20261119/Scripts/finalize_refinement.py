"""Verify all 525 final selections, write the delivery index, and package them."""
from collections import Counter
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(r'D:\BrickMore')
OUT = ROOT/'BrickMore_Comparision/BrickMore_refined_20261119'
sys.path.insert(0,str(ROOT/'brickmore48_tools/pipeline'))
import refine_comparison as core


def main():
    manifest=core.read(OUT/'input_manifest.json')
    summary=core.read(OUT/'summary.json')
    assert summary['finished'] and summary['completed']==525
    baseline={r['prompt_id']:core.read(OUT/'records'/r['prompt_id']/'result.json') for r in manifest}
    selected=core.read(OUT/'regeneration_selections.json')
    expected_replacements={r['prompt_id'] for r in manifest if baseline[r['prompt_id']]['status']!='passed' or r.get('generation_complete') is False}
    assert set(selected)==expected_replacements
    assert core.read(OUT/'regeneration_progress.json')['finished']
    assert not core.read(OUT/'regeneration_progress.json')['exhausted']
    core.verify(OUT,manifest)
    for row in manifest:
        if row['batch']=='A':
            sequence=core.SOURCES[0]/row['sequence_path']
            target_sequence=OUT/'records'/row['prompt_id']/'raw_sequence.txt'
            assert core.sha(sequence)==row['sequence_sha256']
            shutil.copyfile(sequence,target_sequence)
    final_dir=OUT/'final_ldr'
    final_dir.mkdir(exist_ok=True)
    final=[]
    for row in manifest:
        pid=row['prompt_id']
        original=baseline[pid]
        if original['status']=='passed' and pid not in selected:
            source=OUT/original['ldr_path']
            cells,normalization=core.normalize(core.review.assembly.parse_ldr(
                (OUT/'records'/pid/'raw.ldr').read_text(encoding='utf-8')))
            origin='original_retained' if original['raw_audit']['passed'] else 'original_refined'
            metadata=dict(seed=None,baseline_status=original['status'],
                          source_folder=f'records/{pid}')
        else:
            replacement=selected[pid]
            assert replacement['caption']==row['caption']
            folder=OUT/replacement['folder']
            generation=core.read(folder/'generation.json')
            assert generation['prompt']==row['caption'] and generation['completed']
            assert generation['seed']==replacement['seed']
            candidate=core.read(folder/'candidate_result.json')
            assert candidate['status']=='passed'
            for name,expected in replacement['output_sha256'].items():
                assert core.sha(folder/name)==expected,(pid,name)
            bricks,parsed=core.review.parse((folder/'raw.txt').read_text(encoding='utf-8'))
            cells,normalization=core.normalize(bricks)
            source=OUT/replacement['ldr_path']
            origin='regenerated'
            metadata=dict(seed=replacement['seed'],baseline_status=original['status'],
                          source_folder=replacement['folder'])
        target=final_dir/f'{pid}.ldr'
        header = [
            f"0 BrickMore refined {pid}",
            f"0 !BRICKMORE PROMPT_ID {pid}",
            f"0 !BRICKMORE PROMPT {row['caption']}",
            f"0 !BRICKMORE REVISION {core.review.REVISION}",
            f"0 !BRICKMORE ORIGIN {origin}",
            f"0 !BRICKMORE SEED {metadata['seed'] if metadata['seed'] is not None else 'original'}",
        ]
        target.write_text('\n'.join(header)+'\n'+source.read_text(encoding='utf-8'),encoding='utf-8')
        final_bricks=core.review.assembly.parse_ldr(target.read_text(encoding='utf-8'))
        audit=core.independent_audit(final_bricks,cells)
        assert audit['passed'],pid
        final.append(dict(prompt_id=pid,batch=row['batch'],category=row['category'],
            level=row['level'],caption=row['caption'],origin=origin,
            raw_bricks=original['raw_bricks'],raw_stud_components=original['raw_audit']['stud_components'],
            refined_bricks=len(final_bricks),normalization=normalization,validation=audit,
            ldr_path=target.relative_to(OUT).as_posix(),ldr_sha256=core.sha(target),**metadata))
    assert len(final)==525==len(list(final_dir.glob('*.ldr')))
    assert len({r['prompt_id'] for r in final})==525
    baseline_counts=Counter(r['status'] for r in baseline.values())
    counts=Counter(r['origin'] for r in final)
    clipped=[r for r in final if r['normalization']['removed_voxels']]
    final_summary=dict(input_models=525,verified_final_models=525,by_origin=dict(counts),
        baseline_status_counts=dict(baseline_counts),
        additional_incomplete_replacements=core.read(OUT/'additional_regeneration_required.json')['prompt_ids'],
        baseline_by_batch=summary['by_batch'],
        final_by_batch={b:dict(Counter(r['origin'] for r in final if r['batch']==b)) for b in 'AB'},
        regenerated_prompt_ids=sorted(selected),
        clipped_final_targets=[dict(prompt_id=r['prompt_id'],origin=r['origin'],
            original_voxels=r['normalization']['original_voxels'],
            target_voxels=r['normalization']['target_voxels'],
            removed_voxels=r['normalization']['removed_voxels']) for r in clipped],
        all_final_checks=dict(exact_target_coverage=True,no_overlaps=True,
            allowed_dimensions=True,in_bounds=True,one_real_stud_component=True,
            ldr_readback=True,prompt_mapping=True),
        physical_stability_tested=False)
    core.dump(OUT/'final_results.json',final)
    core.dump(OUT/'final_summary.json',final_summary)
    core.dump(OUT/'final_verification.json',dict(passed=True,verified_final_models=525,
        checks=final_summary['all_final_checks'],source_weights_sha256=core.read(
            OUT/'regeneration_provenance.json')['model_weights_sha256']))
    core.dump(OUT/'initially_failed_models.json',[r for r in baseline.values() if r['status']!='passed'])

    sources=[
        'brickmore48_tools/pipeline/refine_comparison.py',
        'brickmore48_tools/pipeline/regenerate_comparison_failures.py',
        'brickmore48_tools/pipeline/regenerate_review5.py',
        'brickmore48_tools/analysis/raw_failure_autopsy.py',
        'Train/algorithms/voxel_assembly_b/assembly_pipeline.py',
        'Train/algorithms/voxel_assembly_b/toolkit_snapshot/voxel_assembly.py',
        'Train/algorithms/voxel_assembly_b/toolkit_snapshot/optimized_geometry.py',
        'Train/algorithms/voxel_assembly_b/toolkit_snapshot/brick_catalog.py',
        'Train/algorithms/voxel_assembly_b/toolkit_snapshot/interlocking.py',
        'Train/algorithms/voxel_assembly_b/toolkit_snapshot/voxel_io.py',
    ]
    for name in sources:
        target=OUT/'Scripts/project_sources'/name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,target)
    provenance=core.read(OUT/'provenance.json')
    provenance.update(
        regeneration=True,
        initial_refinement_runtime=dict(python_executable=sys.executable,python_version=sys.version.split()[0],scipy_version=__import__('scipy').__version__,numpy_version=__import__('numpy').__version__,workers=2,highs_threads_per_worker=1,mip_relative_gap=.08),
        regeneration_provenance='regeneration_provenance.json',
        final_source_code_sha256=core.sha(core.__file__),
        implementation_note=(
            'The archived single_stud_cover.py was unavailable. Existing project '
            'regenerate_review5.retile connected exact-cover cuts are reused. A '
            'single real stud-run flow implementation supplies a second formulation. '
            'Both require exact target coverage and one actual stud-contact component. '
            '12/60/180-second tiers and all individual solver calls are recorded. '
            'Failed original outputs retain their records and are replaced in the '
            'final selection by regenerated candidates using the same prompt.'),
        archived_code_sha256={name:core.sha(ROOT/name) for name in sources})
    core.dump(OUT/'provenance.json',provenance)

    label={'original_retained':'原始布局保留','original_refined':'原始输出重铺',
           'regenerated':'换种子重生成后通过'}
    lines=[
        '# BrickMore 525 个模型的 refine 结果',
        '',
        '**525/525 个最终 LDR 通过本轮几何复核。** A 组 260 个，B 组 265 个。',
        '',
        f"- 原始布局已满足检查，保留 {counts['original_retained']} 个。",
        f"- 对原始输出保形重铺后通过 {counts['original_refined']} 个。",
        f"- 原始重铺失败或生成未完成的输出，换种子重生成后通过 {counts['regenerated']} 个。",
        '',
        '## 使用文件',
        '',
        '- [final_ldr](final_ldr/) 为完整的 525 个最终模型，按原提示词 ID 命名。',
        '- [final_summary.json](final_summary.json) 为最终统计，[final_results.json](final_results.json) 为模型与提示词、种子和源版本的对应关系。',
        '- [final_verification.json](final_verification.json) 保存最终检查结果。',
        '- records/<提示词ID>/raw.ldr、raw.json、result.json 保存原始输出与第一轮修复记录。A 组另保存原规范序列 raw_sequence.txt。',
        '- records/<提示词ID>/regeneration/ 保存每个换种子候选的原始文本、生成参数、修复过程与结果。',
        '- [refined_ldr](refined_ldr/) 为第一轮对原始输出保形修复后通过的模型。',
        '- [initially_failed_models.json](initially_failed_models.json) 保留第一轮失败记录。',
        '',
        'LDR 使用标准单位，格距 20 LDU、层距 24 LDU。raw_sequence.txt 与 refined.txt 为标准 H×W (x,y,z)，h 沿 X、w 沿 Y、z 竖向。重生成 raw.txt 保留模型原文，解析沿用项目既有的 YX 尺寸约定。',
        '',
        '## 流程与验证',
        '',
        '沿用原流程的 20 种方向砖型、48³ 边界、重叠体素并集、精确覆盖重铺和单一真实凸点连通检查。MILP 按 12、60、180 秒升级，并保存每次求解状态。对第一轮失败项按原提示词换种子生成，采用 temperature=0.7、top_p=0.9、top_k=20、最多 8192 个新 token。完整种子阶梯和实际选择在重生成记录中。',
        '',
        '旧脚本引用的 single_stud_cover.py 已不可用。本轮复用了项目现有 regenerate_review5.retile 连通性割平面实现，并补充按原文档约束重建的单一凸点流实现。实际使用代码、版本和文件哈希保存在 Scripts 与 provenance.json。',
        '',
        '每个最终 LDR 都重新读取，验证合法砖型、边界、无重叠、与所选目标体素集合完全相同，以及上下层真实凸点接触图只有一个连通分量。原始输入、重生成候选和最终版本均保留。',
        '',
        '首个重生成通过项使用 Transformers BF16。为控制本机 6 GB 显存中的长序列缓存占用，后续使用同一权重转换的 BF16 GGUF，通过 llama.cpp b12359 CUDA 执行，K/V 缓存为 q8_0。每个候选的实际后端和参数分别保存，GGUF 与原权重哈希保存在 regeneration_provenance.json。',
        '',
        f'有 {len(clipped)} 个最终目标沿用原流程进行了 48³ 边界裁剪，具体如下。',
        '',
        '| 提示词 ID | 所选来源 | 裁剪前体素 | 裁剪后体素 | 移除体素 |',
        '|---|---|---:|---:|---:|',
    ]
    for r in clipped:
        n=r['normalization']
        lines.append(f"| {r['prompt_id']} | {label[r['origin']]} | {n['original_voxels']} | {n['target_voxels']} | {n['removed_voxels']} |")
    lines += [
        '',
        '本轮通过条件为单一凸点连通、无重叠和精确覆盖。实体稳定性、承重及实际装配路径尚未测试。原始生成是否完整的标记保存在源记录中。',
        '',
        '## 逐模型索引',
        '',
        '| 提示词 ID | 原始砖数 | 原始凸点分量 | 最终砖数 | 最终来源 | 种子 |',
        '|---|---:|---:|---:|---|---:|',
    ]
    for r in final:
        lines.append(f"| [{r['prompt_id']}]({r['ldr_path']}) | {r['raw_bricks']} | {r['raw_stud_components']} | {r['refined_bricks']} | {label[r['origin']]} | {r['seed'] if r['seed'] is not None else '—'} |")
    (OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    archive=OUT.parent/'BrickMore_525_refine_results_20261119.zip'
    files=sorted(p for p in OUT.rglob('*') if p.is_file() and p.suffix not in ('.tmp','.pyc') and '__pycache__' not in p.parts)
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in files:
            z.write(path,OUT.name+'/'+path.relative_to(OUT).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(files)
    archive.with_suffix('.zip.sha256').write_text(core.sha(archive)+'  '+archive.name+'\n',encoding='ascii')
    print(json.dumps(final_summary,ensure_ascii=False))
    print(archive,archive.stat().st_size)


if __name__=='__main__':
    main()

