# -*- coding: utf-8 -*-
"""在 Blender GUI 里打开两个 BrickMore 模型(与参考渲染相同的 ImportLDraw 管线)。
左:首批 basket L1-A 原版(即 raw.png 参考渲染图那只)
右:basket L1V2 重铺版
"""
import bpy
import os
import sys
from pathlib import Path

ROOT = Path(r"E:\brick_train\brick_infer_5070ti_20261001\BrickGPT")
sys.path.insert(0, str(ROOT))

import ImportLDraw
from ImportLDraw.loadldraw.loadldraw import Options, Configure, loadFromFile, FileSystem

plugin_path = Path(ImportLDraw.__file__).parent

# 与 render_bricks.py(参考渲染管线)一致的零件选项
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
Options.addEnvironmentTexture = True
Options.addWorldEnvironmentTexture = True
Options.addGroundPlane = True
Options.removeDefaultObjects = True
Options.setRenderSettings = False

Configure()

MODELS = [
    (r"E:\brick_train\brick_infer_5070ti_20261001\BrickGPT\bmore48_levels\basket\L1\raw.ldr", 0.0),
    (r"E:\brick_train\brick_infer_5070ti_20261001\BrickGPT\bmore48_levels2\basket\L1V2\stitched.ldr", 6.0),
]

before = set(bpy.data.objects)
for path, xoff in MODELS:
    loadFromFile(None, FileSystem.locate(path))
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.parent is None:
            o.location.x += xoff
    before = set(bpy.data.objects)

for area in bpy.context.screen.areas:
    if area.type == "VIEW_3D":
        space = area.spaces.active
        space.shading.type = "MATERIAL"
        region = next(r for r in area.regions if r.type == "WINDOW")
        with bpy.context.temp_override(area=area, region=region):
            bpy.ops.object.select_all(action="SELECT")
            bpy.ops.view3d.view_selected()
