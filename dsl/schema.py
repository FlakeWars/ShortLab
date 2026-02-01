from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Canvas(BaseModel):
    width: int
    height: int
    fps: int
    duration_s: float

    model_config = ConfigDict(extra="forbid")


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
    shape: str
    size: float | Dict[str, float]
    color: str
    mass: Optional[float] = 1.0
    render: Optional[Dict[str, object]] = None

    model_config = ConfigDict(extra="forbid")


class Distribution(BaseModel):
    type: str
    params: Optional[Dict[str, object]] = None

    model_config = ConfigDict(extra="forbid")


class Spawn(BaseModel):
    entity_id: str
    count: int
    distribution: Distribution

    model_config = ConfigDict(extra="forbid")


class Rule(BaseModel):
    id: str
    type: str
    applies_to: str
    params: Dict[str, object]
    probability: Optional[float] = None

    model_config = ConfigDict(extra="forbid")


class FSMTransitionWhen(BaseModel):
    type: str
    params: Dict[str, object]

    model_config = ConfigDict(extra="forbid")


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
    forces: Optional[Dict[str, object]] = None
    fsm: Optional[FSM] = None
    interactions: Optional[Dict[str, object]] = None

    model_config = ConfigDict(extra="forbid")


class TerminationTime(BaseModel):
    at_s: float

    model_config = ConfigDict(extra="forbid")


class TerminationCondition(BaseModel):
    type: str
    params: Dict[str, object]

    model_config = ConfigDict(extra="forbid")


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


class DSL(BaseModel):
    dsl_version: str
    meta: Meta
    scene: Scene
    systems: Systems
    termination: Termination
    output: Output
    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid")
