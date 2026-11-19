"""CPU-only, incremental assembly geometry. Not a static-force solver or VLM.

No reference structure is used to accept, repair, or rank a generation.
"""
from collections import deque
from dataclasses import asdict, dataclass
import hashlib
import json
import re
from brick_catalog import BRICKGPT_DIMENSIONS, dimensions_for_library


DIMENSIONS = BRICKGPT_DIMENSIONS


@dataclass(frozen=True)
class Placement:
    h: int
    w: int
    x: int
    y: int
    z: int

    def to_txt(self):
        return f"{self.h}x{self.w} ({self.x},{self.y},{self.z})\n"

    @classmethod
    def parse(cls, text):
        match = re.fullmatch(r"(\d+)x(\d+) \((\d+),(\d+),(\d+)\)", text.strip())
        if not match:
            raise ValueError("ill_formatted")
        return cls(*map(int, match.groups()))

    @classmethod
    def from_brick(cls, brick):
        return cls(*(getattr(brick, key) for key in ("h", "w", "x", "y", "z")))

    def cells(self):
        return ((x, y, self.z) for x in range(self.x, self.x + self.h)
                for y in range(self.y, self.y + self.w))


@dataclass(frozen=True)
class GeometryConfig:
    world_dim: int = 20
    bottom_up: bool = True
    require_lower_support: bool = True
    min_support_fraction: float = 0.10
    max_components: int = 64
    min_bricks: int = 6
    brick_library: str = 'brickgpt'
    max_cantilever_distance: int | None = None

    def __post_init__(self):
        if any(type(v) is not int for v in (self.world_dim,self.max_components,self.min_bricks)):
            raise ValueError('geometry counts must be integers')
        if not 1 <= self.world_dim <= 128:
            raise ValueError("world_dim must be in 1..128")
        if not 0 <= self.min_support_fraction <= 1:
            raise ValueError("invalid support fraction")
        if self.max_components < 1 or self.min_bricks < 1:
            raise ValueError("invalid geometry budget")
        dimensions_for_library(self.brick_library)
        if self.max_cantilever_distance is not None and (
                type(self.max_cantilever_distance) is not int or self.max_cantilever_distance < 0):
            raise ValueError('invalid cantilever distance')

    @property
    def dimensions(self):
        return dimensions_for_library(self.brick_library)


class GeometryState:
    """Occupied-cell index + union-find, WITHOUT a virtual ground union."""
    def __init__(self, cfg=None):
        self.cfg = cfg or GeometryConfig()
        self.bricks = []
        self.occupied = {}
        self.parents = []
        self.version = 0
        self.support_fractions = []
        self.support_distances = []
        self._component_count = 0
        self._candidate_cache = None

    def find(self, index):
        while self.parents[index] != index:
            self.parents[index] = self.parents[self.parents[index]]
            index = self.parents[index]
        return index

    def groups(self):
        groups = {}
        for index in range(len(self.bricks)):
            groups.setdefault(self.find(index), []).append(index)
        return list(groups.values())

    @property
    def components(self):
        return self._component_count

    def clone(self):
        """Copy mutable indices only; Placement and GeometryConfig are immutable."""
        state = GeometryState(self.cfg)
        state.bricks = self.bricks.copy()
        state.occupied = self.occupied.copy()
        state.parents = self.parents.copy()
        state.support_fractions = self.support_fractions.copy()
        state.support_distances = self.support_distances.copy()
        state._component_count = self._component_count
        state.version = self.version
        return state

    def contact(self, brick):
        lower_cells = {(x, y, brick.z - 1) for x, y, _ in brick.cells()}
        upper_cells = {(x, y, brick.z + 1) for x, y, _ in brick.cells()}
        lower = lower_cells.intersection(self.occupied)
        neighbours = {self.occupied[cell] for cell in lower | upper_cells.intersection(self.occupied)}
        return len(lower) / (brick.h * brick.w), neighbours

    def check(self, brick):
        if any(type(getattr(brick,key,None)) is not int for key in ('h','w','x','y','z')):
            return 'non_integer_brick'
        if (brick.h, brick.w) not in self.cfg.dimensions:
            return "not_in_library"
        if not (0 <= brick.x <= self.cfg.world_dim - brick.h and
                0 <= brick.y <= self.cfg.world_dim - brick.w and
                0 <= brick.z < self.cfg.world_dim):
            return "out_of_bounds"
        if any(cell in self.occupied for cell in brick.cells()):
            return "collision"
        previous_z = self.bricks[-1].z if self.bricks else 0
        if self.cfg.bottom_up and brick.z < previous_z:
            return "layer_order"
        if self.cfg.bottom_up and brick.z > previous_z + 1:
            return "layer_jump"
        support, neighbours = self.contact(brick)
        if brick.z > 0 and self.cfg.require_lower_support:
            if not support or support < self.cfg.min_support_fraction:
                return "lower_support"
        if brick.z > 0 and self.cfg.max_cantilever_distance is not None:
            distance = self.support_distance(brick)
            if distance is None or distance > self.cfg.max_cantilever_distance:
                return 'overextended'
        if not self.bricks and brick.z != 0:
            return "no_ground_anchor"
        roots = {self.find(index) for index in neighbours}
        if self.components + 1 - len(roots) > self.cfg.max_components:
            return "component_budget"
        return "success"

    def support_distance(self, brick):
        """Maximum footprint Manhattan distance from a direct lower stud.

        A local cantilever heuristic, not center-of-mass or force equilibrium.
        """
        if brick.z == 0:
            return 0
        footprint = [(x,y) for x,y,_ in brick.cells()]
        anchors = [(x,y) for x,y in footprint if (x,y,brick.z-1) in self.occupied]
        if not anchors:
            return None
        return max(min(abs(x-a)+abs(y-b) for a,b in anchors) for x,y in footprint)

    def add(self, brick, enforce_policy=True):
        reason = self.check(brick)
        if reason != "success" and enforce_policy:
            raise ValueError(reason)
        # Audits may ignore sequence/support policy, but never corrupt occupancy.
        if reason in ("collision", "out_of_bounds", "not_in_library", 'non_integer_brick'):
            raise ValueError(reason)
        support, neighbours = self.contact(brick)
        roots = {self.find(other) for other in neighbours}
        self._component_count += 1 - len(roots)
        self.support_distances.append(self.support_distance(brick))
        index = len(self.bricks)
        self.bricks.append(brick)
        self.parents.append(index)
        for other in neighbours:
            self.parents[self.find(other)] = self.find(index)
        for cell in brick.cells():
            self.occupied[cell] = index
        self.support_fractions.append(1.0 if brick.z == 0 else support)
        self.version += 1
        self._candidate_cache = None

    @classmethod
    def rebuild(cls, bricks, cfg=None, enforce_policy=True):
        state = cls(cfg)
        for brick in bricks:
            state.add(Placement.from_brick(brick), enforce_policy=enforce_policy)
        return state

    def fingerprint(self):
        return hashlib.sha256("".join(b.to_txt() for b in self.bricks).encode()).hexdigest()

    def legal_candidates(self):
        """Limit token choices to complete locally feasible placements, not just syntax.

        Only occupied support footprints are considered above ground. The cache
        is invalidated at every commit; callers may filter taboo candidates.
        """
        if self._candidate_cache is not None:
            return self._candidate_cache
        dim = self.cfg.world_dim
        last_z = self.bricks[-1].z if self.bricks else 0
        heights = range(last_z, min(dim, last_z + 2)) if self.cfg.bottom_up else range(dim)
        candidates = []
        # Compute component roots once, rather than for every candidate.
        roots = {i: self.find(i) for i in range(len(self.bricks))}
        component_count = len(set(roots.values()))
        for z in heights:
            if not self.bricks and z != 0:
                continue
            below = {(x, y) for x, y, cell_z in self.occupied if cell_z == z - 1}
            for h, w in self.cfg.dimensions:
                if z > 0 and self.cfg.require_lower_support:
                    origins = {(x - dx, y - dy) for x, y in below
                               for dx in range(h) for dy in range(w)
                               if 0 <= x - dx <= dim - h and 0 <= y - dy <= dim - w}
                else:
                    origins = {(x, y) for x in range(dim - h + 1) for y in range(dim - w + 1)}
                for x, y in sorted(origins):
                    brick = Placement(h, w, x, y, z)
                    cells = tuple(brick.cells())
                    if any(cell in self.occupied for cell in cells):
                        continue
                    support, neighbours = self.contact(brick)
                    if z > 0 and self.cfg.require_lower_support and support < self.cfg.min_support_fraction:
                        continue
                    if component_count + 1 - len({roots[i] for i in neighbours}) > self.cfg.max_components:
                        continue
                    if self.cfg.max_cantilever_distance is not None and z > 0:
                        distance = self.support_distance(brick)
                        if distance is None or distance > self.cfg.max_cantilever_distance:
                            continue
                    candidates.append(brick)
        self._candidate_cache = tuple(candidates)
        return self._candidate_cache

    def audit(self):
        groups = self.groups()
        grounded = [any(self.bricks[i].z == 0 for i in group) for group in groups]
        layer_order = all(a.z <= b.z for a, b in zip(self.bricks, self.bricks[1:]))
        bad_support = [i for i, (b, support) in enumerate(zip(self.bricks, self.support_fractions))
                       if b.z > 0 and (support == 0 or support < self.cfg.min_support_fraction)]
        overextended = [i for i,(b,distance) in enumerate(zip(self.bricks,self.support_distances))
                        if b.z > 0 and self.cfg.max_cantilever_distance is not None and
                        (distance is None or distance > self.cfg.max_cantilever_distance)]
        return {"bricks": len(self.bricks), "components": len(groups),
                "component_sizes": sorted(map(len, groups), reverse=True),
                "ground_reachable": bool(groups) and all(grounded),
                "single_component": len(groups) == 1, "bottom_up_order": layer_order,
                "unsupported_prefix_indices": bad_support,
                "prefix_support_pass": not bad_support,
                "overextended_prefix_indices": overextended,
                "prefix_cantilever_pass": not overextended,
                "max_cantilever_distance_observed": max((d for d in self.support_distances if d is not None),default=0),
                "min_support_fraction": min(self.support_fractions, default=0.0),
                "mean_support_fraction": sum(self.support_fractions) / len(self.support_fractions) if self.bricks else 0.0,
                "geometry_config": asdict(self.cfg),
                "static_stability": None, "semantic_verified": False}


def plane_components(cells):
    remaining = set(cells)
    groups = []
    while remaining:
        queue = [remaining.pop()]
        group = set(queue)
        while queue:
            x, y = queue.pop()
            for neighbour in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    group.add(neighbour)
                    queue.append(neighbour)
        groups.append(group)
    return groups


def has_enclosed_air(cells):
    """2-D cavity proxy; does NOT prove a usable 3-D cup or a handle."""
    if not cells:
        return False
    xmin, xmax = min(x for x, _ in cells) - 1, max(x for x, _ in cells) + 1
    ymin, ymax = min(y for _, y in cells) - 1, max(y for _, y in cells) + 1
    empty = {(x, y) for x in range(xmin, xmax + 1) for y in range(ymin, ymax + 1)} - cells
    queue = deque([(xmin, ymin)])
    visited = {(xmin, ymin)}
    while queue:
        x, y = queue.popleft()
        for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if point in empty and point not in visited:
                visited.add(point)
                queue.append(point)
    return bool(empty - visited)


def shape_proxy(state, caption):
    """Conservative category cues, explicitly NOT semantic proof.

    These are rejection/ranking heuristics, not a learned classifier. They may
    reject stylized valid shapes, and passing them does not prove prompt fidelity.
    """
    text = caption.lower()
    category = next((name for name in ("bench", "chair", "sofa", "table", "mug", "cup", "bus", "car", "vessel")
                     if re.search(r"\b" + name + r"\b", text)), "unknown")
    layers = {}
    for x, y, z in state.occupied:
        layers.setdefault(z, set()).add((x, y))
    surfaces = []
    for z, cells in layers.items():
        for group in plane_components(cells):
            sx = max(x for x, _ in group) - min(x for x, _ in group) + 1
            sy = max(y for _, y in group) - min(y for _, y in group) + 1
            if sx >= 2 and sy >= 2 and len(group) >= 8 and len(group) / (sx * sy) >= 0.35:
                surfaces.append((z, len(group)))
    height = max(layers, default=-1) + 1
    sx = max((x for x, _, _ in state.occupied), default=-1) - min((x for x, _, _ in state.occupied), default=0) + 1
    sy = max((y for _, y, _ in state.occupied), default=-1) - min((y for _, y, _ in state.occupied), default=0) + 1
    checks = {}
    if category in ("bench", "chair", "sofa", "table"):
        raised = [surface for surface in surfaces if surface[0] > 0]
        checks["raised_horizontal_surface"] = bool(raised)
        if category in ("chair", "sofa") and "back" in text:
            checks["surface_with_structure_above"] = any(
                z < height - 1 and sum(len(cells) for level, cells in layers.items() if level > z) >= 4
                for z, _ in raised)
    if category in ("mug", "cup"):
        checks["enclosed_air_cross_section"] = any(has_enclosed_air(cells) for cells in layers.values())
    if category in ("bench", "table", "car", "bus", "vessel"):
        checks["not_extreme_vertical_column"] = height <= 2 * max(sx, sy, 1)
    if category in ("car", "bus", "vessel"):
        checks["coherent_horizontal_body"] = bool(surfaces) and max(sx, sy) >= 4
    issues = [key for key, passed in checks.items() if not passed]
    cue_score = sum(checks.values()) / len(checks) if checks else 0.5
    # Small, transparent tie-breaker; never substitutes for a failed cue.
    if category in ("mug", "cup"):
        detail = sum(has_enclosed_air(cells) for cells in layers.values()) / max(len(layers), 1)
    elif category in ("bench", "table", "car", "bus", "vessel"):
        detail = min(1.0, max(sx, sy) / max(height, 1))
    else:
        detail = min(1.0, max((area for _, area in surfaces), default=0) / max(sx * sy, 1))
    return {"category": category, "checks": checks, "issues": issues,
            "pass": bool(state.bricks) and not issues,
            "score": 0.8 * cue_score + 0.2 * detail, "cue_score": cue_score,
            "status": "heuristic_only" if checks else "not_assessed",
            "bbox": [sx, sy, height], "semantic_verified": False}


def completion_check(state, caption, require_shape=True):
    geometry = state.audit()
    proxy = shape_proxy(state, caption)
    issues = []
    if len(state.bricks) < state.cfg.min_bricks:
        issues.append("too_few_bricks")
    if not geometry["single_component"]:
        issues.append("multiple_components")
    if not geometry["ground_reachable"]:
        issues.append("not_ground_reachable")
    if state.cfg.bottom_up and not geometry["bottom_up_order"]:
        issues.append("layer_order")
    if state.cfg.require_lower_support and not geometry["prefix_support_pass"]:
        issues.append("lower_support")
    if state.cfg.max_cantilever_distance is not None and not geometry['prefix_cantilever_pass']:
        issues.append('overextended')
    if require_shape:
        issues.extend("shape_proxy:" + issue for issue in proxy["issues"])
    return {"pass": not issues, "issues": issues, "geometry": geometry, "shape_proxy": proxy,
            "full_physics": False, "semantic_verified": False}


def quality_key(check):
    """Lexicographic: valid completion > connectivity > cues > prefix support."""
    geom = check["geometry"]
    sizes = geom["component_sizes"]
    ratio = sizes[0] / geom["bricks"] if sizes else 0
    return (int(check["pass"]), int(geom["ground_reachable"]), ratio,
            check["shape_proxy"]["score"], int(geom["prefix_support_pass"]),
            geom["mean_support_fraction"], -len(check["issues"]), -geom["components"])


def config_fingerprint(cfg):
    return hashlib.sha256(json.dumps(asdict(cfg), sort_keys=True).encode()).hexdigest()
