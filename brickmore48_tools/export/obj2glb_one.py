import bpy, sys
argv = sys.argv[sys.argv.index("--") + 1:]
src, dst = argv
bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete()
bpy.ops.wm.obj_import(filepath=src)
bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB",
                          export_draco_mesh_compression_enable=True,
                          export_draco_mesh_compression_level=6, export_apply=True)
print("OK", dst)
