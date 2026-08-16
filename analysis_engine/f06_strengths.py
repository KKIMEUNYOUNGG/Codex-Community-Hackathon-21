from __future__ import annotations

import math
import uuid
from collections import defaultdict
from datetime import date
from typing import Any, Sequence

from .aggregation_utils import (
    average_likes,
    average_recency,
    concentrated_persona_segments,
    evidence_refs,
    minimum_support,
    opinion_counts,
    ordered_review_ids,
    parse_review_date,
    product_like_p95,
    raw_reviews_by_id,
    top_personas,
)
from .aspect_models import ReviewAnalysis, Sentiment
from .aspect_taxonomy import ASPECT_LABELS_KO, OPINION_LABELS_KO
from .insight_models import PersonaAspectInsight, Strength


STRENGTH_NAMESPACE = uuid.UUID("7715b996-dffd-43f0-a70f-3a1e21317fca")


def detect_strengths(
    product_id: str,
    analyses: Sequence[ReviewAnalysis],
    raw_reviews: Sequence[dict[str, Any]],
    *,
    min_support: int | None = None,
    evidence_limit: int = 5,
    analysis_as_of: date | None = None,
    persona_aspects: Sequence[PersonaAspectInsight] = (),
) -> list[Strength]:
    threshold = min_support if min_support is not None else minimum_support(len(analyses))
    if threshold < 1:
        raise ValueError("min_support는 1 이상이어야 합니다.")

    raw_by_id = raw_reviews_by_id(raw_reviews)
    as_of = analysis_as_of or date.today()
    analysis_by_id = {analysis.review_id: analysis for analysis in analyses}
    positive_ids: dict[tuple[object, object, object], set[str]] = defaultdict(set)
    positive_mentions: dict[tuple[object, object, object], list[tuple[str, str, str]]] = defaultdict(list)
    aspect_positive_ids: dict[object, set[str]] = defaultdict(set)
    aspect_negative_ids: dict[object, set[str]] = defaultdict(set)
    for analysis in analyses:
        for mention in analysis.aspects:
            if mention.sentiment == Sentiment.NEGATIVE:
                aspect_negative_ids[mention.aspect].add(analysis.review_id)
                continue
            aspect_positive_ids[mention.aspect].add(analysis.review_id)
            key = (mention.category, mention.aspect, mention.opinion_code)
            positive_ids[key].add(analysis.review_id)
            positive_mentions[key].append((analysis.review_id, mention.evidence, mention.opinion))

    like_p95 = product_like_p95(raw_reviews)
    strengths: list[Strength] = []
    for (category, aspect, opinion_code), ids in positive_ids.items():
        if len(ids) < threshold:
            continue
        ordered_ids = ordered_review_ids(ids, raw_by_id)
        evidence_by_review: dict[str, list[str]] = defaultdict(list)
        opinions: list[str] = []
        for review_id, evidence, opinion in positive_mentions[(category, aspect, opinion_code)]:
            evidence_by_review[review_id].append(evidence)
            opinions.append(opinion)

        aspect_sentiment_ids = aspect_positive_ids[aspect] | aspect_negative_ids[aspect]
        positive_ratio = (len(ids) + 1) / (len(aspect_sentiment_ids) + 2)
        frequency = min(1.0, len(ids) / max(5, math.ceil(len(analyses) * 0.10)))
        recency = average_recency(ids, raw_by_id, analysis_as_of=as_of)
        likes = average_likes(ids, raw_by_id, like_p95)
        score = 100 * (0.50 * frequency + 0.35 * positive_ratio + 0.10 * recency + 0.05 * likes)
        dates = [parse_review_date(raw_by_id.get(review_id, {})) for review_id in ids]
        known_dates = sorted(value for value in dates if value is not None)
        strength_id = str(
            uuid.uuid5(
                STRENGTH_NAMESPACE,
                f"{product_id}:{category.value}:{aspect.value}:{opinion_code.value}",
            )
        )
        affected_personas = concentrated_persona_segments(
            persona_aspects,
            category=category,
            aspect=aspect,
            opinion_code=opinion_code,
            insight_kind="positive",
        ) or top_personas(analysis_by_id[review_id] for review_id in ids)
        strengths.append(
            Strength(
                strength_id=strength_id,
                title=f"{ASPECT_LABELS_KO[aspect]} · {OPINION_LABELS_KO[opinion_code]}",
                category=category,
                aspect=aspect,
                opinion_code=opinion_code,
                related_review_count=len(ids),
                aspect_review_count=len(aspect_sentiment_ids),
                positive_ratio=round(len(ids) / len(aspect_sentiment_ids), 4),
                score=round(score, 2),
                mention_count=len(positive_mentions[(category, aspect, opinion_code)]),
                first_seen_at=known_dates[0].isoformat() if known_dates else None,
                last_seen_at=known_dates[-1].isoformat() if known_dates else None,
                affected_personas=affected_personas,
                dominant_opinions=opinion_counts(opinions),
                review_ids=ordered_ids,
                evidence=evidence_refs(ordered_ids, evidence_by_review, evidence_limit),
            )
        )

    return sorted(
        strengths,
        key=lambda item: (
            -item.score,
            -item.related_review_count,
            item.aspect.value,
            item.opinion_code.value,
            item.strength_id,
        ),
    )
