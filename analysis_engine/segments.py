from __future__ import annotations

from .aspect_models import Persona


DEFAULT_SEGMENT_DIMENSIONS: tuple[tuple[str, ...], ...] = (
    ("gender",),
    ("height_band",),
    ("weight_band",),
    ("color",),
    ("size",),
    ("height_band", "size"),
    ("weight_band", "size"),
    ("gender", "size"),
    ("color", "size"),
)


def _five_unit_band(value: int, unit: str) -> str:
    lower = (value // 5) * 5
    return f"{lower}~{lower + 4}{unit}"


def persona_values(persona: Persona) -> dict[str, str | None]:
    return {
        "gender": persona.gender,
        "height_band": _five_unit_band(persona.height_cm, "cm") if persona.height_cm else None,
        "weight_band": _five_unit_band(persona.weight_kg, "kg") if persona.weight_kg else None,
        "color": persona.color,
        "size": persona.size,
    }


def segment_for(persona: Persona, dimensions: tuple[str, ...]) -> dict[str, str] | None:
    values = persona_values(persona)
    if any(dimension not in values for dimension in dimensions):
        raise ValueError(f"지원하지 않는 Persona 차원: {dimensions}")
    if any(values[dimension] is None for dimension in dimensions):
        return None
    return {dimension: str(values[dimension]) for dimension in dimensions}


def persona_signature(persona: Persona) -> tuple[str, ...] | None:
    values = persona_values(persona)
    ordered = tuple(values[key] or "" for key in ("gender", "height_band", "weight_band", "color", "size"))
    return ordered if any(ordered) else None


def persona_label(persona: Persona) -> str | None:
    values = persona_values(persona)
    parts = [
        values["gender"],
        values["height_band"],
        values["weight_band"],
        values["color"],
        values["size"],
    ]
    compact = [str(part) for part in parts if part]
    return " · ".join(compact) if compact else None
