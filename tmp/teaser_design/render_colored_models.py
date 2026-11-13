"""Render the project's actual part meshes with diagnostic per-brick colors."""
from functools import lru_cache
from pathlib import Path
import json
import math

import numpy as np
from numba import njit
from PIL import Image

ROOT = Path('D:/BrickMore')
PACKAGE = ROOT / 'Deploy/build/comparison_20261110/BrickMoreComparison'
OUT = ROOT / 'tmp/teaser_design/renders'
OUT.mkdir(parents=True, exist_ok=True)
PALETTE = np.array([
    [80, 153, 201], [237, 169, 71], [224, 105, 100], [97, 179, 151],
    [161, 139, 200], [224, 144, 184], [117, 192, 211], [193, 191, 113],
], dtype=float)


@njit(cache=True)
def raster(projected, faces, colors, size):
    pixels = np.full((size, size, 3), 255, np.uint8)
    depth = np.full((size, size), -1e30, np.float32)
    for index in range(len(faces)):
        i, j, k = faces[index]
        a, b, c = projected[i], projected[j], projected[k]
        denom = (b[1]-c[1])*(a[0]-c[0]) + (c[0]-b[0])*(a[1]-c[1])
        if abs(denom) < 1e-10:
            continue
        x0 = max(0, int(math.floor(min(a[0], b[0], c[0]))))
        x1 = min(size-1, int(math.ceil(max(a[0], b[0], c[0]))))
        y0 = max(0, int(math.floor(min(a[1], b[1], c[1]))))
        y1 = min(size-1, int(math.ceil(max(a[1], b[1], c[1]))))
        for y in range(y0, y1+1):
            for x in range(x0, x1+1):
                u = ((b[1]-c[1])*(x+.5-c[0]) + (c[0]-b[0])*(y+.5-c[1])) / denom
                v = ((c[1]-a[1])*(x+.5-c[0]) + (a[0]-c[0])*(y+.5-c[1])) / denom
                w = 1-u-v
                if u >= -1e-6 and v >= -1e-6 and w >= -1e-6:
                    z = u*a[2]+v*b[2]+w*c[2]
                    if z > depth[y, x]:
                        depth[y, x] = z
                        for channel in range(3):
                            pixels[y, x, channel] = int(colors[index, channel])
    return pixels


@lru_cache(maxsize=None)
def mesh(stem):
    with np.load(PACKAGE / 'Assets/render_meshes' / f'{stem}.npz') as data:
        return data['vertices'], data['faces']


def ldraw(path):
    instances = []
    for line in path.read_text(encoding='utf-8').splitlines():
        fields = line.split()
        if not fields or fields[0] != '1':
            continue
        values = np.array(list(map(float, fields[2:14])))
        matrix = np.eye(4)
        matrix[:3, 3] = values[:3]
        matrix[:3, :3] = values[3:].reshape(3, 3)
        instances.append({'part_stem': Path(fields[-1]).stem,
                          'matrix_ldu': matrix.tolist()})
    return {'instances': instances}


def colored_geometry(assembly):
    parts, boxes = [], []
    for part in assembly['instances']:
        vertices, faces = mesh(part['part_stem'])
        matrix = np.asarray(part['matrix_ldu'])
        world = vertices @ matrix[:3, :3].T + matrix[:3, 3]
        world[:, 1] *= -1
        parts.append((world, faces))
        boxes.append((world.min(0), world.max(0)))
    boxes = np.asarray(boxes)
    chosen = np.full(len(parts), -1, dtype=int)
    uses = np.zeros(len(PALETTE), dtype=int)
    for index in range(len(parts)):
        nearby = np.all(boxes[:index, 1] >= boxes[index, 0]-1, axis=1)
        nearby &= np.all(boxes[:index, 0] <= boxes[index, 1]+1, axis=1)
        neighbors = chosen[:index][nearby]
        penalties = np.bincount(neighbors, minlength=len(PALETTE))*10000 + uses
        choice = int(np.argmin(penalties))
        chosen[index] = choice
        uses[choice] += 1
    all_vertices, all_faces, all_colors = [], [], []
    offset = 0
    for index, (vertices, faces) in enumerate(parts):
        all_vertices.append(vertices)
        all_faces.append(faces+offset)
        all_colors.append(np.tile(PALETTE[chosen[index]], (len(faces), 1)))
        offset += len(vertices)
    return np.concatenate(all_vertices), np.concatenate(all_faces), np.concatenate(all_colors)


def voxel_geometry(path):
    cells = json.loads(path.read_text(encoding='utf-8'))['voxels']
    corners = np.array([(0,0,0),(1,0,0),(1,1,0),(0,1,0),
                        (0,0,1),(1,0,1),(1,1,1),(0,1,1)], dtype=float)
    triangles = np.array([(0,2,1),(0,3,2),(4,5,6),(4,6,7),
                          (0,1,5),(0,5,4),(1,2,6),(1,6,5),
                          (2,3,7),(2,7,6),(3,0,4),(3,4,7)])
    vertices, faces = [], []
    for index, cell in enumerate(cells):
        origin = np.array([cell['x'], cell['y'], cell['z']])*[20,24,20]
        vertices.append(origin + .3 + corners*[19.4,23.4,19.4])
        faces.append(triangles+index*8)
    vertices, faces = np.concatenate(vertices), np.concatenate(faces)
    return vertices, faces, np.tile([182,193,205], (len(faces),1))


def render(name, geometry, size=760):
    vertices, faces, colors = geometry
    vertices = vertices.astype(np.float32)
    faces = faces.astype(np.int32)
    vertices -= (vertices.min(0)+vertices.max(0))*.5
    normals = np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],
                       vertices[faces[:,2]]-vertices[faces[:,0]])
    normals /= np.maximum(np.linalg.norm(normals, axis=1)[:,None], 1e-12)
    light = np.array([.35,.85,.4])
    light /= np.linalg.norm(light)
    shades = .53 + .46*np.abs(normals @ light)
    colors = np.clip(colors*shades[:,None], 0, 255).astype(np.float32)
    azimuth, elevation = math.radians(42), math.radians(28)
    direction = np.array([math.sin(azimuth)*math.cos(elevation), math.sin(elevation),
                          math.cos(azimuth)*math.cos(elevation)])
    right = np.cross([0,1,0], direction)
    right /= np.linalg.norm(right)
    up = np.cross(direction, right)
    flat = np.column_stack((vertices@right, vertices@up))
    center = (flat.min(0)+flat.max(0))*.5
    scale = size*.91 / max(np.ptp(flat, axis=0))
    projected = np.column_stack(((flat[:,0]-center[0])*scale+size/2,
                                 -(flat[:,1]-center[1])*scale+size/2,
                                 vertices@direction)).astype(np.float32)
    pixels = raster(projected, faces, colors, size)
    Image.fromarray(pixels).save(OUT / f'{name}.png')
    print('Rendered', name, flush=True)


def main():
    table = ROOT / 'Train/preview/piano_table_retile/results/A/table/vx80k5p_20261010_A_table_m0001'
    birdhouse = ROOT / 'tmp/teaser_design/birdhouse_conversion'
    for name, folder in [('table', table), ('birdhouse', birdhouse)]:
        render(name+'_voxels', voxel_geometry(folder / 'source.model.json'))
        render(name+'_bricks', colored_geometry(ldraw(folder / 'model.ldr')))

    samples = [
        'brickmore__camera_L2_P1_G__raw', 'brickmore__camera_L2_P1_G__stitched',
        'brickmore__car-L1V2__raw', 'brickmore__car-L1V2__stitched',
        'brickmore__birdhouse-L1__stitched', 'brickmore__chair-L2V5__raw',
        'brickmore__vessel_L1_P2_G__stitched', 'brickmore__bookshelf-L1-C1__stitched',
        'brickmore__guitar_L1_P2_G__stitched', 'brickmore__table-L1V3__stitched',
        'brickmore__pot-L1-A__stitched', 'brickmore__sofa-L1V3__stitched',
    ]
    for name in samples:
        assembly = json.loads((PACKAGE / 'Data/assemblies' / f'{name}.json').read_text(encoding='utf-8'))
        render(name, colored_geometry(assembly))

    (OUT / 'render_note.json').write_text(json.dumps({
        'geometry': 'Project source voxels and exported LDraw part transforms',
        'brick_colors': 'Diagnostic graph coloring of nearby brick bounding boxes',
        'source_voxel_colors': 'Uniform gray for visualization',
        'display_colors_are_model_predictions': False,
        'voxel_and_brick_dimensions': '20 LDU pitch; 24 LDU layer height',
        'view': {'azimuth_degrees': 42, 'elevation_degrees': 28},
    }, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
