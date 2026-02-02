from __future__ import annotations

import json
import os
import math
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import shutil

import cairo

from dsl.validate import validate_file


@dataclass
class EntityState:
    entity_id: str
    shape: str
    size: float
    color: str
    x: float
    y: float
    tags: List[str] = field(default_factory=list)
    vx: float = 0.0
    vy: float = 0.0
    angle: Optional[float] = None


@dataclass
class RenderConfig:
    out_dir: Path
    out_video: Path
    design_system_version: str = "mvp-0"
    renderer_version: str = "cairo-mvp-0"


@dataclass
class FSMState:
    name: str
    entered_at_s: float = 0.0


@dataclass
class MemoryGrid:
    cols: int
    rows: int
    memory: List[List[float]] = field(default_factory=list)

    @classmethod
    def create(cls, cols: int, rows: int) -> "MemoryGrid":
        grid = cls(cols=cols, rows=rows)
        grid.memory = [[0.0 for _ in range(cols)] for _ in range(rows)]
        return grid

    def decay(self, rate: float) -> None:
        for y in range(self.rows):
            for x in range(self.cols):
                self.memory[y][x] = max(0.0, self.memory[y][x] - rate)

    def mark(self, x: int, y: int, value: float) -> None:
        if 0 <= x < self.cols and 0 <= y < self.rows:
            self.memory[y][x] = min(1.0, max(self.memory[y][x], value))

    def sample_gradient(self, x: int, y: int) -> tuple[float, float]:
        # Central difference gradient
        left = self.memory[y][x - 1] if x > 0 else self.memory[y][x]
        right = self.memory[y][x + 1] if x < self.cols - 1 else self.memory[y][x]
        up = self.memory[y - 1][x] if y > 0 else self.memory[y][x]
        down = self.memory[y + 1][x] if y < self.rows - 1 else self.memory[y][x]
        return (right - left, down - up)


@dataclass
class EmitterState:
    id: str
    entity_id: str
    rate_per_s: float
    distribution: object
    params: Dict[str, object]
    start_s: float
    end_s: Optional[float]
    limit: Optional[int]
    emitted: int = 0
    carry: float = 0.0


@dataclass
class TerminationSpec:
    type: str
    params: Dict[str, object]


def _parse_color(hex_color: str) -> tuple[float, float, float]:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return r, g, b


def _matches_selector(ent: EntityState, selector: str) -> bool:
    if selector in {"*", "all"}:
        return True
    if selector.startswith("tag:"):
        tag_name = selector.split(":", 1)[1]
        return tag_name in ent.tags
    return ent.entity_id == selector


def _entities_for_selector(states: List[EntityState], selector: str) -> List[EntityState]:
    return [ent for ent in states if _matches_selector(ent, selector)]


def _nearest_entity(
    source: EntityState, candidates: List[EntityState]
) -> Optional[EntityState]:
    filtered = [c for c in candidates if c is not source]
    if not filtered:
        return None
    return min(filtered, key=lambda ent: math.hypot(ent.x - source.x, ent.y - source.y))


def _resolve_target_point(
    source: EntityState,
    states: List[EntityState],
    target: object,
    fallback: tuple[float, float],
) -> Optional[tuple[float, float]]:
    if isinstance(target, dict):
        try:
            return (float(target["x"]), float(target["y"]))
        except (KeyError, TypeError, ValueError):
            return None
    if isinstance(target, str):
        candidates = _entities_for_selector(states, target)
        nearest = _nearest_entity(source, candidates)
        if nearest is None:
            return None
        return (nearest.x, nearest.y)
    return fallback


def _spawn_entities(model) -> List[EntityState]:
    entities_by_id = {e.id: e for e in model.systems.entities}
    rng = __import__("random").Random(model.meta.seed)
    states: List[EntityState] = []
    width = model.scene.canvas.width
    height = model.scene.canvas.height
    cx, cy = width / 2, height / 2

    for spawn in model.systems.spawns:
        spec = entities_by_id[spawn.entity_id]
        size = _pick_size(spec.size, rng)
        dist = spawn.distribution.type
        params = spawn.distribution.params or {}
        for i in range(spawn.count):
            x, y, angle = _spawn_point(dist, params, i, spawn.count, rng, width, height, cx, cy)
            states.append(
                EntityState(
                    entity_id=spec.id,
                    shape=spec.shape,
                    size=size,
                    color=spec.color,
                    x=x,
                    y=y,
                    tags=list(spec.tags or []),
                    angle=angle,
                )
            )

    return states


def _spawn_point(
    dist: str,
    params: Dict[str, object],
    index: int,
    count: int,
    rng,
    width: float,
    height: float,
    cx: float,
    cy: float,
) -> tuple[float, float, Optional[float]]:
    if dist == "center":
        return (cx, cy, None)
    if dist == "random":
        padding = float(params.get("padding", 0.0))
        x = rng.random() * (width - 2 * padding) + padding
        y = rng.random() * (height - 2 * padding) + padding
        return (x, y, None)
    if dist == "grid":
        cols = max(1, int(params.get("cols", 1)))
        rows = max(1, int(params.get("rows", 1)))
        gx = index % cols
        gy = index // cols
        x = (gx + 0.5) * (width / cols)
        y = (gy + 0.5) * (height / rows)
        return (x, y, None)
    if dist == "orbit":
        radius = float(params.get("radius", 100))
        angle = (2 * math.pi / max(1, count)) * index
        x = cx + math.cos(angle) * radius
        y = cy + math.sin(angle) * radius
        return (x, y, angle)
    raise ValueError(f"Unsupported distribution: {dist}")


def _apply_orbit(states: List[EntityState], model, dt: float, rule) -> None:
    width = model.scene.canvas.width
    height = model.scene.canvas.height
    cx, cy = width / 2, height / 2
    speed = float(rule.params.get("speed", 1.0))
    for ent in states:
        if not _matches_selector(ent, rule.applies_to):
            continue
        if ent.angle is None:
            ent.angle = 0.0
        center_param = rule.params.get("center")
        center = _resolve_target_point(ent, states, center_param, (cx, cy))
        if center is None:
            continue
        center_x, center_y = center
        ent.angle += speed * dt
        radius = math.hypot(ent.x - center_x, ent.y - center_y)
        ent.x = center_x + math.cos(ent.angle) * radius
        ent.y = center_y + math.sin(ent.angle) * radius
        ent.vx = -math.sin(ent.angle) * speed * radius
        ent.vy = math.cos(ent.angle) * speed * radius


def _apply_attract_repel(states: List[EntityState], model, dt: float, rule) -> None:
    strength = float(rule.params.get("strength", 1.0))
    radius = float(rule.params.get("radius", float("inf")))
    falloff = str(rule.params.get("falloff", "inverse_square"))
    if rule.type == "repel":
        strength = -strength
    for a in states:
        if not _matches_selector(a, rule.applies_to):
            continue
        target_param = rule.params.get("target")
        target = _resolve_target_point(a, states, target_param, None)
        if target is None:
            continue
        tx, ty = target
        dx = tx - a.x
        dy = ty - a.y
        dist = math.hypot(dx, dy)
        if dist == 0 or dist > radius:
            continue
        nx = dx / dist
        ny = dy / dist
        if falloff == "linear":
            force = strength / max(1.0, dist)
        else:
            force = strength / (dist * dist)
        a.vx += nx * force * dt
        a.vy += ny * force * dt


def _apply_split(states: List[EntityState], model, dt: float, rng, rule) -> List[EntityState]:
    angle_threshold = float(rule.params.get("angle_threshold_deg", 45))
    into = int(rule.params.get("into", 2))
    speed_mult = float(rule.params.get("speed_multiplier", 1.0))
    new_states: List[EntityState] = []
    used = set()
    for i, a in enumerate(states):
        for j, b in enumerate(states):
            if i >= j:
                continue
            if not _matches_selector(a, rule.applies_to) or not _matches_selector(
                b, rule.applies_to
            ):
                continue
            if (i in used) or (j in used):
                continue
            dx = a.x - b.x
            dy = a.y - b.y
            if math.hypot(dx, dy) > (a.size + b.size):
                continue
            # angle between velocity vectors
            av = (a.vx, a.vy)
            bv = (b.vx, b.vy)
            denom = (math.hypot(*av) * math.hypot(*bv)) or 1.0
            cos_angle = max(-1.0, min(1.0, (av[0] * bv[0] + av[1] * bv[1]) / denom))
            angle = math.degrees(math.acos(cos_angle))
            if angle < angle_threshold:
                continue
            used.update({i, j})
            base_x = (a.x + b.x) / 2
            base_y = (a.y + b.y) / 2
            for _ in range(into):
                theta = rng.random() * 2 * math.pi
                speed = math.hypot(a.vx, a.vy) * speed_mult
                new_states.append(
                    EntityState(
                        entity_id=a.entity_id,
                        shape=a.shape,
                        size=max(2.0, a.size * 0.6),
                        color=a.color,
                        x=base_x,
                        y=base_y,
                        vx=math.cos(theta) * speed,
                        vy=math.sin(theta) * speed,
                        tags=list(a.tags),
                    )
                )
    if used:
        states = [s for idx, s in enumerate(states) if idx not in used]
        states.extend(new_states)
    return states


def _apply_merge(states: List[EntityState], model, rule) -> List[EntityState]:
    distance = float(rule.params.get("distance", 12.0))
    mode = str(rule.params.get("mode", "largest"))
    new_states: List[EntityState] = []
    used = set()
    for i, a in enumerate(states):
        if not _matches_selector(a, rule.applies_to) or i in used:
            continue
        for j, b in enumerate(states):
            if j <= i or j in used:
                continue
            if not _matches_selector(b, rule.applies_to):
                continue
            if math.hypot(a.x - b.x, a.y - b.y) > distance:
                continue
            used.update({i, j})
            if mode == "average":
                size = max(2.0, (a.size + b.size) / 2)
                x = (a.x + b.x) / 2
                y = (a.y + b.y) / 2
                vx = (a.vx + b.vx) / 2
                vy = (a.vy + b.vy) / 2
            else:
                bigger = a if a.size >= b.size else b
                size = max(2.0, bigger.size)
                x = bigger.x
                y = bigger.y
                vx = bigger.vx
                vy = bigger.vy
            new_states.append(
                EntityState(
                    entity_id=a.entity_id,
                    shape=a.shape,
                    size=size,
                    color=a.color,
                    x=x,
                    y=y,
                    vx=vx,
                    vy=vy,
                    tags=list(a.tags),
                )
            )
            break
    if used:
        states = [s for idx, s in enumerate(states) if idx not in used]
        states.extend(new_states)
    return states


def _apply_decay(states: List[EntityState], model, dt: float, rule) -> List[EntityState]:
    rate = float(rule.params.get("rate_per_s", 0.1))
    min_size = 0.0
    for ent in states:
        if not _matches_selector(ent, rule.applies_to):
            continue
        ent.size = max(0.0, ent.size - rate * dt)
    states = [s for s in states if s.size >= min_size]
    return states


def _apply_memory(states: List[EntityState], model, dt: float, memory: MemoryGrid, rule) -> None:
    decay = float(rule.params.get("decay", 0.01))
    influence = float(rule.params.get("influence", 1.0))
    memory.decay(decay * dt)
    width = model.scene.canvas.width
    height = model.scene.canvas.height
    cell_w = width / memory.cols
    cell_h = height / memory.rows
    for ent in states:
        if not _matches_selector(ent, rule.applies_to):
            continue
        gx = int(ent.x / cell_w)
        gy = int(ent.y / cell_h)
        memory.mark(gx, gy, 1.0)
        gx = min(memory.cols - 1, max(0, gx))
        gy = min(memory.rows - 1, max(0, gy))
        dx, dy = memory.sample_gradient(gx, gy)
        ent.vx += dx * influence * dt
        ent.vy += dy * influence * dt


def _apply_fsm(model, fsm_state: FSMState, current_time_s: float, states) -> FSMState:
    fsm = model.systems.fsm
    if fsm is None:
        return fsm_state
    transitions = [t for t in fsm.transitions if t.from_ == fsm_state.name]
    if not transitions:
        return fsm_state
    transitions.sort(key=lambda t: t.priority or 0, reverse=True)

    for t in transitions:
        when = t.when
        if when.type == "time":
            at_s = float(when.params.get("at_s", 0))
            if current_time_s >= at_s:
                return FSMState(name=t.to, entered_at_s=current_time_s)
        if when.type == "metric":
            if _check_metric(when.params, states, current_time_s):
                return FSMState(name=t.to, entered_at_s=current_time_s)
    return fsm_state


def _apply_emitters(
    states: List[EntityState],
    emitters: List[EmitterState],
    model,
    current_time_s: float,
    dt: float,
    rng,
) -> None:
    if not emitters:
        return
    entities_by_id = {e.id: e for e in model.systems.entities}
    width = model.scene.canvas.width
    height = model.scene.canvas.height
    cx, cy = width / 2, height / 2
    for emitter in emitters:
        if current_time_s < emitter.start_s:
            continue
        if emitter.end_s is not None and current_time_s > emitter.end_s:
            continue
        if emitter.limit is not None and emitter.emitted >= emitter.limit:
            continue
        emitter.carry += emitter.rate_per_s * dt
        spawn_count = int(emitter.carry)
        if spawn_count <= 0:
            continue
        emitter.carry -= spawn_count
        if emitter.limit is not None:
            remaining = max(0, emitter.limit - emitter.emitted)
            spawn_count = min(spawn_count, remaining)
        if spawn_count <= 0:
            continue
        spec = entities_by_id[emitter.entity_id]
        size = _pick_size(spec.size, rng)
        dist = emitter.distribution.type
        params = emitter.distribution.params or {}
        for i in range(spawn_count):
            x, y, angle = _spawn_point(
                dist, params, i, max(1, spawn_count), rng, width, height, cx, cy
            )
            states.append(
                EntityState(
                    entity_id=spec.id,
                    shape=spec.shape,
                    size=size,
                    color=spec.color,
                    x=x,
                    y=y,
                    tags=list(spec.tags or []),
                    angle=angle,
                )
            )
            states[-1].__dict__["canvas_width"] = width
            states[-1].__dict__["canvas_height"] = height
            emitter.emitted += 1


def _pick_size(size_spec, rng) -> float:
    if isinstance(size_spec, dict):
        if "value" in size_spec:
            return float(size_spec["value"])
        min_v = float(size_spec.get("min", 1.0))
        max_v = float(size_spec.get("max", min_v))
        if max_v < min_v:
            max_v = min_v
        distribution = size_spec.get("distribution", "uniform")
        if distribution == "normal":
            mu = (min_v + max_v) / 2
            sigma = (max_v - min_v) / 6 if max_v > min_v else 0.0
            value = rng.gauss(mu, sigma) if sigma > 0 else mu
            return max(min_v, min(max_v, value))
        return rng.uniform(min_v, max_v)
    return float(size_spec)


def _apply_bounds(states: List[EntityState], model) -> None:
    constraints = model.systems.constraints
    if constraints is None or constraints.bounds is None:
        return
    bounds = constraints.bounds
    width = model.scene.canvas.width
    height = model.scene.canvas.height
    padding = float(getattr(bounds, "padding", 0.0) or 0.0)
    left = padding
    top = padding
    right = width - padding
    bottom = height - padding
    btype = bounds.type
    restitution = float(getattr(bounds, "restitution", 1.0) or 1.0)

    for ent in states:
        radius = ent.size
        left_bound = left + radius
        right_bound = right - radius
        top_bound = top + radius
        bottom_bound = bottom - radius
        if btype == "clamp":
            ent.x = min(max(ent.x, left_bound), right_bound)
            ent.y = min(max(ent.y, top_bound), bottom_bound)
        elif btype == "wrap":
            if ent.x < left_bound:
                ent.x = right_bound
            elif ent.x > right_bound:
                ent.x = left_bound
            if ent.y < top_bound:
                ent.y = bottom_bound
            elif ent.y > bottom_bound:
                ent.y = top_bound
        elif btype == "bounce":
            if ent.x < left_bound:
                ent.x = left_bound
                ent.vx = abs(ent.vx) * restitution
            elif ent.x > right_bound:
                ent.x = right_bound
                ent.vx = -abs(ent.vx) * restitution
            if ent.y < top_bound:
                ent.y = top_bound
                ent.vy = abs(ent.vy) * restitution
            elif ent.y > bottom_bound:
                ent.y = bottom_bound
                ent.vy = -abs(ent.vy) * restitution


def _apply_forces(states: List[EntityState], model, dt: float, rng) -> None:
    forces = model.systems.forces
    if forces is None:
        return
    gravity = forces.gravity
    gx = 0.0
    gy = 0.0
    if isinstance(gravity, dict):
        gx = float(gravity.get("x", 0.0))
        gy = float(gravity.get("y", 0.0))
    elif gravity is not None:
        gy = float(gravity)
    for ent in states:
        ent.vx += gx * dt
        ent.vy += gy * dt

    if forces.noise is not None:
        strength = float(forces.noise.get("strength", 0.0))
        scale = float(forces.noise.get("scale", 1.0))
        seed = forces.noise.get("seed")
        if strength <= 0 or scale <= 0:
            return
        noise_rng = rng
        if seed is not None:
            noise_rng = __import__("random").Random(int(seed))
        for ent in states:
            ent.vx += (noise_rng.random() * 2 - 1) * strength * scale * dt
            ent.vy += (noise_rng.random() * 2 - 1) * strength * scale * dt


def _build_termination(model) -> Optional[TerminationSpec]:
    term = model.termination
    if term is None or term.condition is None:
        return None
    if term.condition.type != "metric":
        return None
    return TerminationSpec(type="metric", params=term.condition.params)


def _check_metric(params: Dict[str, object], states, current_time_s: float) -> bool:
    name = params.get("name")
    op = params.get("op")
    value = float(params.get("value", 0))
    if states is None:
        return False
    if name == "population":
        metric = len(states)
    elif name == "entropy":
        metric = len(states)
    elif name == "coverage":
        metric = _coverage_metric(states, params.get("window_s"))
    elif name == "stability":
        eps = float(params.get("stability_eps", 1e-3))
        metric = _stability_metric(states, params.get("window_s"), eps)
    else:
        return False
    if op == ">":
        return metric > value
    if op == ">=":
        return metric >= value
    if op == "<":
        return metric < value
    if op == "<=":
        return metric <= value
    if op == "==":
        return metric == value
    return False


def _check_termination(
    termination: TerminationSpec, states: List[EntityState], current_time_s: float
) -> bool:
    if termination.type == "metric":
        return _check_metric(termination.params, states, current_time_s)
    return False


def _coverage_metric(states: List[EntityState], window_s: object) -> float:
    # Approximate coverage as sum of circle areas / canvas area
    if not states:
        return 0.0
    width = states[0].__dict__.get("canvas_width", None)
    height = states[0].__dict__.get("canvas_height", None)
    if width is None or height is None:
        return 0.0
    total_area = float(width) * float(height)
    covered = 0.0
    for ent in states:
        covered += math.pi * (ent.size ** 2)
    return min(1.0, covered / total_area) if total_area > 0 else 0.0


def _stability_metric(states: List[EntityState], window_s: object, eps: float = 1e-3) -> float:
    # Approximate stability as proportion of low-velocity entities
    if not states:
        return 1.0
    stable = 0
    for ent in states:
        if math.hypot(ent.vx, ent.vy) <= eps:
            stable += 1
    return stable / max(1, len(states))


def _apply_interactions(states: List[EntityState], model, dt: float) -> None:
    interactions = model.systems.interactions
    if interactions is None:
        return
    rng = __import__("random").Random(model.meta.seed)
    to_remove: List[EntityState] = []
    for pair in interactions.pairs:
        rule = pair.rule
        for a in states:
            if not _matches_selector(a, pair.a):
                continue
            for b in states:
                if a is b or not _matches_selector(b, pair.b):
                    continue
                if rule.when is not None:
                    distance = rule.when.get("distance_lte")
                    probability = rule.when.get("probability")
                    if distance is not None:
                        if math.hypot(a.x - b.x, a.y - b.y) > float(distance):
                            continue
                    if probability is not None:
                        if rng.random() > float(probability):
                            continue
                # Support repel/attract interactions for now
                if rule.type in {"repel", "attract"}:
                    strength = float(rule.params.get("strength", 1.0))
                    if rule.type == "repel":
                        strength = -strength
                    dx = b.x - a.x
                    dy = b.y - a.y
                    dist = math.hypot(dx, dy) or 1.0
                    nx = dx / dist
                    ny = dy / dist
                    a.vx += nx * strength * dt
                    a.vy += ny * strength * dt
                elif rule.type == "merge":
                    # merge: collapse b into a
                    mode = str(rule.params.get("mode", "largest"))
                    if mode == "average":
                        size = max(2.0, (a.size + b.size) / 2)
                        a.x = (a.x + b.x) / 2
                        a.y = (a.y + b.y) / 2
                        a.vx = (a.vx + b.vx) / 2
                        a.vy = (a.vy + b.vy) / 2
                    else:
                        size = max(2.0, max(a.size, b.size))
                        if b.size > a.size:
                            a.x, a.y = b.x, b.y
                            a.vx, a.vy = b.vx, b.vy
                    a.size = size
                    to_remove.append(b)
                elif rule.type == "split":
                    into = int(rule.params.get("into", 2))
                    angle_threshold = float(rule.params.get("angle_threshold_deg", 0.0))
                    speed_mult = float(rule.params.get("speed_multiplier", 1.0))
                    av = (a.vx, a.vy)
                    bv = (b.vx, b.vy)
                    denom = (math.hypot(*av) * math.hypot(*bv)) or 1.0
                    cos_angle = max(-1.0, min(1.0, (av[0] * bv[0] + av[1] * bv[1]) / denom))
                    angle = math.degrees(math.acos(cos_angle))
                    if angle < angle_threshold:
                        continue
                    for _ in range(into):
                        theta = rng.random() * 2 * math.pi
                        speed = math.hypot(a.vx, a.vy) * speed_mult
                        states.append(
                            EntityState(
                                entity_id=a.entity_id,
                                shape=a.shape,
                                size=max(2.0, a.size * 0.6),
                                color=a.color,
                                x=a.x,
                                y=a.y,
                                vx=math.cos(theta) * speed,
                                vy=math.sin(theta) * speed,
                                tags=list(a.tags),
                            )
                        )
    if to_remove:
        remaining = [s for s in states if s not in to_remove]
        states[:] = remaining


def _apply_move(states: List[EntityState], model, dt: float, rule) -> None:
    speed = float(rule.params.get("speed", 0.0))
    direction = rule.params.get("direction", [1.0, 0.0])
    dx, dy = float(direction[0]), float(direction[1])
    length = math.hypot(dx, dy) or 1.0
    for ent in states:
        if not _matches_selector(ent, rule.applies_to):
            continue
        ent.vx = (dx / length) * speed
        ent.vy = (dy / length) * speed

    for ent in states:
        ent.x += ent.vx * dt
        ent.y += ent.vy * dt


def render_dsl(dsl_path: str | Path, out_dir: str | Path, out_video: str | Path) -> Path:
    dsl_path = Path(dsl_path).resolve()
    out_dir = Path(out_dir).resolve()
    out_video = Path(out_video).resolve()
    model = validate_file(dsl_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_video = Path(out_video)

    rng = __import__("random").Random(model.meta.seed)
    width = model.scene.canvas.width
    height = model.scene.canvas.height
    fps = model.scene.canvas.fps
    dt = 1.0 / fps
    frames = int(model.scene.canvas.duration_s * fps)

    _warn_on_unsupported(model)
    states = _spawn_entities(model)
    for ent in states:
        ent.__dict__["canvas_width"] = width
        ent.__dict__["canvas_height"] = height
    fsm_state = None
    if model.systems.fsm is not None:
        fsm_state = FSMState(name=model.systems.fsm.initial, entered_at_s=0.0)
    termination = _build_termination(model)
    memory = MemoryGrid.create(
        cols=max(1, int(model.scene.canvas.width / 16)),
        rows=max(1, int(model.scene.canvas.height / 16)),
    )
    emitters: List[EmitterState] = []
    if model.systems.emitters:
        for emitter in model.systems.emitters:
            emitters.append(
                EmitterState(
                    id=emitter.id,
                    entity_id=emitter.entity_id,
                    rate_per_s=float(emitter.rate_per_s),
                    distribution=emitter.distribution,
                    params=emitter.params or {},
                    start_s=float(emitter.start_s or 0.0),
                    end_s=float(emitter.end_s) if emitter.end_s is not None else None,
                    limit=emitter.limit,
                )
            )
    for frame in range(frames):
        current_time = frame * dt
        # 1) Forces (placeholder; implement in dedicated step)
        _apply_forces(states, model, dt, rng)
        # 2) Rules (ordered by DSL list)
        for rule in model.systems.rules:
            if rule.type == "orbit":
                _apply_orbit(states, model, dt, rule)
            elif rule.type in {"attract", "repel"}:
                _apply_attract_repel(states, model, dt, rule)
            elif rule.type == "move":
                _apply_move(states, model, dt, rule)
            elif rule.type == "split":
                states = _apply_split(states, model, dt, rng, rule)
            elif rule.type == "merge":
                states = _apply_merge(states, model, rule)
            elif rule.type == "decay":
                states = _apply_decay(states, model, dt, rule)
            elif rule.type == "memory":
                _apply_memory(states, model, dt, memory, rule)
        _apply_emitters(
            states,
            emitters,
            model,
            current_time,
            dt,
            rng,
        )
        _apply_interactions(states, model, dt)
        _apply_bounds(states, model)
        # 5) FSM transitions
        if fsm_state is not None:
            fsm_state = _apply_fsm(model, fsm_state, current_time, states)
        if termination and _check_termination(termination, states, current_time):
            frames = frame + 1
            break

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(surface)
        bg = _parse_color(model.scene.background)
        ctx.set_source_rgb(*bg)
        ctx.rectangle(0, 0, width, height)
        ctx.fill()

        for ent in states:
            r, g, b = _parse_color(ent.color)
            ctx.set_source_rgb(r, g, b)
            if ent.shape == "circle":
                ctx.arc(ent.x, ent.y, ent.size, 0, 2 * math.pi)
                ctx.fill()
            elif ent.shape == "square":
                ctx.rectangle(ent.x - ent.size, ent.y - ent.size, ent.size * 2, ent.size * 2)
                ctx.fill()

        frame_path = out_dir / f"frame_{frame:05d}.png"
        surface.write_to_png(str(frame_path))

    _encode_video(out_dir, fps, out_video)
    _write_metadata(model, out_dir)
    return out_video


def _warn_on_unsupported(model) -> None:
    supported_rules = {
        "orbit",
        "split",
        "move",
        "attract",
        "repel",
        "merge",
        "decay",
        "memory",
    }
    for rule in model.systems.rules:
        if rule.type not in supported_rules:
            print(f"[renderer] WARN unsupported rule.type: {rule.type}")
    if model.systems.fsm is not None:
        supported_fsm_when = {"time"}
        for t in model.systems.fsm.transitions:
            if t.when.type not in supported_fsm_when:
                print(f"[renderer] WARN unsupported fsm.when.type: {t.when.type}")
    # forces now supported
    # interactions now supported (repel/attract only)
    # constraints now supported


def _encode_video(out_dir: Path, fps: int, out_video: Path) -> None:
    ffmpeg_bin = "/opt/homebrew/bin/ffmpeg"
    if not Path(ffmpeg_bin).exists():
        ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    try:
        timeout_s = int(os.getenv("FFMPEG_TIMEOUT_S", "300"))
    except ValueError:
        timeout_s = 300
    cmd = [
        ffmpeg_bin,
        "-y",
        "-nostdin",
        "-r",
        str(fps),
        "-i",
        str((out_dir / "frame_%05d.png").resolve()),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(out_video),
    ]
    subprocess.run(cmd, check=True, timeout=timeout_s)
    if not out_video.exists() or out_video.stat().st_size == 0:
        raise RuntimeError(f"ffmpeg output missing or empty: {out_video}")


def _write_metadata(model, out_dir: Path) -> None:
    meta = {
        "seed": model.meta.seed,
        "dsl_version": model.dsl_version,
        "design_system_version": "mvp-0",
        "renderer_version": "cairo-mvp-0",
        "canvas": {
            "width": model.scene.canvas.width,
            "height": model.scene.canvas.height,
            "fps": model.scene.canvas.fps,
            "duration_s": model.scene.canvas.duration_s,
        },
        "palette": model.scene.palette,
    }
    (out_dir / "metadata.json").write_text(json.dumps(meta, indent=2))
