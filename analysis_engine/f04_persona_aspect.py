from __future__ import annotations

from collections import defaultdict
from typing import Sequence

from .aspect_models import ReviewAnalysis, Sentiment
from .insight_models import EvidenceRef, PersonaAspectInsight, PersonaAspectSummary
from .segments import DEFAULT_SEGMENT_DIMENSIONS, segment_for


def summarize_persona_aspects(
    analyses: Sequence[ReviewAnalysis],
    *,
    dimension_sets: Sequence[tuple[str, ...]] = DEFAULT_SEGMENT_DIMENSIONS,
    min_segment_reviews: int = 5,
    min_mentions: int = 1,
    evidence_limit: int = 5,
) -> list[PersonaAspectSummary]:
    """Persona segment별 Aspect 전체 긍·부정 rollup을 만든다."""

    if min_segment_reviews < 1 or min_mentions < 1 or evidence_limit < 0:
        raise ValueError("집계 임계값은 올바른 양수여야 합니다.")
    total_reviews = len({analysis.review_id for analysis in analyses})
    summaries: list[PersonaAspectSummary] = []

    for dimensions in dimension_sets:
        segment_reviews: dict[tuple[tuple[str, str], ...], set[str]] = defaultdict(set)
        sentiment_reviews: dict[
            tuple[tuple[tuple[str, str], ...], object, object, Sentiment], set[str]
        ] = defaultdict(set)
        evidence_by_key: dict[
            tuple[tuple[tuple[str, str], ...], object, object], list[EvidenceRef]
        ] = defaultdict(list)
        for analysis in analyses:
            segment = segment_for(analysis.persona, tuple(dimensions))
            if segment is None:
                continue
            segment_key = tuple(sorted(segment.items()))
            segment_reviews[segment_key].add(analysis.review_id)
            seen_aspects: set[tuple[object, object]] = set()
            for mention in analysis.aspects:
                sentiment_reviews[
                    (segment_key, mention.category, mention.aspect, mention.sentiment)
                ].add(analysis.review_id)
                aspect_key = (mention.category, mention.aspect)
                evidence_key = (segment_key, *aspect_key)
                if aspect_key not in seen_aspects and len(evidence_by_key[evidence_key]) < evidence_limit:
                    evidence_by_key[evidence_key].append(
                        EvidenceRef(review_id=analysis.review_id, evidence=mention.evidence)
                    )
                seen_aspects.add(aspect_key)

        known_review_count = len({review_id for ids in segment_reviews.values() for review_id in ids})
        dimension_coverage = known_review_count / total_reviews if total_reviews else 0.0
        aspect_keys = {
            (segment_key, category, aspect)
            for segment_key, category, aspect, _sentiment in sentiment_reviews
        }
        for segment_key, category, aspect in aspect_keys:
            segment_count = len(segment_reviews[segment_key])
            positive_ids = sentiment_reviews.get(
                (segment_key, category, aspect, Sentiment.POSITIVE), set()
            )
            negative_ids = sentiment_reviews.get(
                (segment_key, category, aspect, Sentiment.NEGATIVE), set()
            )
            mentioned_ids = positive_ids | negative_ids
            if segment_count < min_segment_reviews or len(mentioned_ids) < min_mentions:
                continue
            sentiment_total = len(positive_ids) + len(negative_ids)
            summaries.append(
                PersonaAspectSummary(
                    dimensions=list(dimensions),
                    segment=dict(segment_key),
                    segment_review_count=segment_count,
                    category=category,
                    aspect=aspect,
                    mentioned_reviews=len(mentioned_ids),
                    positive_reviews=len(positive_ids),
                    negative_reviews=len(negative_ids),
                    positive_ratio=round(len(positive_ids) / sentiment_total, 4),
                    negative_ratio=round(len(negative_ids) / sentiment_total, 4),
                    mention_rate=round(len(mentioned_ids) / segment_count, 4),
                    dimension_coverage=round(dimension_coverage, 4),
                    coverage_warning=dimension_coverage < 0.70,
                    evidence=evidence_by_key[(segment_key, category, aspect)],
                )
            )

    return sorted(
        summaries,
        key=lambda item: (
            -item.negative_reviews,
            -item.positive_reviews,
            -item.mentioned_reviews,
            "+".join(item.dimensions),
            tuple(item.segment.items()),
            item.aspect.value,
        ),
    )


def analyze_persona_aspects(
    analyses: Sequence[ReviewAnalysis],
    *,
    dimension_sets: Sequence[tuple[str, ...]] = DEFAULT_SEGMENT_DIMENSIONS,
    min_segment_reviews: int = 5,
    min_mentions: int = 1,
    evidence_limit: int = 5,
) -> list[PersonaAspectInsight]:
    if min_segment_reviews < 1 or min_mentions < 1 or evidence_limit < 0:
        raise ValueError("집계 임계값은 올바른 양수여야 합니다.")

    insights: list[PersonaAspectInsight] = []
    total_reviews = len({analysis.review_id for analysis in analyses})

    for dimensions in dimension_sets:
        segment_reviews: dict[tuple[tuple[str, str], ...], set[str]] = defaultdict(set)
        mention_reviews: dict[
            tuple[tuple[tuple[str, str], ...], object, object, object, Sentiment], set[str]
        ] = defaultdict(set)
        evidence_by_key: dict[
            tuple[tuple[tuple[str, str], ...], object, object, object, Sentiment], list[EvidenceRef]
        ] = defaultdict(list)
        dimension_baseline_ids: dict[
            tuple[object, object, object, Sentiment], set[str]
        ] = defaultdict(set)

        for analysis in analyses:
            segment = segment_for(analysis.persona, tuple(dimensions))
            if segment is None:
                continue
            segment_key = tuple(sorted(segment.items()))
            segment_reviews[segment_key].add(analysis.review_id)
            seen_mentions: set[tuple[object, object, object, Sentiment]] = set()
            for mention in analysis.aspects:
                mention_key = (
                    mention.category,
                    mention.aspect,
                    mention.opinion_code,
                    mention.sentiment,
                )
                aggregate_key = (segment_key, *mention_key)
                mention_reviews[aggregate_key].add(analysis.review_id)
                dimension_baseline_ids[mention_key].add(analysis.review_id)
                if mention_key not in seen_mentions and len(evidence_by_key[aggregate_key]) < evidence_limit:
                    evidence_by_key[aggregate_key].append(
                        EvidenceRef(review_id=analysis.review_id, evidence=mention.evidence)
                    )
                seen_mentions.add(mention_key)

        aspect_pairs = {
            (segment_key, category, aspect, opinion_code)
            for segment_key, category, aspect, opinion_code, _sentiment in mention_reviews
        }
        known_review_count = len({review_id for ids in segment_reviews.values() for review_id in ids})
        dimension_coverage = known_review_count / total_reviews if total_reviews else 0.0
        for segment_key, category, aspect, opinion_code in aspect_pairs:
            segment_count = len(segment_reviews[segment_key])
            positive_key = (segment_key, category, aspect, opinion_code, Sentiment.POSITIVE)
            negative_key = (segment_key, category, aspect, opinion_code, Sentiment.NEGATIVE)
            positive_ids = mention_reviews.get(positive_key, set())
            negative_ids = mention_reviews.get(negative_key, set())
            mentioned_ids = positive_ids | negative_ids
            if segment_count < min_segment_reviews or len(mentioned_ids) < min_mentions:
                continue
            sentiment_total = len(positive_ids) + len(negative_ids)
            dominant_sentiment = (
                Sentiment.NEGATIVE if len(negative_ids) >= len(positive_ids) else Sentiment.POSITIVE
            )
            baseline_key = (category, aspect, opinion_code, dominant_sentiment)
            dominant_count = (
                len(negative_ids) if dominant_sentiment == Sentiment.NEGATIVE else len(positive_ids)
            )
            segment_rate = dominant_count / segment_count
            baseline_rate = (
                len(dimension_baseline_ids.get(baseline_key, set())) / known_review_count
                if known_review_count
                else 0.0
            )
            lift = segment_rate / baseline_rate if baseline_rate else 0.0
            rate_delta = segment_rate - baseline_rate
            if dominant_sentiment == Sentiment.NEGATIVE:
                is_insight = dominant_count >= 3 and segment_rate >= 0.20 and rate_delta >= 0.10 and lift >= 1.5
                insight_kind = "negative" if is_insight else None
            else:
                is_insight = dominant_count >= 3 and segment_rate >= 0.25 and rate_delta >= 0.10 and lift >= 1.25
                insight_kind = "positive" if is_insight else None
            combined_evidence = (evidence_by_key.get(negative_key, []) + evidence_by_key.get(positive_key, []))[
                :evidence_limit
            ]
            insights.append(
                PersonaAspectInsight(
                    dimensions=list(dimensions),
                    segment=dict(segment_key),
                    segment_review_count=segment_count,
                    category=category,
                    aspect=aspect,
                    opinion_code=opinion_code,
                    mentioned_reviews=len(mentioned_ids),
                    positive_reviews=len(positive_ids),
                    negative_reviews=len(negative_ids),
                    positive_ratio=round(len(positive_ids) / sentiment_total, 4),
                    negative_ratio=round(len(negative_ids) / sentiment_total, 4),
                    mention_rate=round(len(mentioned_ids) / segment_count, 4),
                    baseline_rate=round(baseline_rate, 4),
                    lift=round(lift, 4),
                    dimension_coverage=round(dimension_coverage, 4),
                    coverage_warning=dimension_coverage < 0.70,
                    is_insight=is_insight,
                    insight_kind=insight_kind,
                    evidence=combined_evidence,
                )
            )

    return sorted(
        insights,
        key=lambda item: (
            -item.negative_reviews,
            -item.negative_ratio,
            -item.mentioned_reviews,
            "+".join(item.dimensions),
            tuple(item.segment.items()),
            item.aspect.value,
            item.opinion_code.value,
        ),
    )
