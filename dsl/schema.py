from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Canvas(BaseModel):
    width: int
    height: int
    fps: int
    duration_s: float

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_canvas(self) -> "Canvas":
        if self.width <= 0 or self.height <= 0:
            raise ValueError("scene.canvas width/height must be > 0")
        if self.fps <= 0:
            raise ValueError("scene.canvas fps must be > 0")
        if self.duration_s <= 0:
            raise ValueError("scene.canvas duration_s must be > 0")
        return self


class Scene(BaseModel):
    canvas: Canvas
    palette: List[str]
    background: str
    time: Optional[Dict[str, float]] = None

    model_config = ConfigDict(extra="forbid")


class Meta(BaseModel):
    id: str
    title: str
    seed: int
    tags: List[str] = Field(default_factory=list)
    attribution: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class Entity(BaseModel):
    id: str
    shape: Literal["circle", "square", "line", "triangle", "custom"]
    size: float | Dict[str, float]
    color: str
    mass: Optional[float] = 1.0
    render: Optional[Dict[str, object]] = None
    tags: Optional[List[str]] = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_size_and_render(self) -> "Entity":
        if isinstance(self.size, dict):
            if "min" not in self.size or "max" not in self.size:
                raise ValueError("entities.size object requires min and max")
            min_v = float(self.size["min"])
            max_v = float(self.size["max"])
            if min_v < 0 or max_v < 0 or max_v < min_v:
                raise ValueError("entities.size min/max must be >=0 and max>=min")
            dist = self.size.get("distribution")
            if dist is not None and dist not in {"uniform", "normal"}:
                raise ValueError("entities.size.distribution must be uniform or normal")

        if self.render is not None:
            opacity = self.render.get("opacity")
            if opacity is not None:
                if not (0.0 <= float(opacity) <= 1.0):
                    raise ValueError("entities.render.opacity must be 0..1")
            stroke = self.render.get("stroke")
            if stroke is not None:
                width = stroke.get("width")
                if width is None or float(width) < 0.0:
                    raise ValueError("entities.render.stroke.width must be >= 0")
                if "color" not in stroke:
                    raise ValueError("entities.render.stroke.color is required")
        if self.tags:
            seen = set()
            for tag in self.tags:
                if not isinstance(tag, str) or not tag.strip():
                    raise ValueError("entities.tags must be non-empty strings")
                if tag in seen:
                    raise ValueError("entities.tags must be unique per entity")
                seen.add(tag)
        return self


class Distribution(BaseModel):
    type: str
    params: Optional[Dict[str, object]] = None

    model_config = ConfigDict(extra="forbid")


class SpawnDistribution(BaseModel):
    type: Literal["center", "random", "grid", "orbit"]
    params: Optional[Dict[str, object]] = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_params(self) -> "SpawnDistribution":
        params = self.params or {}
        if self.type == "grid":
            if "cols" not in params or "rows" not in params:
                raise ValueError("distribution.grid requires cols and rows")
        if self.type == "orbit":
            if "radius" not in params:
                raise ValueError("distribution.orbit requires radius")
            if "speed" in params and float(params["speed"]) < 0.0:
                raise ValueError("distribution.orbit.speed must be >= 0")
        if self.type == "random":
            if "padding" in params and float(params["padding"]) < 0.0:
                raise ValueError("distribution.random.padding must be >= 0")
        return self


class Spawn(BaseModel):
    entity_id: str
    count: int
    distribution: SpawnDistribution

    model_config = ConfigDict(extra="forbid")


class Emitter(BaseModel):
    id: str
    entity_id: str
    rate_per_s: float
    distribution: SpawnDistribution
    params: Optional[Dict[str, object]] = None
    start_s: Optional[float] = 0.0
    end_s: Optional[float] = None
    limit: Optional[int] = None

    model_config = ConfigDict(extra="forbid")


class CollisionEmitter(BaseModel):
    id: str
    entity_id: str
    a: str
    b: str
    count: int = 1
    when: Optional[Dict[str, object]] = None
    cooldown_s: Optional[float] = 0.0
    scatter_radius: Optional[float] = 0.0
    limit: Optional[int] = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_collision_emitter(self) -> "CollisionEmitter":
        if int(self.count) <= 0:
            raise ValueError("collision_emitters.count must be >= 1")
        if self.cooldown_s is not None and float(self.cooldown_s) < 0.0:
            raise ValueError("collision_emitters.cooldown_s must be >= 0")
        if self.scatter_radius is not None and float(self.scatter_radius) < 0.0:
            raise ValueError("collision_emitters.scatter_radius must be >= 0")
        if self.limit is not None and int(self.limit) < 0:
            raise ValueError("collision_emitters.limit must be >= 0")
        if self.when is not None:
            distance = self.when.get("distance_lte")
            probability = self.when.get("probability")
            if distance is not None and float(distance) < 0.0:
                raise ValueError("collision_emitters.when.distance_lte must be >= 0")
            if probability is not None:
                if not (0.0 <= float(probability) <= 1.0):
                    raise ValueError("collision_emitters.when.probability must be 0..1")
        return self


class Rule(BaseModel):
    id: str
    type: str
    applies_to: str
    params: Dict[str, object]
    probability: Optional[float] = None

    model_config = ConfigDict(extra="forbid")

    _POINT_RULE_PARAMS = {
        "orbit": "center",
        "attract": "target",
        "repel": "target",
        "parametric_spiral_motion": "center",
    }

    _REQUIRED_PARAMS = {
        "move": ["speed"],
        "orbit": ["center", "speed"],
        "attract": ["target", "strength"],
        "repel": ["target", "strength"],
        "split": ["into", "angle_threshold_deg"],
        "merge": ["distance"],
        "decay": ["rate_per_s"],
        "parametric_spiral_motion": ["center", "angular_speed", "radial_speed"],
        "size_animation": ["rate_per_s"],
        "memory": ["decay", "influence"],
        "color_animation": ["colors", "rate_per_s"],
    }

    @model_validator(mode="after")
    def _validate_required_params(self) -> "Rule":
        required = self._REQUIRED_PARAMS.get(self.type)
        if required is None:
            raise ValueError(f"rule.type not supported: {self.type}")
        missing = [key for key in required if key not in self.params]
        if missing:
            missing_list = ", ".join(missing)
            raise ValueError(
                f"rule.params missing required keys for {self.type}: {missing_list}"
            )
        point_param = self._POINT_RULE_PARAMS.get(self.type)
        if point_param is not None:
            self._validate_point_param(point_param, self.params.get(point_param))
        if self.type == "size_animation":
            rate = self.params.get("rate_per_s")
            try:
                float(rate)
            except (TypeError, ValueError) as exc:
                raise ValueError("rule.params.rate_per_s must be numeric") from exc
            min_v = self.params.get("min")
            max_v = self.params.get("max")
            if min_v is not None:
                if float(min_v) < 0.0:
                    raise ValueError("rule.params.min must be >= 0")
            if max_v is not None:
                if float(max_v) < 0.0:
                    raise ValueError("rule.params.max must be >= 0")
            if min_v is not None and max_v is not None:
                if float(max_v) < float(min_v):
                    raise ValueError("rule.params.max must be >= rule.params.min")
            remove_on_limit = self.params.get("remove_on_limit")
            if remove_on_limit is not None and not isinstance(remove_on_limit, bool):
                raise ValueError("rule.params.remove_on_limit must be boolean")
        if self.type == "parametric_spiral_motion":
            angular = self.params.get("angular_speed")
            radial = self.params.get("radial_speed")
            try:
                float(angular)
                float(radial)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "rule.params.angular_speed and radial_speed must be numeric"
                ) from exc
            radius_min = self.params.get("radius_min")
            radius_max = self.params.get("radius_max")
            if radius_min is not None:
                if float(radius_min) < 0.0:
                    raise ValueError("rule.params.radius_min must be >= 0")
            if radius_max is not None:
                if float(radius_max) < 0.0:
                    raise ValueError("rule.params.radius_max must be >= 0")
            if radius_min is not None and radius_max is not None:
                if float(radius_max) < float(radius_min):
                    raise ValueError("rule.params.radius_max must be >= rule.params.radius_min")
        if self.type == "color_animation":
            colors = self.params.get("colors")
            if not isinstance(colors, list) or len(colors) < 2:
                raise ValueError("rule.params.colors must be a list with at least 2 colors")
            for color in colors:
                if not isinstance(color, str) or not color.startswith("#") or len(color) != 7:
                    raise ValueError("rule.params.colors must be hex #RRGGBB tokens")
            rate = self.params.get("rate_per_s")
            try:
                float(rate)
            except (TypeError, ValueError) as exc:
                raise ValueError("rule.params.rate_per_s must be numeric") from exc
            mode = self.params.get("mode")
            if mode is not None and mode not in {"step", "lerp"}:
                raise ValueError("rule.params.mode must be step or lerp")
            phase_offset = self.params.get("phase_offset")
            if phase_offset is not None:
                try:
                    float(phase_offset)
                except (TypeError, ValueError) as exc:
                    raise ValueError("rule.params.phase_offset must be numeric") from exc
        return self

    @staticmethod
    def _validate_point_param(name: str, value: object) -> None:
        if isinstance(value, str):
            if value in {"*", "all"}:
                return
            if value.startswith("tag:"):
                return
            return
        if isinstance(value, dict):
            if "x" not in value or "y" not in value:
                raise ValueError(f"rule.params.{name} must include x and y")
            try:
                float(value["x"])
                float(value["y"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"rule.params.{name} must be numeric x/y") from exc
            return
        raise ValueError(f"rule.params.{name} must be selector string or point object")


class FSMTransitionWhen(BaseModel):
    type: str
    params: Dict[str, object]

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_metric_params(self) -> "FSMTransitionWhen":
        if self.type == "metric":
            name = self.params.get("name")
            op = self.params.get("op")
            value = self.params.get("value")
            window_s = self.params.get("window_s")
            sample_every_s = self.params.get("sample_every_s")
            if name is None or op is None or value is None:
                raise ValueError("fsm.when.metric requires name/op/value")
            if op not in {">", ">=", "<", "<=", "=="}:
                raise ValueError("fsm.when.metric.op must be one of >, >=, <, <=, ==")
            if name not in {"population", "coverage", "entropy", "stability"}:
                raise ValueError("fsm.when.metric.name must be a supported metric")
            if name in {"coverage", "stability"}:
                try:
                    numeric_value = float(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError("fsm.when.metric.value must be numeric") from exc
                if not (0.0 <= numeric_value <= 1.0):
                    raise ValueError("fsm.when.metric.value must be 0..1 for coverage/stability")
            window_value = None
            sample_value = None
            if window_s is not None:
                window_value = float(window_s)
                if window_value < 0.0:
                    raise ValueError("fsm.when.metric.window_s must be >= 0")
            if sample_every_s is not None:
                sample_value = float(sample_every_s)
                if sample_value < 0.0:
                    raise ValueError("fsm.when.metric.sample_every_s must be >= 0")
            if (
                window_value is not None
                and sample_value is not None
                and sample_value > window_value
            ):
                raise ValueError("fsm.when.metric.sample_every_s must be <= window_s")
        return self


class FSMTransition(BaseModel):
    from_: str = Field(alias="from")
    to: str
    when: FSMTransitionWhen
    once: Optional[bool] = True
    priority: Optional[int] = 0

    model_config = ConfigDict(extra="forbid", validate_by_name=True)


class FSM(BaseModel):
    states: List[str]
    initial: str
    transitions: List[FSMTransition]

    model_config = ConfigDict(extra="forbid")


class Systems(BaseModel):
    entities: List[Entity]
    spawns: List[Spawn]
    rules: List[Rule]
    emitters: Optional[List[Emitter]] = None
    collision_emitters: Optional[List[CollisionEmitter]] = None
    forces: Optional[Forces] = None
    fsm: Optional[FSM] = None
    interactions: Optional[Interactions] = None
    constraints: Optional[Constraints] = None

    @model_validator(mode="after")
    def _validate_tag_selectors(self) -> "Systems":
        if not self.entities:
            return self
        palette = set()
        if hasattr(self, "_palette"):
            palette = set(self._palette)  # type: ignore[attr-defined]
        valid_tags = set()
        for ent in self.entities:
            if ent.tags:
                valid_tags.update(ent.tags)

        def _check_selector(value: str, context: str) -> None:
            if value.startswith("tag:"):
                tag_name = value.split(":", 1)[1]
                if valid_tags and tag_name not in valid_tags:
                    raise ValueError(f"{context} references unknown tag: {tag_name}")
            if value in palette:
                return

        for rule in self.rules:
            _check_selector(rule.applies_to, "rule.applies_to")
            for param_name in ("center", "target"):
                param_value = rule.params.get(param_name)
                if isinstance(param_value, str):
                    _check_selector(param_value, f"rule.params.{param_name}")

        if self.interactions:
            for pair in self.interactions.pairs:
                if isinstance(pair.a, str):
                    _check_selector(pair.a, "interactions.pairs.a")
                if isinstance(pair.b, str):
                    _check_selector(pair.b, "interactions.pairs.b")
        if self.collision_emitters:
            for emitter in self.collision_emitters:
                if isinstance(emitter.a, str):
                    _check_selector(emitter.a, "collision_emitters.a")
                if isinstance(emitter.b, str):
                    _check_selector(emitter.b, "collision_emitters.b")
        return self


class Forces(BaseModel):
    gravity: Optional[float | Dict[str, float]] = None
    noise: Optional[Dict[str, object]] = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_forces(self) -> "Forces":
        if isinstance(self.gravity, dict):
            if "x" not in self.gravity or "y" not in self.gravity:
                raise ValueError("forces.gravity vector must include x and y")
            try:
                float(self.gravity["x"])
                float(self.gravity["y"])
            except (TypeError, ValueError) as exc:
                raise ValueError("forces.gravity vector must be numeric") from exc

        if self.noise is not None:
            strength = self.noise.get("strength")
            scale = self.noise.get("scale")
            if strength is None or scale is None:
                raise ValueError("forces.noise requires strength and scale")
            if float(strength) < 0.0:
                raise ValueError("forces.noise.strength must be >= 0")
            if float(scale) <= 0.0:
                raise ValueError("forces.noise.scale must be > 0")
        return self


class Bounds(BaseModel):
    type: Literal["clamp", "bounce", "wrap"]
    padding: Optional[float] = 0.0
    restitution: Optional[float] = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_restitution(self) -> "Bounds":
        if self.type == "bounce" and self.restitution is None:
            raise ValueError("bounds.restitution is required for type=bounce")
        if self.restitution is not None:
            if not (0.0 <= float(self.restitution) <= 1.0):
                raise ValueError("bounds.restitution must be 0..1")
        return self


class Constraints(BaseModel):
    bounds: Optional[Bounds] = None

    model_config = ConfigDict(extra="forbid")


class InteractionRule(BaseModel):
    type: Literal["merge", "split", "repel", "attract"]
    params: Dict[str, object]
    when: Optional[Dict[str, object]] = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_when(self) -> "InteractionRule":
        if self.when is None:
            return self
        distance = self.when.get("distance_lte")
        probability = self.when.get("probability")
        if distance is not None:
            if float(distance) < 0.0:
                raise ValueError("interactions.rule.when.distance_lte must be >= 0")
        if probability is not None:
            if not (0.0 <= float(probability) <= 1.0):
                raise ValueError("interactions.rule.when.probability must be 0..1")
        return self

    @model_validator(mode="after")
    def _validate_rule_params(self) -> "InteractionRule":
        required_map = {
            "merge": ["distance"],
            "split": ["into", "angle_threshold_deg"],
            "repel": ["target", "strength"],
            "attract": ["target", "strength"],
        }
        required = required_map.get(self.type, [])
        missing = [key for key in required if key not in self.params]
        if missing:
            missing_list = ", ".join(missing)
            raise ValueError(
                f"interactions.rule.params missing required keys for {self.type}: {missing_list}"
            )
        return self


class InteractionPair(BaseModel):
    a: str
    b: str
    rule: InteractionRule

    model_config = ConfigDict(extra="forbid")


class Interactions(BaseModel):
    pairs: List[InteractionPair]

    model_config = ConfigDict(extra="forbid")


class TerminationTime(BaseModel):
    at_s: float

    model_config = ConfigDict(extra="forbid")


class TerminationCondition(BaseModel):
    type: str
    params: Dict[str, object]

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_metric_condition(self) -> "TerminationCondition":
        if self.type == "metric":
            name = self.params.get("name")
            op = self.params.get("op")
            value = self.params.get("value")
            window_s = self.params.get("window_s")
            sample_every_s = self.params.get("sample_every_s")
            if name is None or op is None or value is None:
                raise ValueError("termination.condition.metric requires name/op/value")
            if op not in {">", ">=", "<", "<=", "=="}:
                raise ValueError(
                    "termination.condition.metric.op must be one of >, >=, <, <=, =="
                )
            if name not in {"population", "coverage", "entropy", "stability"}:
                raise ValueError(
                    "termination.condition.metric.name must be a supported metric"
                )
            if name in {"coverage", "stability"}:
                try:
                    numeric_value = float(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError("termination.condition.metric.value must be numeric") from exc
                if not (0.0 <= numeric_value <= 1.0):
                    raise ValueError(
                        "termination.condition.metric.value must be 0..1 for coverage/stability"
                    )
            window_value = None
            sample_value = None
            if window_s is not None:
                window_value = float(window_s)
                if window_value < 0.0:
                    raise ValueError("termination.condition.metric.window_s must be >= 0")
            if sample_every_s is not None:
                sample_value = float(sample_every_s)
                if sample_value < 0.0:
                    raise ValueError(
                        "termination.condition.metric.sample_every_s must be >= 0"
                    )
            if (
                window_value is not None
                and sample_value is not None
                and sample_value > window_value
            ):
                raise ValueError(
                    "termination.condition.metric.sample_every_s must be <= window_s"
                )
        return self


class Termination(BaseModel):
    time: Optional[TerminationTime] = None
    condition: Optional[TerminationCondition] = None

    model_config = ConfigDict(extra="forbid")


class Output(BaseModel):
    format: str
    resolution: str
    codec: str
    bitrate: str

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_output(self) -> "Output":
        if "x" not in self.resolution:
            raise ValueError("output.resolution must be WxH")
        width_str, height_str = self.resolution.lower().split("x", 1)
        if int(width_str) <= 0 or int(height_str) <= 0:
            raise ValueError("output.resolution must be positive WxH")
        if not self.format:
            raise ValueError("output.format is required")
        if self.format != "mp4":
            raise ValueError("output.format must be mp4")
        if not self.codec:
            raise ValueError("output.codec is required")
        if self.codec != "h264":
            raise ValueError("output.codec must be h264")
        if not self.bitrate:
            raise ValueError("output.bitrate is required")
        return self


class DSL(BaseModel):
    dsl_version: str
    meta: Meta
    scene: Scene
    systems: Systems
    termination: Termination
    output: Output
    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_palette_refs(self) -> "DSL":
        palette = set(self.scene.palette)
        if len(self.scene.palette) < 2:
            raise ValueError("scene.palette must have at least 2 colors")
        for color in self.scene.palette:
            if not isinstance(color, str) or not color.startswith("#") or len(color) != 7:
                raise ValueError("scene.palette colors must be hex #RRGGBB")
        if self.scene.background not in palette:
            raise ValueError("scene.background not in palette")
        for ent in self.systems.entities:
            if ent.color not in palette:
                raise ValueError(f"entities.color not in palette: {ent.color}")
            if ent.render:
                stroke = ent.render.get("stroke")
                if stroke and stroke.get("color") not in palette:
                    raise ValueError("entities.render.stroke.color not in palette")
        for rule in self.systems.rules:
            if rule.type != "color_animation":
                continue
            colors = rule.params.get("colors")
            if not isinstance(colors, list):
                raise ValueError("rule.params.colors must be a list")
            for color in colors:
                if color not in palette:
                    raise ValueError(f"rule.params.colors not in palette: {color}")
        return self

    @model_validator(mode="after")
    def _validate_ids_unique(self) -> "DSL":
        entity_ids = [e.id for e in self.systems.entities]
        if len(entity_ids) != len(set(entity_ids)):
            raise ValueError("entities.id must be unique")
        rule_ids = [r.id for r in self.systems.rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("rules.id must be unique")
        if self.systems.emitters:
            emitter_ids = [e.id for e in self.systems.emitters]
            if len(emitter_ids) != len(set(emitter_ids)):
                raise ValueError("emitters.id must be unique")
        if self.systems.collision_emitters:
            emitter_ids = [e.id for e in self.systems.collision_emitters]
            if len(emitter_ids) != len(set(emitter_ids)):
                raise ValueError("collision_emitters.id must be unique")
        return self

    @model_validator(mode="after")
    def _validate_output_matches_canvas(self) -> "DSL":
        res = self.output.resolution.lower().split("x", 1)
        if len(res) == 2:
            width, height = int(res[0]), int(res[1])
            if width != self.scene.canvas.width or height != self.scene.canvas.height:
                raise ValueError("output.resolution must match scene.canvas width/height")
        return self
