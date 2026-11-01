"""bmore48_levels2 全量导出 OBJ(黄色砖块):raw.obj(canonical)+ stitched.obj(有兜底时)。
几何移植自包内 live_preview.export_glb(方砖+12段凸点);纯 Python,无 Blender。"""
import json
import math
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = Path(r'E:\brick_train\brick_infer_5070ti_20261001\BrickGPT\bmore48_levels2')
MTL_NAME = 'yellow.mtl'
INSET = 0.012
STUD_R = 0.24
STUD_H = 0.2   # LDraw 凸点高 4 LDu = 0.2 格距
Z_SCALE = 1.2  # LDraw 砖高 24 LDu / 格距 20 LDu = 1.2,与参考渲染比例一致
SEG = 16

MTL_TEXT = (
    'newmtl brick_yellow\n'
    'Ka 1.000 0.823 0.067\n'
    'Kd 1.000 0.823 0.067\n'
    'Ks 0.050 0.050 0.050\n'
    'Ns 32.0\n'
    'illum 2\n'
)


def bricks_centroid_offset(cells):
    lo = [min(p[i] for p in cells) for i in range(3)]
    hi = [max(p[i] for p in cells) + 1 for i in range(3)]
    return ((lo[0] + hi[0]) / 2, lo[2], (lo[1] + hi[1]) / 2)


def emit_obj(bricks, cells, path, mtl_rel):
    cx, cy, cz = bricks_centroid_offset(cells)
    verts, norms, faces = [], [], []

    def tri(a, b, c, n):
        ab = [b[i] - a[i] for i in range(3)]
        ac = [c[i] - a[i] for i in range(3)]
        cross = (ab[1] * ac[2] - ab[2] * ac[1],
                 ab[2] * ac[0] - ab[0] * ac[2],
                 ab[0] * ac[1] - ab[1] * ac[0])
        if sum(cross[i] * n[i] for i in range(3)) < 0:
            b, c = c, b
        base = len(verts)
        for p in (a, b, c):
            verts.append((p[0] - cx, (p[2] - cy) * Z_SCALE, p[1] - cz))
            norms.append(n)
        faces.append((base + 1, base + 2, base + 3))

    def quad(a, b, c, d, n):
        tri(a, b, c, n)
        tri(a, c, d, n)

    for b in bricks:
        h, w, x, y, z = b['h'], b['w'], b['x'], b['y'], b['z']
        x0, x1 = x + INSET, x + h - INSET
        y0, y1 = y + INSET, y + w - INSET
        z0, z1 = z + INSET, z + 1 - INSET
        quad((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (0, 0, -1))
        quad((x1, y0, z1), (x0, y0, z1), (x0, y1, z1), (x1, y1, z1), (0, 0, 1))
        quad((x0, y0, z1), (x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (-1, 0, 0))
        quad((x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0), (1, 0, 0))
        quad((x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1), (0, 1, 0))
        quad((x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0), (0, -1, 0))
        for sx in range(x, x + h):
            for sy in range(y, y + w):
                if (sx, sy, z + 1) in cells:
                    continue
                cxp, cyp = sx + .5, sy + .5
                bottom = z + 1 - INSET
                top = bottom + STUD_H
                for j in range(SEG):
                    a1 = j * 2 * math.pi / SEG
                    a2 = (j + 1) * 2 * math.pi / SEG
                    p = (cxp + STUD_R * math.cos(a1), cyp + STUD_R * math.sin(a1), top)
                    q = (cxp + STUD_R * math.cos(a2), cyp + STUD_R * math.sin(a2), top)
                    tri((cxp, cyp, top), p, q, (0, 0, 1))
                    nrm = (math.cos((a1 + a2) / 2), math.sin((a1 + a2) / 2), 0)
                    quad((p[0], p[1], bottom), (q[0], q[1], bottom), q, p, nrm)

    lines = [f'# BrickMore-48 export | bricks={len(bricks)} voxels={len(cells)}',
             f'mtllib {mtl_rel}', 'o brickgpt', 'usemtl brick_yellow']
    for v in verts:
        lines.append(f'v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}')
    for n in norms:
        lines.append(f'vn {n[0]:.4f} {n[1]:.4f} {n[2]:.4f}')
    for f in faces:
        lines.append(f'f {f[0]}//{f[0]} {f[1]}//{f[1]} {f[2]}//{f[2]}')
    path.write_text('\n'.join(lines), encoding='utf-8')


LINE = re.compile(r'(\d+)x(\d+) \((\d+),(\d+),(\d+)\)')


def parse_canonical(txt):
    bricks = []
    for ln in txt.splitlines():
        m = LINE.match(ln.strip())
        if not m:
            continue
        h, w, x, y, z = map(int, m.groups())
        bricks.append(dict(h=h, w=w, x=x, y=y, z=z))
    return bricks


def cells_of(bricks):
    return {(x, y, b['z']) for b in bricks
            for x in range(b['x'], b['x'] + b['h']) for y in range(b['y'], b['y'] + b['w'])}


(BASE / MTL_NAME).write_text(MTL_TEXT, encoding='utf-8')
n_raw = n_st = 0
for d in sorted(BASE.glob('*/*/')):
    rep_p = d / 'raw_report.json'
    if rep_p.exists() and not (d / 'raw.obj').exists():
        bricks = json.loads(rep_p.read_text(encoding='utf-8'))['bricks']
        emit_obj(bricks, cells_of(bricks), d / 'raw.obj', '../../' + MTL_NAME)
        n_raw += 1
    st_p = d / 'stitched.txt'
    if st_p.exists() and not (d / 'stitched.obj').exists():
        sb = parse_canonical(st_p.read_text(encoding='utf-8'))
        emit_obj(sb, cells_of(sb), d / 'stitched.obj', '../../' + MTL_NAME)
        n_st += 1
print(f'OBJ DONE: raw {n_raw}, stitched {n_st}')
