from __future__ import annotations

import json
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


def _parse_color(hex_color: str) -> tuple[float, float, float]:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return r, g, b


def _spawn_entities(model) -> List[EntityState]:
    entities_by_id = {e.id: e for e in model.systems.entities}
    rng = __import__("random").Random(model.meta.seed)
    states: List[EntityState] = []
    width = model.scene.canvas.width
    height = model.scene.canvas.height
    cx, cy = width / 2, height / 2

    for spawn in model.systems.spawns:
        spec = entities_by_id[spawn.entity_id]
        size = spec.size["value"] if isinstance(spec.size, dict) else float(spec.size)
        dist = spawn.distribution.type
        params = spawn.distribution.params or {}
        for i in range(spawn.count):
            if dist == "center":
                x, y = cx, cy
                angle = None
            elif dist == "random":
                x, y = rng.random() * width, rng.random() * height
                angle = None
            elif dist == "grid":
                cols = max(1, int(params.get("cols", 1)))
                rows = max(1, int(params.get("rows", 1)))
                gx = i % cols
                gy = i // cols
                x = (gx + 0.5) * (width / cols)
                y = (gy + 0.5) * (height / rows)
                angle = None
            elif dist == "orbit":
                radius = float(params.get("radius", 100))
                angle = (2 * math.pi / max(1, spawn.count)) * i
                x = cx + math.cos(angle) * radius
                y = cy + math.sin(angle) * radius
            else:
                raise ValueError(f"Unsupported distribution: {dist}")

            states.append(
                EntityState(
                    entity_id=spec.id,
                    shape=spec.shape,
                    size=size,
                    color=spec.color,
                    x=x,
                    y=y,
                    angle=angle,
                )
            )

    return states


def _apply_orbit(states: List[EntityState], model, dt: float) -> None:
    width = model.scene.canvas.width
    height = model.scene.canvas.height
    cx, cy = width / 2, height / 2
    for rule in model.systems.rules:
        if rule.type != "orbit":
            continue
        speed = float(rule.params.get("speed", 1.0))
        for ent in states:
            if ent.entity_id != rule.applies_to:
                continue
            if ent.angle is None:
                ent.angle = 0.0
            ent.angle += speed * dt
            radius = math.hypot(ent.x - cx, ent.y - cy)
            ent.x = cx + math.cos(ent.angle) * radius
            ent.y = cy + math.sin(ent.angle) * radius
            ent.vx = -math.sin(ent.angle) * speed * radius
            ent.vy = math.cos(ent.angle) * speed * radius


def _apply_attract_repel(states: List[EntityState], model, dt: float) -> None:
    rules = [r for r in model.systems.rules if r.type in {"attract", "repel"}]
    if not rules:
        return
    for rule in rules:
        strength = float(rule.params.get("strength", 1.0))
        min_dist = float(rule.params.get("min_dist", 4.0))
        max_dist = float(rule.params.get("max_dist", 500.0))
        if rule.type == "repel":
            strength = -strength
        for i, a in enumerate(states):
            if a.entity_id != rule.applies_to:
                continue
            for j, b in enumerate(states):
                if i == j:
                    continue
                dx = b.x - a.x
                dy = b.y - a.y
                dist = math.hypot(dx, dy)
                if dist < min_dist or dist > max_dist:
                    continue
                nx = dx / dist
                ny = dy / dist
                force = strength / (dist * dist)
                a.vx += nx * force * dt
                a.vy += ny * force * dt


def _apply_split(states: List[EntityState], model, dt: float, rng) -> List[EntityState]:
    for rule in model.systems.rules:
        if rule.type != "split":
            continue
        angle_threshold = float(rule.params.get("angle_threshold_deg", 45))
        into = int(rule.params.get("into", 2))
        speed_mult = float(rule.params.get("speed_multiplier", 1.0))
        new_states: List[EntityState] = []
        used = set()
        for i, a in enumerate(states):
            for j, b in enumerate(states):
                if i >= j:
                    continue
                if a.entity_id != rule.applies_to or b.entity_id != rule.applies_to:
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
                for k in range(into):
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
                        )
                    )
        if used:
            states = [s for idx, s in enumerate(states) if idx not in used]
            states.extend(new_states)
    return states


def _apply_merge(states: List[EntityState], model) -> List[EntityState]:
    for rule in model.systems.rules:
        if rule.type != "merge":
            continue
        distance = float(rule.params.get("distance", 12.0))
        size_factor = float(rule.params.get("size_factor", 0.5))
        new_states: List[EntityState] = []
        used = set()
        for i, a in enumerate(states):
            if a.entity_id != rule.applies_to or i in used:
                continue
            for j, b in enumerate(states):
                if j <= i or j in used:
                    continue
                if b.entity_id != rule.applies_to:
                    continue
                if math.hypot(a.x - b.x, a.y - b.y) > distance:
                    continue
                used.update({i, j})
                new_states.append(
                    EntityState(
                        entity_id=a.entity_id,
                        shape=a.shape,
                        size=max(2.0, (a.size + b.size) * size_factor),
                        color=a.color,
                        x=(a.x + b.x) / 2,
                        y=(a.y + b.y) / 2,
                        vx=(a.vx + b.vx) / 2,
                        vy=(a.vy + b.vy) / 2,
                    )
                )
                break
        if used:
            states = [s for idx, s in enumerate(states) if idx not in used]
            states.extend(new_states)
    return states


def _apply_decay(states: List[EntityState], model, dt: float) -> List[EntityState]:
    for rule in model.systems.rules:
        if rule.type != "decay":
            continue
        rate = float(rule.params.get("rate", 0.1))
        min_size = float(rule.params.get("min_size", 2.0))
        for ent in states:
            if ent.entity_id != rule.applies_to:
                continue
            ent.size = max(0.0, ent.size - rate * dt)
        states = [s for s in states if s.size >= min_size]
    return states


def _apply_memory(states: List[EntityState], model, dt: float, memory: MemoryGrid) -> None:
    for rule in model.systems.rules:
        if rule.type != "memory":
            continue
        decay = float(rule.params.get("decay", 0.01))
        influence = float(rule.params.get("influence", 1.0))
        memory.decay(decay * dt)
        width = model.scene.canvas.width
        height = model.scene.canvas.height
        cell_w = width / memory.cols
        cell_h = height / memory.rows
        for ent in states:
            if ent.entity_id != rule.applies_to:
                continue
            gx = int(ent.x / cell_w)
            gy = int(ent.y / cell_h)
            memory.mark(gx, gy, 1.0)
            gx = min(memory.cols - 1, max(0, gx))
            gy = min(memory.rows - 1, max(0, gy))
            dx, dy = memory.sample_gradient(gx, gy)
            ent.vx += dx * influence * dt
            ent.vy += dy * influence * dt


def _apply_fsm(model, fsm_state: FSMState, current_time_s: float) -> FSMState:
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
    return fsm_state


def _apply_move(states: List[EntityState], model, dt: float) -> None:
    for rule in model.systems.rules:
        if rule.type != "move":
            continue
        speed = float(rule.params.get("speed", 0.0))
        direction = rule.params.get("direction", [1.0, 0.0])
        dx, dy = float(direction[0]), float(direction[1])
        length = math.hypot(dx, dy) or 1.0
        for ent in states:
            if ent.entity_id != rule.applies_to:
                continue
            ent.vx = (dx / length) * speed
            ent.vy = (dy / length) * speed

    for ent in states:
        ent.x += ent.vx * dt
        ent.y += ent.vy * dt


def render_dsl(dsl_path: str | Path, out_dir: str | Path, out_video: str | Path) -> Path:
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
    fsm_state = None
    if model.systems.fsm is not None:
        fsm_state = FSMState(name=model.systems.fsm.initial, entered_at_s=0.0)
    memory = MemoryGrid.create(
        cols=max(1, int(model.scene.canvas.width / 16)),
        rows=max(1, int(model.scene.canvas.height / 16)),
    )
    for frame in range(frames):
        current_time = frame * dt
        if fsm_state is not None:
            fsm_state = _apply_fsm(model, fsm_state, current_time)
        _apply_orbit(states, model, dt)
        _apply_attract_repel(states, model, dt)
        _apply_move(states, model, dt)
        states = _apply_split(states, model, dt, rng)
        states = _apply_merge(states, model)
        states = _apply_decay(states, model, dt)
        _apply_memory(states, model, dt, memory)

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


def _encode_video(out_dir: Path, fps: int, out_video: Path) -> None:
    ffmpeg_bin = "/opt/homebrew/bin/ffmpeg"
    if not Path(ffmpeg_bin).exists():
        ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg_bin,
        "-y",
        "-r",
        str(fps),
        "-i",
        str(out_dir / "frame_%05d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(out_video),
    ]
    subprocess.run(cmd, check=True)


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
