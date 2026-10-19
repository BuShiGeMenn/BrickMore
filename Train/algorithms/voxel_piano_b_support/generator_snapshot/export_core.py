from __future__ import annotations

import math
import struct
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw


GRID = 48
PALETTE = {
    "white": (238, 238, 232, 255),
    "cream": (222, 205, 166, 255),
    "light_blue": (126, 177, 205, 255),
    "blue": (57, 105, 155, 255),
    "brown": (133, 83, 48, 255),
    "dark_brown": (77, 46, 30, 255),
    "tan": (191, 145, 86, 255),
    "dark_gray": (66, 70, 76, 255),
    "gray": (123, 128, 132, 255),
    "black": (25, 27, 30, 255),
    "red": (165, 55, 48, 255),
    "green": (72, 121, 83, 255),
    "yellow": (214, 174, 63, 255),
}


@dataclass(frozen=True)
class Cell:
    color: str
    part: str
    importance: int = 5


class Model:
    def __init__(self) -> None:
        self.cells: dict[tuple[int, int, int], Cell] = {}
        self.repairs: list[dict] = []

    def set(self, x: int, y: int, z: int, color: str, part: str, importance: int = 5) -> None:
        coord = (round(x), round(y), round(z))
        current = self.cells.get(coord)
        if current is None or importance >= current.importance:
            self.cells[coord] = Cell(color, part, importance)

    def box(self, x0: int, x1: int, y0: int, y1: int, z0: int, z1: int, color: str, part: str, importance: int = 5) -> None:
        for x in range(round(min(x0, x1)), round(max(x0, x1)) + 1):
            for y in range(round(min(y0, y1)), round(max(y0, y1)) + 1):
                for z in range(round(min(z0, z1)), round(max(z0, z1)) + 1):
                    self.set(x, y, z, color, part, importance)

    def segment(self, start: tuple[float, float, float], end: tuple[float, float, float], radius: float, color: str, part: str, importance: int = 5) -> None:
        distance = math.dist(start, end)
        steps = max(1, math.ceil(distance * 2.2))
        r = max(0, math.ceil(radius))
        for index in range(steps + 1):
            t = index / steps
            center = tuple(start[a] * (1 - t) + end[a] * t for a in range(3))
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    for dz in range(-r, r + 1):
                        if dx * dx + dy * dy + dz * dz <= radius * radius + 0.35:
                            self.set(round(center[0] + dx), round(center[1] + dy), round(center[2] + dz), color, part, importance)

    def cylinder_y(self, cx: float, cz: float, y0: int, y1: int, radius: float, color: str, part: str, importance: int = 5, hollow: bool = False) -> None:
        outer = math.ceil(radius)
        inner = max(0.0, radius - 1.6)
        for y in range(round(min(y0, y1)), round(max(y0, y1)) + 1):
            for x in range(round(cx) - outer, round(cx) + outer + 1):
                for z in range(round(cz) - outer, round(cz) + outer + 1):
                    d2 = (x - cx) ** 2 + (z - cz) ** 2
                    if d2 <= radius ** 2 + 0.25 and (not hollow or d2 >= inner ** 2):
                        self.set(x, y, z, color, part, importance)

    def cylinder_x(self, x0: int, x1: int, cy: float, cz: float, radius: float, color: str, part: str, importance: int = 5, hollow: bool = False) -> None:
        """Rasterize a cylinder whose axis runs along X, for wheels and rollers."""
        outer = math.ceil(radius)
        inner = max(0.0, radius - 1.6)
        for x in range(round(min(x0, x1)), round(max(x0, x1)) + 1):
            for y in range(round(cy) - outer, round(cy) + outer + 1):
                for z in range(round(cz) - outer, round(cz) + outer + 1):
                    d2 = (y - cy) ** 2 + (z - cz) ** 2
                    if d2 <= radius ** 2 + 0.25 and (not hollow or d2 >= inner ** 2):
                        self.set(x, y, z, color, part, importance)

    def ellipsoid(self, cx: float, cy: float, cz: float, rx: float, ry: float, rz: float, color: str, part: str, importance: int = 5, shell: bool = False) -> None:
        for x in range(math.floor(cx-rx), math.ceil(cx+rx)+1):
            for y in range(math.floor(cy-ry), math.ceil(cy+ry)+1):
                for z in range(math.floor(cz-rz), math.ceil(cz+rz)+1):
                    q = ((x-cx)/max(rx,.5))**2 + ((y-cy)/max(ry,.5))**2 + ((z-cz)/max(rz,.5))**2
                    inner = ((x-cx)/max(rx-1.4,.5))**2 + ((y-cy)/max(ry-1.4,.5))**2 + ((z-cz)/max(rz-1.4,.5))**2
                    if q <= 1.0 and (not shell or inner >= 1.0):
                        self.set(x, y, z, color, part, importance)


def neighbors(coord: tuple[int, int, int]):
    x, y, z = coord
    yield x + 1, y, z
    yield x - 1, y, z
    yield x, y + 1, z
    yield x, y - 1, z
    yield x, y, z + 1
    yield x, y, z - 1


def connected_components(cells: dict[tuple[int, int, int], Cell]) -> list[set[tuple[int, int, int]]]:
    remaining = set(cells)
    components = []
    while remaining:
        start = remaining.pop()
        component = {start}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for target in neighbors(current):
                if target in remaining:
                    remaining.remove(target)
                    component.add(target)
                    queue.append(target)
        components.append(component)
    return sorted(components, key=len, reverse=True)


def connect_components(model: Model) -> None:
    repairs = 0
    while True:
        components = connected_components(model.cells)
        if len(components) <= 1:
            break
        main, other = components[0], components[1]
        a, b = min(
            ((p, q) for p in main for q in other),
            key=lambda pair: sum(abs(pair[0][axis] - pair[1][axis]) for axis in range(3)),
        )
        source = model.cells[a]
        x, y, z = a
        for target_axis in range(3):
            target_value = b[target_axis]
            while (x, y, z)[target_axis] != target_value:
                values = [x, y, z]
                values[target_axis] += 1 if target_value > values[target_axis] else -1
                x, y, z = values
                model.set(x, y, z, source.color, "semantic_connection", 6)
        repairs += 1
    if repairs:
        model.repairs.append({"type": "semantic_face_connection", "connectionCount": repairs})


def normalize(model: Model) -> None:
    if not model.cells:
        raise ValueError("Cannot normalize an empty model")
    xs = [p[0] for p in model.cells]
    ys = [p[1] for p in model.cells]
    zs = [p[2] for p in model.cells]
    size_x = max(xs) - min(xs) + 1
    size_y = max(ys) - min(ys) + 1
    size_z = max(zs) - min(zs) + 1
    if max(size_x, size_y, size_z) > GRID:
        raise ValueError(f"Model exceeds {GRID} grid: {(size_x, size_y, size_z)}")
    shift_x = (GRID - size_x) // 2 - min(xs)
    shift_y = -min(ys)
    shift_z = (GRID - size_z) // 2 - min(zs)
    model.cells = {(x + shift_x, y + shift_y, z + shift_z): cell for (x, y, z), cell in model.cells.items()}


FACES = (
    ((1, 0, 0), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1))),
    ((-1, 0, 0), ((0, 0, 1), (0, 1, 1), (0, 1, 0), (0, 0, 0))),
    ((0, 1, 0), ((0, 1, 1), (1, 1, 1), (1, 1, 0), (0, 1, 0))),
    ((0, -1, 0), ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1))),
    ((0, 0, 1), ((1, 0, 1), (1, 1, 1), (0, 1, 1), (0, 0, 1))),
    ((0, 0, -1), ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0))),
)


def save_obj(path: Path, model: Model) -> None:
    materials = sorted({cell.color for cell in model.cells.values()})
    mtl_path = path.with_suffix(".mtl")
    with mtl_path.open("w", encoding="ascii", newline="\n") as handle:
        for material in materials:
            r, g, b, _ = PALETTE[material]
            handle.write(f"newmtl voxel_{material}\nKd {r/255:.6f} {g/255:.6f} {b/255:.6f}\nKa 0 0 0\n\n")
    vertex = 1
    with path.open("w", encoding="ascii", newline="\n") as handle:
        handle.write(f"mtllib {mtl_path.name}\n")
        for color in materials:
            handle.write(f"usemtl voxel_{color}\n")
            for (x, y, z), cell in sorted(model.cells.items()):
                if cell.color != color:
                    continue
                for direction, corners in FACES:
                    if (x + direction[0], y + direction[1], z + direction[2]) in model.cells:
                        continue
                    for cx, cy, cz in corners:
                        handle.write(f"v {x+cx} {y+cy} {z+cz}\n")
                    handle.write(f"f {vertex} {vertex+1} {vertex+2} {vertex+3}\n")
                    vertex += 4


def chunk(name: bytes, content: bytes, children: bytes = b"") -> bytes:
    return name + struct.pack("<II", len(content), len(children)) + content + children


def save_vox(path: Path, model: Model) -> None:
    colors = list(PALETTE)
    color_index = {name: index + 1 for index, name in enumerate(colors)}
    size = chunk(b"SIZE", struct.pack("<III", GRID, GRID, GRID))
    entries = bytearray()
    for (x, y, z), cell in sorted(model.cells.items()):
        entries.extend(bytes((x, z, y, color_index[cell.color])))
    xyzi = chunk(b"XYZI", struct.pack("<I", len(model.cells)) + bytes(entries))
    rgba = bytearray()
    for name in colors:
        rgba.extend(bytes(PALETTE[name]))
    for _ in range(256 - len(colors)):
        rgba.extend(bytes((0, 0, 0, 255)))
    main = chunk(b"MAIN", b"", size + xyzi + chunk(b"RGBA", bytes(rgba)))
    path.write_bytes(b"VOX " + struct.pack("<I", 150) + main)


def projection(model: Model, view: str, size: int = 180) -> Image.Image:
    if view == "front":
        key = lambda p: (p[0], p[1]); depth = lambda p: p[2]
    elif view == "right":
        key = lambda p: (p[2], p[1]); depth = lambda p: p[0]
    else:
        key = lambda p: (p[0], p[2]); depth = lambda p: p[1]
    visible = {}
    for p, cell in model.cells.items():
        k = key(p)
        if k not in visible or depth(p) > visible[k][0]:
            visible[k] = (depth(p), cell)
    us = [k[0] for k in visible]
    vs = [k[1] for k in visible]
    span_u, span_v = max(us) - min(us) + 1, max(vs) - min(vs) + 1
    scale = max(2, min((size - 16) // max(1, span_u), (size - 16) // max(1, span_v)))
    image = Image.new("RGB", (size, size), "#f7f7f7")
    draw = ImageDraw.Draw(image)
    ox = (size - span_u * scale) // 2
    oy = (size - span_v * scale) // 2
    for (u, v), (_, cell) in visible.items():
        x = ox + (u - min(us)) * scale
        y = size - oy - (v - min(vs) + 1) * scale
        rgb = PALETTE[cell.color][:3]
        draw.rectangle((x, y, x + scale - 1, y + scale - 1), fill=rgb)
    return image


def save_preview(path: Path, model: Model) -> None:
    canvas = Image.new("RGB", (570, 205), "white")
    draw = ImageDraw.Draw(canvas)
    for index, view in enumerate(("front", "right", "top")):
        draw.text((10 + index * 190, 4), view.upper(), fill="#273444")
        canvas.paste(projection(model, view), (5 + index * 190, 22))
    canvas.save(path)
