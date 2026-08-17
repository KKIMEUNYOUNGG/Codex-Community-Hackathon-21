from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from datetime import date, datetime
from typing import Any, Iterable, Sequence

from .aspect_models import ReviewAnalysis
from .insight_models import EvidenceRef, OpinionCount, PersonaAspectInsight
from .segments import persona_label


SUPPORT_RATE = 0.02


def raw_reviews_by_id(raw_reviews: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for review in raw_reviews:
        review_id = str(review.get("review_id") or review.get("source_review_id") or "")
        if review_id:
            result[review_id] = review
    return result


def parse_review_date(review: dict[str, Any]) -> date | None:
    value = review.get("date") or review.get("reviewed_at")
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"\s+", " ", normalized).strip()


def deduplicate_inputs(
    analyses: Sequence[ReviewAnalysis],
    raw_reviews: Sequence[dict[str, Any]],
) -> tuple[list[ReviewAnalysis], list[dict[str, Any]]]:
    raw_by_id = raw_reviews_by_id(raw_reviews)
    candidates: list[tuple[ReviewAnalysis, dict[str, Any]]] = []
    for analysis in analyses:
        raw = raw_by_id.get(analysis.review_id)
        if raw is not None:
            candidates.append((analysis, raw))

    candidates.sort(
        key=lambda item: (
            parse_review_date(item[1]) or date.min,
            int(item[1].get("like_count") or 0),
            item[0].review_id,
        ),
        reverse=True,
    )
    seen: set[tuple[str, str]] = set()
    kept: list[tuple[ReviewAnalysis, dict[str, Any]]] = []
    for analysis, raw in candidates:
        user_id = str(raw.get("encrypted_user_id") or "")
        text = normalize_text(str(raw.get("review_text") or ""))
        key = (user_id, text)
        if user_id and text and key in seen:
            continue
        if user_id and text:
            seen.add(key)
        kept.append((analysis, raw))

    kept.sort(key=lambda item: item[0].review_id)
    return [item[0] for item in kept], [item[1] for item in kept]


def minimum_support(review_count: int) -> int:
    return max(3, math.ceil(review_count * SUPPORT_RATE))


def top_personas(analyses: Iterable[ReviewAnalysis], limit: int = 3) -> list[str]:
    counts = Counter(label for analysis in analyses if (label := persona_label(analysis.persona)))
    return [label for label, _count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def concentrated_persona_segments(
    persona_aspects: Sequence[PersonaAspectInsight],
    *,
    category: object,
    aspect: object,
    opinion_code: object,
    insight_kind: str,
    limit: int = 3,
) -> list[str]:
    matches = [
        insight
        for insight in persona_aspects
        if insight.is_insight
        and insight.insight_kind == insight_kind
        and insight.category == category
        and insight.aspect == aspect
        and insight.opinion_code == opinion_code
    ]
    matches.sort(
        key=lambda insight: (
            -(insight.negative_reviews if insight_kind == "negative" else insight.positive_reviews),
            -insight.lift,
            -insight.segment_review_count,
            "+".join(insight.dimensions),
            tuple(insight.segment.items()),
        )
    )
    labels: list[str] = []
    for insight in matches:
        label = " × ".join(insight.segment[dimension] for dimension in insight.dimensions)
        if label not in labels:
            labels.append(label)
        if len(labels) >= limit:
            break
    return labels


def opinion_counts(opinions: Iterable[str], limit: int = 5) -> list[OpinionCount]:
    display_by_key: dict[str, str] = {}
    counts: Counter[str] = Counter()
    for opinion in opinions:
        key = normalize_text(opinion)
        if not key:
            continue
        display_by_key.setdefault(key, opinion.strip())
        counts[key] += 1
    return [
        OpinionCount(opinion=display_by_key[key], review_count=count)
        for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def ordered_review_ids(
    review_ids: Iterable[str],
    raw_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    return sorted(
        set(review_ids),
        key=lambda review_id: (
            int(raw_by_id.get(review_id, {}).get("like_count") or 0),
            parse_review_date(raw_by_id.get(review_id, {})) or date.min,
            review_id,
        ),
        reverse=True,
    )


def evidence_refs(
    review_ids: Sequence[str],
    evidence_by_review: dict[str, list[str]],
    limit: int = 5,
) -> list[EvidenceRef]:
    result: list[EvidenceRef] = []
    for review_id in review_ids:
        for evidence in evidence_by_review.get(review_id, []):
            result.append(EvidenceRef(review_id=review_id, evidence=evidence))
            break
        if len(result) >= limit:
            break
    return result


def product_like_p95(raw_reviews: Sequence[dict[str, Any]]) -> float:
    likes = sorted(max(0, int(review.get("like_count") or 0)) for review in raw_reviews)
    if not likes:
        return 0.0
    index = max(0, math.ceil(0.95 * len(likes)) - 1)
    return float(likes[index])


def average_recency(
    review_ids: Iterable[str],
    raw_by_id: dict[str, dict[str, Any]],
    *,
    analysis_as_of: date,
    half_life_days: int = 180,
) -> float:
    if half_life_days < 1:
        raise ValueError("half_life_days는 1 이상이어야 합니다.")
    unique_review_ids = set(review_ids)
    if not unique_review_ids:
        return 0.0
    scores = []
    for review_id in unique_review_ids:
        value = parse_review_date(raw_by_id.get(review_id, {}))
        scores.append(
            0.0
            if value is None
            else 2 ** (-max(0, (analysis_as_of - value).days) / half_life_days)
        )
    return sum(scores) / len(scores)


def average_likes(
    review_ids: Iterable[str],
    raw_by_id: dict[str, dict[str, Any]],
    like_p95: float,
) -> float:
    if like_p95 <= 0:
        return 0.0
    denominator = math.log1p(like_p95)
    scores = [
        min(1.0, math.log1p(max(0, int(raw_by_id.get(review_id, {}).get("like_count") or 0))) / denominator)
        for review_id in set(review_ids)
    ]
    return sum(scores) / len(scores) if scores else 0.0
