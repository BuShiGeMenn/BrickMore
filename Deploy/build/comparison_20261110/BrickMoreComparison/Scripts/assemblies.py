"""LDraw and numbered GLB structure adapters, preserving export/file order."""
from __future__ import annotations
import json,re,struct
from pathlib import Path
import numpy as np

METRES_PER_LDU=.0004
ROTATION=np.array([[1.,0,0],[0,0,1],[0,-1,0]])
PART_NAME=re.compile(r'^(\d+)_(\d+\.dat)(?:\.\d+)?$',re.I)
PARTS={(1,1):'3005',(1,2):'3004',(1,3):'3622',(1,4):'3010',(1,6):'3009',(1,8):'3008',
       (2,2):'3003',(2,3):'3002',(2,4):'3001',(2,6):'2456',(2,8):'3007'}

def node_matrix(node):
    if 'matrix' in node:return np.asarray(node['matrix'],dtype=float).reshape(4,4,order='F')
    quaternion=np.asarray(node.get('rotation',[0,0,0,1]),dtype=float)
    quaternion/=np.linalg.norm(quaternion)
    x,y,z,w=quaternion;m=np.eye(4)
    m[:3,:3]=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
        [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
        [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])@np.diag(node.get('scale',[1,1,1]))
    m[:3,3]=node.get('translation',[0,0,0]);return m

def world_nodes(data):
    visited=set()
    def visit(i,parent):
        if i in visited:raise ValueError('Repeated/cyclic GLB node')
        visited.add(i);node=data['nodes'][i];world=parent@node_matrix(node)
        yield i,node,world
        for child in node.get('children',[]):yield from visit(child,world)
    roots=data['scenes'][data.get('scene',0)]['nodes']
    for i in roots:yield from visit(i,np.eye(4))

def recover_glb(path):
    content=Path(path).read_bytes();magic,version,length=struct.unpack('<4sII',content[:12])
    if magic!=b'glTF' or version!=2 or length!=len(content):raise ValueError('Invalid GLB header')
    size,kind=struct.unpack('<II',content[12:20]);assert kind==0x4E4F534A
    data=json.loads(content[20:20+size]);basis=np.eye(4);basis[:3,:3]=METRES_PER_LDU*ROTATION;inverse=np.linalg.inv(basis)
    instances=[];bounds={}
    for index,node,world in world_nodes(data):
        if 'mesh' not in node:continue
        match=PART_NAME.fullmatch(node.get('name',''))
        if not match:raise ValueError(f'Unnumbered part mesh: {node.get("name")}')
        order=int(match[1]);stem=match[2].lower()[:-4];matrix=inverse@world@basis;r=matrix[:3,:3]
        if not np.allclose(r.T@r,np.eye(3),atol=1e-6) or abs(np.linalg.det(r)-1)>1e-6:raise ValueError('Scaled/reflected/sheared GLB part')
        key=(node['mesh'],stem)
        if key not in bounds:
            points=[]
            for primitive in data['meshes'][node['mesh']]['primitives']:
                accessor=data['accessors'][primitive['attributes']['POSITION']]
                lo,hi=accessor['min'],accessor['max']
                points.extend(np.array([x,y,z])@ROTATION/METRES_PER_LDU for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2]))
            a=np.array(points);bounds[key]=dict(mesh_index=node['mesh'],part_stem=stem,local_lo_ldu=a.min(0).tolist(),local_hi_ldu=a.max(0).tolist())
        instances.append(dict(export_index=order,node_index=index,part_stem=stem,matrix_ldu=matrix.tolist()))
    instances.sort(key=lambda p:p['export_index'])
    if not instances or [p['export_index'] for p in instances]!=list(range(1,len(instances)+1)):raise ValueError('Noncontiguous export part numbers')
    return dict(instances=instances,mesh_bounds=list(bounds.values()),order_provenance='numbered GLB export nodes; original generation order unverified',up_axis='canonical +Z, converted from glTF +Y',source_up=[0,0,1])

def recover_procedural_glb(path):
    """Strict adapter for the supplied unindexed cuboid/stud triangle streams.

    Every body must be a complete 12-triangle rectangular box of a legal brick
    size. Every other triangle must lie in that body's top-stud envelope. This
    does not infer parts from silhouettes or segment arbitrary merged meshes.
    """
    content=Path(path).read_bytes();size=struct.unpack('<I',content[12:16])[0]
    data=json.loads(content[20:20+size]);binary=content[28+size:]
    if len(data['nodes'])!=1 or len(data['meshes'])!=1 or data['nodes'][0]!={'mesh':0}:raise ValueError('Not the known procedural GLB layout')
    primitives=data['meshes'][0]['primitives']
    if len(primitives)!=1 or 'indices' in primitives[0] or primitives[0].get('mode',4)!=4:raise ValueError('Not an unindexed triangle stream')
    ac=data['accessors'][primitives[0]['attributes']['POSITION']];view=data['bufferViews'][ac['bufferView']]
    if ac['componentType']!=5126 or ac['type']!='VEC3':raise ValueError('Unexpected vertex encoding')
    vertices=np.ndarray((ac['count'],3),dtype='<f4',buffer=binary,offset=view.get('byteOffset',0)+ac.get('byteOffset',0),strides=(view.get('byteStride',12),4)).astype(float)
    if len(vertices)%3:raise ValueError('Incomplete triangles')
    triangles=vertices.reshape(-1,3,3);ys=triangles[:,:,1].max(1)-triangles[:,:,1].min(1)
    candidates=np.flatnonzero(ys>.5)*3;bodies=[];end=0;vertical_scale=None
    for start in candidates:
        if start<end or start+36>len(vertices):continue
        block=vertices[start:start+36];lo=block.min(0);hi=block.max(0);span=hi-lo
        scale=span[1]/.976
        if min(abs(scale-1),abs(scale-1.2))>2e-4:continue
        h,w=round(span[0]+.024),round(span[2]+.024)
        if tuple(sorted((h,w))) not in PARTS or max(abs(span[0]-(h-.024)),abs(span[2]-(w-.024)))>2e-4:continue
        unique=np.unique(np.round(block,4),axis=0)
        if len(unique)!=8 or any(len(np.unique(unique[:,axis]))!=2 for axis in range(3)):continue
        planes=collections_counter_planes(block,lo,hi)
        if planes!=[2]*6:continue
        if vertical_scale is None:vertical_scale=scale
        if abs(scale-vertical_scale)>2e-4:raise ValueError('Mixed brick-height scales')
        z=(lo[1]-.012*scale)/scale
        if abs(z-round(z))>3e-4:raise ValueError('Off-grid procedural layer')
        bodies.append((int(start),dict(h=h,w=w,layer=round(z),lo=lo,hi=hi)));end=start+36
    if not bodies or bodies[0][0]!=0:raise ValueError('No complete procedural brick bodies')
    instances=[]
    for index,(start,b) in enumerate(bodies):
        stop=bodies[index+1][0] if index+1<len(bodies) else len(vertices);tail=vertices[start+36:stop]
        lo,hi=b['lo'],b['hi']
        if len(tail) and (np.any(tail[:,1]<hi[1]-3e-4) or np.any(tail[:,1]>hi[1]+.25*vertical_scale) or
             np.any(tail[:,0]<lo[0]-3e-4) or np.any(tail[:,0]>hi[0]+3e-4) or np.any(tail[:,2]<lo[2]-3e-4) or np.any(tail[:,2]>hi[2]+3e-4)):
            raise ValueError('Unaccounted geometry outside a brick/stud envelope')
        h,w=b['h'],b['w'];matrix=np.eye(4)
        matrix[:3,:3]=np.array([[0,0,1],[0,1,0],[-1,0,0]]) if h<=w else np.diag([-1,1,-1])
        matrix[:3,3]=[(lo[0]+hi[0])*10,-24*(b['layer']+1),(lo[2]+hi[2])*10]
        instances.append(dict(export_index=index+1,part_stem=PARTS[tuple(sorted((h,w)))],matrix_ldu=matrix.tolist()))
    return dict(instances=instances,mesh_bounds=[],source_up=[0,-1,0],up_axis='LDraw -Y',
        order_provenance='procedural triangle-stream body order; original generation order unverified',
        reconstruction=dict(method='strict complete cuboid bodies plus exhaustive top-stud envelope validation',
             body_count=len(bodies),all_vertices_accounted_for=True,source_vertical_scale=vertical_scale,
             conversion='horizontal grid spacing ->20 LDU, vertical layer ->24 LDU; source display-height convention normalized'))

def collections_counter_planes(block,lo,hi):
    counts=[0]*6
    for tri in block.reshape(12,3,3):
        axes=[(axis,side) for axis in range(3) for side,value in enumerate((lo[axis],hi[axis])) if np.max(np.abs(tri[:,axis]-value))<2e-4]
        if len(axes)!=1 or np.linalg.norm(np.cross(tri[1]-tri[0],tri[2]-tri[0]))<1e-7:return []
        axis,side=axes[0];counts[axis*2+side]+=1
    return counts

def parse_ldr(text,catalog,aliases):
    instances=[]
    for number,line in enumerate(text.splitlines(),1):
        f=line.split()
        if not f or f[0] in ('0','2','3','4','5'):continue
        if len(f)!=15 or f[0]!='1':raise ValueError(f'Unsupported LDraw record {number}')
        values=np.asarray(list(map(float,f[2:14])));assert np.isfinite(values).all()
        m=np.eye(4);m[:3,3]=values[:3];m[:3,:3]=values[3:].reshape(3,3)
        stem=Path(f[-1].replace('\\','/')).stem.lower();original=stem
        if stem not in catalog.stem_to_id:
            if stem not in aliases:raise ValueError(f'Part not in pinned catalog: {stem}')
            stem,xf=aliases[stem];m=m@xf
        if abs(abs(np.linalg.det(m[:3,:3]))-1)>1e-4:raise ValueError(f'Nonrigid LDraw transform {number}')
        instances.append(dict(export_index=len(instances)+1,part_stem=stem,matrix_ldu=m.tolist(),original_part=original,color=f[1]))
    if not instances:raise ValueError('Empty LDraw')
    return dict(instances=instances,order_provenance='LDraw file record order; original generation order unverified',up_axis='LDraw -Y',source_up=[0,-1,0])

def orient_ldraw(assembly):
    # A rigid global basis change, preserving every part and relative pose.
    if assembly.get('source_up')==[0,0,1]:
        rotation=np.eye(4);rotation[:3,:3]=ROTATION.T
        for part in assembly['instances']:part['matrix_ldu']=(rotation@np.asarray(part['matrix_ldu'])).tolist()
    assembly['up_axis']='LDraw -Y';return assembly
