from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from pydantic import ValidationError

from .schema import DSL


class DSLValidationError(Exception):
    pass


def _load_data(path: Path) -> Dict[str, Any]:
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except Exception as exc:  # pragma: no cover - runtime dependency
            raise DSLValidationError(
                "PyYAML is required to load YAML files."
            ) from exc
        return yaml.safe_load(path.read_text())
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text())
    raise DSLValidationError(f"Unsupported DSL format: {path.suffix}")


def _parse_model(payload: Dict[str, Any]) -> DSL:
    if hasattr(DSL, "model_validate"):
        return DSL.model_validate(payload)  # pydantic v2
    return DSL.parse_obj(payload)  # pydantic v1


def _validate_refs(model: DSL) -> List[str]:
    errors: List[str] = []
    entity_ids = {e.id for e in model.systems.entities}

    for spawn in model.systems.spawns:
        if spawn.entity_id not in entity_ids:
            errors.append(f"spawn.entity_id not found: {spawn.entity_id}")

    for rule in model.systems.rules:
        applies = rule.applies_to
        if applies in {"*", "all"}:
            continue
        if applies.startswith("tag:"):
            continue
        if applies not in entity_ids:
            errors.append(f"rule.applies_to not found: {applies}")

    term = model.termination
    if (term.time is None and term.condition is None) or (
        term.time is not None and term.condition is not None
    ):
        errors.append("termination must specify exactly one of time or condition")

    if model.systems.fsm is not None:
        states = set(model.systems.fsm.states)
        if model.systems.fsm.initial not in states:
            errors.append("fsm.initial must be in fsm.states")
        for transition in model.systems.fsm.transitions:
            if transition.from_ not in states:
                errors.append(f"fsm.transition.from not in states: {transition.from_}")
            if transition.to not in states:
                errors.append(f"fsm.transition.to not in states: {transition.to}")

    return errors


def validate_file(path: str | Path) -> DSL:
    path = Path(path)
    payload = _load_data(path)
    try:
        model = _parse_model(payload)
    except ValidationError as exc:
        raise DSLValidationError(str(exc)) from exc

    ref_errors = _validate_refs(model)
    if ref_errors:
        raise DSLValidationError("; ".join(ref_errors))

    return model
