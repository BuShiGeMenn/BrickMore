"""Render real generated brick geometry and export a portable GLB per candidate."""
import json
import hashlib
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def render(folder):
    source = folder / 'model.json'
    if not source.exists():
        source = folder / 'raw_geometry.json'
    if not source.exists():
        return
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    bricks = json.loads(source.read_text(encoding='utf-8'))['bricks']
    cells = {(x,y,b['z']) for b in bricks for x in range(b['x'],b['x']+b['h'])
             for y in range(b['y'],b['y']+b['w'])}
    low = [min(p[i] for p in cells) for i in range(3)]
    high = [max(p[i] for p in cells)+1 for i in range(3)]
    center = ((low[0]+high[0])/2,(low[1]+high[1])/2,low[2])
    vertices, faces = [], []
    def point(x,y,z):
        return (x-center[0],y-center[1],(z-center[2])*1.2)
    def box(x0,y0,z0,x1,y1,z1):
        i = len(vertices)
        vertices.extend(point(*p) for p in ((x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),
                       (x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)))
        faces.extend(tuple(i+j for j in f) for f in ((0,3,2,1),(4,5,6,7),(0,1,5,4),
                     (1,2,6,5),(2,3,7,6),(3,0,4,7)))
    for b in bricks:
        x,y,z,h,w = (b[k] for k in ('x','y','z','h','w'))
        box(x+.014,y+.014,z+.006,x+h-.014,y+w-.014,z+1-.006)
        for sx in range(x,x+h):
            for sy in range(y,y+w):
                if (sx,sy,z+1) in cells:
                    continue
                i = len(vertices)
                segments = 16
                for height in (z+.994,z+1+.16667):
                    for j in range(segments):
                        a = 2*math.pi*j/segments
                        vertices.append(point(sx+.5+.24*math.cos(a),sy+.5+.24*math.sin(a),height))
                faces.append(tuple(i+segments+j for j in range(segments)))
                for j in range(segments):
                    k = (j+1)%segments
                    faces.append((i+j,i+k,i+segments+k,i+segments+j))
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    mesh = bpy.data.meshes.new('Generated LEGO geometry')
    mesh.from_pydata(vertices,[],faces)
    mesh.update()
    obj = bpy.data.objects.new(folder.name,mesh)
    bpy.context.collection.objects.link(obj)
    material = bpy.data.materials.new('Display yellow - model has no color output')
    material.diffuse_color = (.92,.57,.035,1)
    material.use_nodes = True
    material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.92,.57,.035,1)
    material.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .32
    mesh.materials.append(material)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(folder/'model.glb'),export_format='GLB',use_selection=True,
                              export_yup=True)
    obj.select_set(False)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 720
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.world.color = (.25,.25,.25)
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.82,.86,.92,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .5
    scene.view_settings.view_transform = 'AgX'
    height = (high[2]-low[2])*1.2
    span = max(high[0]-low[0],high[1]-low[1],height)
    target = Vector((0,0,height*.46))
    bpy.ops.mesh.primitive_plane_add(size=span*200,location=(0,0,-.04))
    floor = bpy.context.object
    floor_mat = bpy.data.materials.new('Backdrop')
    floor_mat.diffuse_color = (.86,.89,.94,1)
    floor.data.materials.append(floor_mat)
    for location,power,size in (((span,-span,span*1.8),1200,span),((-span,-span*.5,span),650,span),
                               ((0,span,span*1.5),900,span*.7)):
        data = bpy.data.lights.new('Softbox','AREA')
        data.energy = power*max(1,(span/12)**2)
        data.shape = 'DISK'
        data.size = size
        light = bpy.data.objects.new('Softbox',data)
        scene.collection.objects.link(light)
        light.location = location
        light.rotation_euler = (target-light.location).to_track_quat('-Z','Y').to_euler()
    camera_data = bpy.data.cameras.new('Camera')
    camera = bpy.data.objects.new('Camera',camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = 'ORTHO'
    for name,direction in (('preview',(1.25,-1.6,1.05)),('side',(.05,-1.6,.65)),('reverse',(-1.25,1.6,1.05))):
        camera.location = target + Vector(direction)*span
        camera.rotation_euler = (target-camera.location).to_track_quat('-Z','Y').to_euler()
        inverse = camera.rotation_euler.to_matrix().transposed()
        projected = [inverse @ (Vector(point(x,y,z))-target) for x in (low[0],high[0])
                     for y in (low[1],high[1]) for z in (low[2],high[2]+.2)]
        width = max(p.x for p in projected)-min(p.x for p in projected)
        depth = max(p.y for p in projected)-min(p.y for p in projected)
        camera_data.ortho_scale = max(width,depth*720/640)*1.25
        scene.render.filepath = str(folder/(name+'.png'))
        bpy.ops.render.render(write_still=True)
    print('RENDERED',folder.name,flush=True)
    (folder/'render_metadata.json').write_text(json.dumps(dict(source_file=source.name,
        source_sha256=source_hash,display_color='uniform yellow, not model-generated color',
        renderer='Blender Cycles',brick_height_to_stud_spacing=1.2),indent=2),encoding='utf-8')


base = Path(sys.argv[sys.argv.index('--')+1])
committed={row['id'] for row in json.loads((base/'manifest.json').read_text(encoding='utf-8'))
           if row.get('visual_review',{}).get('decision')!='rejected'}
if '--only' in sys.argv:
    committed &= set(sys.argv[sys.argv.index('--only')+1].split(','))
for folder in sorted((base/'models').iterdir()):
    if folder.name not in committed:
        continue
    if '--force' in sys.argv or not (folder/'preview.png').exists() or not (folder/'render_metadata.json').exists():
        render(folder)
