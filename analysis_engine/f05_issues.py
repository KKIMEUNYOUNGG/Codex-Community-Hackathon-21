from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any, Sequence

from .aggregation_utils import (
    evidence_refs,
    concentrated_persona_segments,
    minimum_support,
    opinion_counts,
    ordered_review_ids,
    parse_review_date,
    raw_reviews_by_id,
    top_personas,
)
from .aspect_models import ReviewAnalysis, Sentiment
from .aspect_taxonomy import ASPECT_LABELS_KO, OPINION_LABELS_KO
from .insight_models import Issue
from .insight_models import PersonaAspectInsight


ISSUE_NAMESPACE = uuid.UUID("e7edc10a-e9ca-45de-91c0-b9d91a773885")


def detect_issues(
    product_id: str,
    analyses: Sequence[ReviewAnalysis],
    raw_reviews: Sequence[dict[str, Any]],
    *,
    min_support: int | None = None,
    evidence_limit: int = 5,
    persona_aspects: Sequence[PersonaAspectInsight] = (),
) -> list[Issue]:
    threshold = min_support if min_support is not None else minimum_support(len(analyses))
    if threshold < 1:
        raise ValueError("min_support는 1 이상이어야 합니다.")

    raw_by_id = raw_reviews_by_id(raw_reviews)
    analysis_by_id = {analysis.review_id: analysis for analysis in analyses}
    negative_ids: dict[tuple[object, object, object], set[str]] = defaultdict(set)
    negative_mentions: dict[tuple[object, object, object], list[tuple[str, str, str]]] = defaultdict(list)
    aspect_positive_ids: dict[object, set[str]] = defaultdict(set)
    aspect_negative_ids: dict[object, set[str]] = defaultdict(set)

    for analysis in analyses:
        for mention in analysis.aspects:
            if mention.sentiment == Sentiment.POSITIVE:
                aspect_positive_ids[mention.aspect].add(analysis.review_id)
                continue
            aspect_negative_ids[mention.aspect].add(analysis.review_id)
            key = (mention.category, mention.aspect, mention.opinion_code)
            negative_ids[key].add(analysis.review_id)
            negative_mentions[key].append((analysis.review_id, mention.evidence, mention.opinion))

    issues: list[Issue] = []
    for (category, aspect, opinion_code), ids in negative_ids.items():
        if len(ids) < threshold:
            continue
        ordered_ids = ordered_review_ids(ids, raw_by_id)
        evidence_by_review: dict[str, list[str]] = defaultdict(list)
        opinions: list[str] = []
        for review_id, evidence, opinion in negative_mentions[(category, aspect, opinion_code)]:
            evidence_by_review[review_id].append(evidence)
            opinions.append(opinion)

        aspect_sentiment_ids = aspect_negative_ids[aspect] | aspect_positive_ids[aspect]
        dates = [parse_review_date(raw_by_id.get(review_id, {})) for review_id in ids]
        known_dates = sorted(value for value in dates if value is not None)
        issue_id = str(
            uuid.uuid5(
                ISSUE_NAMESPACE,
                f"{product_id}:{category.value}:{aspect.value}:{opinion_code.value}",
            )
        )
        title = f"{ASPECT_LABELS_KO[aspect]} · {OPINION_LABELS_KO[opinion_code]}"
        affected_personas = concentrated_persona_segments(
            persona_aspects,
            category=category,
            aspect=aspect,
            opinion_code=opinion_code,
            insight_kind="negative",
        ) or top_personas(analysis_by_id[review_id] for review_id in ids)
        issues.append(
            Issue(
                issue_id=issue_id,
                title=title,
                category=category,
                aspect=aspect,
                opinion_code=opinion_code,
                related_review_count=len(ids),
                aspect_review_count=len(aspect_sentiment_ids),
                negative_ratio=round(len(ids) / len(aspect_sentiment_ids), 4),
                mention_count=len(negative_mentions[(category, aspect, opinion_code)]),
                first_seen_at=known_dates[0].isoformat() if known_dates else None,
                last_seen_at=known_dates[-1].isoformat() if known_dates else None,
                affected_personas=affected_personas,
                dominant_opinions=opinion_counts(opinions),
                review_ids=ordered_ids,
                evidence=evidence_refs(ordered_ids, evidence_by_review, evidence_limit),
            )
        )

    return sorted(
        issues,
        key=lambda item: (
            -item.related_review_count,
            -item.negative_ratio,
            item.aspect.value,
            item.opinion_code.value,
            item.issue_id,
        ),
    )
