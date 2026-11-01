# -*- coding: utf-8 -*-
"""批量把 BrickMore 模型的 LDR 导出为 GLB(Blender 真零件几何,Draco 压缩)。
用法: blender --background --factory-startup --python blender_glb_batch.py -- <job文件> <日志文件>
job 文件每行: <ldr路径>|<glb路径>
"""
import bpy
import os
import sys
import time
from pathlib import Path

argv = sys.argv[sys.argv.index("--") + 1:]
job_file, log_file = argv[0], argv[1]

ROOT = Path(r"E:\brick_train\brick_infer_5070ti_20261001\BrickGPT")
sys.path.insert(0, str(ROOT))
import ImportLDraw
from ImportLDraw.loadldraw.loadldraw import Options, Configure, FileSystem, loadFromFile

plugin_path = Path(ImportLDraw.__file__).parent
Options.ldrawDirectory = str(Path.home() / "ldraw")
Options.useLogoStuds = True
Options.useUnofficialParts = True
Options.gaps = True
Options.studLogoDirectory = os.path.join(plugin_path, "studs")
Options.LSynthDirectory = os.path.join(plugin_path, "lsynth")
Options.verbose = 0
Options.overwriteExistingMaterials = True
Options.overwriteExistingMeshes = True
Options.scale = 0.01
Options.createInstances = True
Options.removeDoubles = True
Options.positionObjectOnGroundAtOrigin = True
Options.flattenHierarchy = False
Options.edgeSplit = True
Options.addBevelModifier = True
Options.bevelWidth = 0.5
Options.scriptDirectory = os.path.join(plugin_path, "loadldraw")
Options.addGroundPlane = False
Options.removeDefaultObjects = True
Options.setRenderSettings = False
Configure()

jobs = []
for line in open(job_file, encoding="utf-8"):
    line = line.strip()
    if line:
        jobs.append(line.split("|"))

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)

def log(msg):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

log(f"start: {len(jobs)} jobs")
ok = fail = 0
t0 = time.time()
for i, (ldr, glb) in enumerate(jobs, 1):
    try:
        clear_scene()
        loadFromFile(None, FileSystem.locate(ldr))
        os.makedirs(os.path.dirname(glb), exist_ok=True)
        bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB",
                                  export_draco_mesh_compression_enable=True,
                                  export_draco_mesh_compression_level=6,
                                  export_apply=True)
        ok += 1
    except Exception as e:
        fail += 1
        log(f"FAIL {ldr}: {e}")
    if i % 20 == 0 or i == len(jobs):
        done_ratio = i / len(jobs)
        eta = (time.time() - t0) / done_ratio * (1 - done_ratio)
        log(f"progress {i}/{len(jobs)} ok={ok} fail={fail} eta={eta/60:.0f}min")
log(f"done ok={ok} fail={fail} elapsed={(time.time()-t0)/60:.1f}min")
