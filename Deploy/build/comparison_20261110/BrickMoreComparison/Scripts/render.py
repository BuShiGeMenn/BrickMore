"""Deterministic eight-view CPU triangle rendering of shared actual part meshes."""
import argparse,json,math,time
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image
from numba import njit
from common import ROOT,Journal,digest,dump,emit,rows,sha

@njit(cache=True)
def raster(projected,faces,shades,size):
    pixels=np.full((size,size,3),246,np.uint8);depth=np.full((size,size),-1e30,np.float32)
    for index in range(len(faces)):
        i,j,k=faces[index];a,b,c=projected[i],projected[j],projected[k]
        denom=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(denom)<1e-10:continue
        x0=max(0,int(math.floor(min(a[0],b[0],c[0]))));x1=min(size-1,int(math.ceil(max(a[0],b[0],c[0]))))
        y0=max(0,int(math.floor(min(a[1],b[1],c[1]))));y1=min(size-1,int(math.ceil(max(a[1],b[1],c[1]))))
        for y in range(y0,y1+1):
            for x in range(x0,x1+1):
                u=((b[1]-c[1])*(x+.5-c[0])+(c[0]-b[0])*(y+.5-c[1]))/denom
                v=((c[1]-a[1])*(x+.5-c[0])+(a[0]-c[0])*(y+.5-c[1]))/denom
                w=1-u-v
                if u>=-1e-6 and v>=-1e-6 and w>=-1e-6:
                    z=u*a[2]+v*b[2]+w*c[2]
                    if z>depth[y,x]:
                        depth[y,x]=z
                        pixels[y,x,0]=int(242*shades[index]);pixels[y,x,1]=int(205*shades[index]);pixels[y,x,2]=int(55*shades[index])
    return pixels

@lru_cache(maxsize=None)
def mesh(stem):
    with np.load(ROOT/'Assets/render_meshes'/f'{stem}.npz') as z:return z['vertices'],z['faces']

def combined(assembly):
    vs=[];fs=[];offset=0
    for part in assembly['instances']:
        v,f=mesh(part['part_stem']);m=np.asarray(part['matrix_ldu']);world=v@m[:3,:3].T+m[:3,3];world[:,1]*=-1
        vs.append(world);fs.append(f+offset);offset+=len(v)
    vertices=np.concatenate(vs).astype(np.float32);faces=np.concatenate(fs).astype(np.int32)
    center=(vertices.min(0)+vertices.max(0))*.5;radius=float(np.linalg.norm(vertices.max(0)-vertices.min(0))*.5)
    return vertices-center,faces,max(radius,1)

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--size',type=int,default=512);a=p.parse_args()
    items=rows(a.input);a.out.mkdir(parents=True,exist_ok=True)
    config=dict(input_sha256=sha(a.input),source_sha256=sha(__file__),catalog_sha256=sha(ROOT/'Assets/catalog.json'),
       size=a.size,views=8,elevation_deg=25,azimuth_deg=list(range(0,360,45)),projection='orthographic bounding-sphere fit',
       material='uniform yellow for all systems',geometry='official original inset part surfaces, adapted renderer; no color-accuracy claim',background=[246,246,246])
    journal=Journal(a.out/'renders.jsonl',config);light=np.array([.4,.8,.5]);light/=np.linalg.norm(light)
    for index,row in enumerate(items):
        ih=digest({'assembly':row['assembly_sha256'],'config':config});cached=journal.cached(row['sample_id'],ih)
        if cached:
            if any(sha(a.out/path)!=expected for path,expected in zip(cached['view_paths'],cached['view_sha256'])):raise ValueError('Changed/missing cached image')
            emit('render',(index+1)*8,len(items)*8,row['sample_id']);continue
        assembly=json.loads((ROOT/row['assembly_path']).read_text(encoding='utf-8'));vertices,faces,radius=combined(assembly)
        normals=np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],vertices[faces[:,2]]-vertices[faces[:,0]])
        normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-12)
        shades=(.5+.47*np.abs(normals@light)).astype(np.float32)
        folder=a.out/'views'/row['sample_id'];folder.mkdir(parents=True,exist_ok=True);paths=[];hashes=[]
        for view in range(8):
            az=math.radians(view*45);el=math.radians(25)
            direction=np.array([math.sin(az)*math.cos(el),math.sin(el),math.cos(az)*math.cos(el)])
            right=np.cross([0,1,0],direction);right/=np.linalg.norm(right);up=np.cross(direction,right)
            projected=np.column_stack((vertices@right*a.size*.435/radius+a.size/2,
                -vertices@up*a.size*.435/radius+a.size/2,vertices@direction)).astype(np.float32)
            image=raster(projected,faces,shades,a.size);target=folder/f'{view:02}.png';temp=target.with_suffix('.png.tmp')
            Image.fromarray(image).save(temp,format='PNG');temp.replace(target)
            paths.append(target.relative_to(a.out).as_posix());hashes.append(sha(target))
            emit('render',index*8+view+1,len(items)*8,row['sample_id']+f' view {view+1}/8')
        journal.add({**row,'view_paths':paths,'view_sha256':hashes,'render_protocol':config},ih)
    dump(a.out/'render_protocol.json',config)

if __name__=='__main__':main()
