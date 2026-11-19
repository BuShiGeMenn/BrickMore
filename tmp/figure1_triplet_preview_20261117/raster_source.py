from pathlib import Path
from functools import lru_cache
import math
import numpy as np
from numba import njit

DATA = Path('D:/BrickMore/Essay/BrickMore/V2/figure_data')

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
    with np.load(DATA / 'meshes' / f'{stem}.npz') as data:
        return data['vertices'], data['faces']


