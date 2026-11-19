"""Strict, model-independent voxel adapters. Internal coordinates are Z-up."""
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
from optimized_geometry import Placement

MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_VOXELS = 200_000
MAX_DENSE_CELLS = 2_097_152


def integer(value, name='coordinate'):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be a finite integer, not {value!r}')
    if not math.isfinite(value) or int(value) != value:
        raise ValueError(f'{name} must be a finite integer, not {value!r}')
    return int(value)


def color_value(value=None):
    if value is None:
        return 0xCCCCCC
    if isinstance(value, str):
        text = value.removeprefix('#')
        if len(text) != 6 or any(c not in '0123456789abcdefABCDEF' for c in text):
            raise ValueError('color must be #RRGGBB or a 24-bit integer')
        return int(text, 16)
    value = integer(value, 'color')
    if not 0 <= value <= 0xFFFFFF:
        raise ValueError('color out of range')
    return value  # Zero is black, NOT a missing value.


@dataclass
class VoxelModel:
    cells: dict
    metadata: dict = field(default_factory=dict)
    bricks: list | None = None

    def normalized(self, normalize_origin=False, world_dim=128):
        if not self.cells:
            raise ValueError('empty voxel model')
        if len(self.cells) > MAX_VOXELS:
            raise ValueError('voxel budget exceeded')
        origin = tuple(min(p[i] for p in self.cells) for i in range(3))
        shift = tuple(-v for v in origin) if normalize_origin else (0, 0, 0)
        cells = {tuple(p[i] + shift[i] for i in range(3)): c for p, c in self.cells.items()}
        if any(any(v < 0 or v >= world_dim for v in p) for p in cells):
            raise ValueError('coordinates outside world; use explicit origin normalization or increase world_dim')
        bricks = None if self.bricks is None else [
            Placement(b.h, b.w, b.x+shift[0], b.y+shift[1], b.z+shift[2]) for b in self.bricks]
        previous_shift = self.metadata.get('origin_shift_xyz', [0, 0, 0])
        total_shift = [previous_shift[i] + shift[i] for i in range(3)]
        return VoxelModel(cells, {**self.metadata, 'origin_shift_xyz': total_shift,
                                 'internal_up_axis': 'z', 'world_dim': world_dim}, bricks)


def from_json(value, up_axis='z'):
    """Accept voxel arrays, {voxels:...}, Ocean {data:...}, or {bricks:...}.

    Ocean coordinates use Y-up: request up_axis='y'. No automatic axis guessing.
    Bricks expand to exact cells; overlapping bricks or inconsistent cells fail.
    """
    if up_axis not in ('y', 'z'):
        raise ValueError('up_axis must be y or z')
    metadata = {'source_format': 'json', 'source_up_axis': up_axis, 'duplicate_voxels': 0}
    items = value
    kind = 'voxels'
    if isinstance(value, dict):
        if 'voxels' in value:
            items = value['voxels']
        elif 'data' in value:
            items = value['data']
        elif 'bricks' in value:
            items, kind = value['bricks'], 'bricks'
        else:
            raise ValueError('expected voxels/data/bricks array')
    if not isinstance(items, list) or len(items) > MAX_VOXELS:
        raise ValueError('input must be an array within voxel budget')
    cells, bricks = {}, []
    def point(raw):
        if isinstance(raw, dict):
            coords = [raw.get(k) for k in ('x', 'y', 'z')]
        elif isinstance(raw, (list, tuple)) and len(raw) == 3:
            coords = raw
        else:
            raise ValueError('voxel must have exactly three coordinates')
        x, y, z = (integer(v) for v in coords)
        return (x, z, y) if up_axis == 'y' else (x, y, z)
    for raw in items:
        p = point(raw)
        c = color_value(raw.get('color', raw.get('c')) if isinstance(raw, dict) else None)
        if kind == 'bricks':
            if not isinstance(raw, dict):
                raise ValueError('brick must be an object')
            if up_axis == 'y':
                h, w = integer(raw.get('width'), 'width'), integer(raw.get('depth'), 'depth')
            else:
                h, w = integer(raw.get('h'), 'h'), integer(raw.get('w'), 'w')
            if h < 1 or w < 1 or h > 128 or w > 128 or raw.get('height', 1) != 1:
                raise ValueError('only positive rectangular single-brick-height blocks supported')
            b = Placement(h, w, *p)
            footprint = set(b.cells())
            if 'cells' in raw:
                listed = [point(item) for item in raw['cells']]
                if len(listed) != len(set(listed)) or set(listed) != footprint:
                    raise ValueError('brick cells do not match its complete rectangular footprint')
            bricks.append(b)
        else:
            footprint = [p]
        for pos in footprint:
            if pos in cells:
                if kind == 'bricks':
                    raise ValueError('overlapping source bricks')
                if cells[pos] != c:
                    raise ValueError('same coordinate has conflicting colors')
                metadata['duplicate_voxels'] += 1
            cells[pos] = c
            if len(cells) > MAX_VOXELS:
                raise ValueError('voxel budget exceeded')
    metadata['source_kind'] = kind
    return VoxelModel(cells, metadata, bricks if kind == 'bricks' else None)


def read_model(path, up_axis='z', array_axis_order='xyz', threshold=None, prefer_bricks=False):
    path = Path(path)
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError('input file too large')
    ext = path.suffix.lower()
    if ext == '.json':
        value = json.loads(path.read_text(encoding='utf-8-sig'))
        if prefer_bricks and isinstance(value, dict) and 'bricks' in value:
            value = {'bricks': value['bricks']}
        return from_json(value, up_axis)
    if ext in ('.txt', '.xyz'):
        text = path.read_text(encoding='utf-8-sig')
        lines = [v.strip() for v in text.splitlines() if v.strip() and not v.lstrip().startswith('#')]
        if len(lines) > MAX_VOXELS:
            raise ValueError('input record budget exceeded')
        if ext == '.txt' and any('(' in line for line in lines):
            if up_axis != 'z':
                raise ValueError('BrickGPT TXT is already Z-up')
            bricks = [Placement.parse(line) for line in lines]
            model = from_json({'bricks': [dict(h=b.h,w=b.w,x=b.x,y=b.y,z=b.z) for b in bricks]})
            model.metadata['source_format'] = 'brickgpt_txt'
            return model
        try:
            records = [[int(v) for v in line.replace(',', ' ').split()] for line in lines]
        except ValueError as exc:
            raise ValueError('XYZ input must contain integer triplets') from exc
        return from_json(records, up_axis)
    if ext == '.npy':
        import numpy as np  # Optional; core does not require NumPy or Torch.
        if sorted(array_axis_order) != ['x', 'y', 'z']:
            raise ValueError('array_axis_order must be a permutation of xyz')
        data = np.load(path, allow_pickle=False, mmap_mode='r')
        if data.ndim != 3 or data.size > MAX_DENSE_CELLS or max(data.shape) > 128:
            raise ValueError('expected bounded three-dimensional array')
        if data.dtype.kind not in 'bifu' or not np.isfinite(data).all():
            raise ValueError('dense array must be finite numeric occupancy')
        if threshold is None:
            if not np.isin(data, (0, 1)).all():
                raise ValueError('non-binary dense input requires an explicit occupancy threshold')
            occupied = data != 0
        else:
            if not math.isfinite(threshold):
                raise ValueError('threshold must be finite')
            occupied = data >= threshold
        points = np.argwhere(occupied)
        if len(points) > MAX_VOXELS:
            raise ValueError('voxel budget exceeded')
        records = [[int(row[array_axis_order.index(k)]) for k in 'xyz'] for row in points]
        model = from_json(records, up_axis)
        model.metadata.update(source_format='npy', array_axis_order=array_axis_order, threshold=threshold)
        return model
    raise ValueError('supported input: JSON voxel/brick arrays, BrickGPT TXT, XYZ, NPY occupancy; mesh/VOX/LDR import not supported')
