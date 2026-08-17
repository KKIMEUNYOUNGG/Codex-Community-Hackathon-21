from __future__ import annotations

import re
import unicodedata
from typing import Any

from .aspect_models import Persona


SIZE_RE = re.compile(
    r"^(?:0{1,2}S|X{0,5}S|M|X{0,5}L|[2-5]XL|FREE|ONE\s*SIZE|\d{2,3})$",
    re.IGNORECASE,
)
OPTION_LABEL_RE = re.compile(
    r"(?:색상|컬러|COLOR|COLOUR|사이즈|SIZE)\s*[:：]?\s*",
    re.IGNORECASE,
)


def _clean_option_part(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", OPTION_LABEL_RE.sub("", value)).strip(" []()")


def _normalize_gender(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = unicodedata.normalize("NFKC", value).strip()
    key = normalized.casefold()
    if key in {"여성", "여자", "female", "woman", "women", "f"}:
        return "여성"
    if key in {"남성", "남자", "male", "man", "men", "m"}:
        return "남성"
    return normalized


def parse_color_and_size(option: Any) -> tuple[str | None, str | None]:
    if not isinstance(option, str) or not option.strip():
        return None, None

    parts = [_clean_option_part(part) for part in re.split(r"\s*(?:[/,|]|·)\s*", option)]
    parts = [part for part in parts if part]
    if not parts:
        return None, None
    if len(parts) == 1:
        value = parts[0]
        return (None, value.upper().replace(" ", "")) if SIZE_RE.fullmatch(value) else (value.upper(), None)

    size_index = next(
        (index for index in range(len(parts) - 1, -1, -1) if SIZE_RE.fullmatch(parts[index])),
        None,
    )
    if size_index is None:
        return parts[0], None

    size = parts[size_index].upper().replace(" ", "")
    color_parts = [part for index, part in enumerate(parts) if index != size_index]
    color = " / ".join(color_parts).upper() or None
    return color, size


def persona_from_review(review: dict[str, Any]) -> Persona:
    color, size = parse_color_and_size(review.get("option") or review.get("purchased_option"))
    return Persona(
        gender=_normalize_gender(review.get("reviewer_gender")),
        height_cm=review.get("reviewer_height_cm"),
        weight_kg=review.get("reviewer_weight_kg"),
        color=color,
        size=size,
    )
