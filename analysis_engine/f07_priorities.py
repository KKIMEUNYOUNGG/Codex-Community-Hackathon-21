from __future__ import annotations

import math
from datetime import date
from typing import Any, Sequence

from .aggregation_utils import (
    average_likes,
    average_recency,
    product_like_p95,
    raw_reviews_by_id,
)
from .aspect_models import ReviewAnalysis
from .insight_models import (
    ImprovementPriority,
    Issue,
    PersonaAspectInsight,
    PriorityComponents,
)


PRIORITY_WEIGHTS = {
    "frequency": 0.30,
    "negative_ratio": 0.30,
    "affected_customer_breadth": 0.20,
    "recency": 0.15,
    "likes": 0.05,
}


def _date_ordinal(value: str | None) -> int:
    if not value:
        return 0
    try:
        return date.fromisoformat(value[:10]).toordinal()
    except ValueError:
        return 0


def _unique_customer_breadth(
    review_ids: Sequence[str],
    raw_by_id: dict[str, dict[str, Any]],
    total_review_count: int,
) -> float:
    all_customer_ids = {
        str(review.get("encrypted_user_id"))
        for review in raw_by_id.values()
        if review.get("encrypted_user_id")
    }
    affected_customer_ids = {
        str(raw_by_id[review_id].get("encrypted_user_id"))
        for review_id in set(review_ids)
        if review_id in raw_by_id and raw_by_id[review_id].get("encrypted_user_id")
    }
    if all_customer_ids and affected_customer_ids:
        return min(1.0, len(affected_customer_ids) / len(all_customer_ids))
    return min(1.0, len(set(review_ids)) / total_review_count) if total_review_count else 0.0


def _matching_persona_reason(
    issue: Issue,
    persona_aspects: Sequence[PersonaAspectInsight],
) -> str | None:
    candidates = [
        insight
        for insight in persona_aspects
        if insight.is_insight
        and insight.insight_kind == "negative"
        and insight.category == issue.category
        and insight.aspect == issue.aspect
        and insight.opinion_code == issue.opinion_code
    ]
    if not candidates:
        return None
    strongest = sorted(
        candidates,
        key=lambda insight: (
            -insight.negative_reviews,
            -insight.lift,
            "+".join(insight.dimensions),
            tuple(insight.segment.items()),
        ),
    )[0]
    segment = " × ".join(strongest.segment[dimension] for dimension in strongest.dimensions)
    return f"{segment} 고객군에서 기준 대비 {strongest.lift:.2f}배 집중"


def rank_improvement_priorities(
    issues: Sequence[Issue],
    analyses: Sequence[ReviewAnalysis],
    raw_reviews: Sequence[dict[str, Any]],
    *,
    persona_aspects: Sequence[PersonaAspectInsight] = (),
    analysis_as_of: date | None = None,
) -> list[ImprovementPriority]:
    """F07 리뷰 기반 개선 우선순위를 계산한다.

    판매량·반품률·매출처럼 입력에 없는 지표는 사용하지 않는다. 모든 구성요소는
    0~1로 정규화되며 가중합은 설명 가능한 고정식(priority-v1)이다.
    """

    total_review_count = len({analysis.review_id for analysis in analyses})
    raw_by_id = raw_reviews_by_id(raw_reviews)
    like_p95 = product_like_p95(raw_reviews)
    as_of = analysis_as_of or date.today()
    saturation_count = max(5, math.ceil(total_review_count * 0.10))
    seen_issue_ids: set[str] = set()
    scored: list[tuple[Issue, float, PriorityComponents, list[str]]] = []

    for issue in issues:
        if issue.issue_id in seen_issue_ids:
            raise ValueError(f"중복 issue_id: {issue.issue_id}")
        seen_issue_ids.add(issue.issue_id)

        frequency = min(1.0, issue.related_review_count / saturation_count)
        # 작은 표본의 0%/100% 과신을 줄이는 Laplace smoothing.
        negative_ratio = (issue.related_review_count + 1) / (issue.aspect_review_count + 2)
        customer_breadth = _unique_customer_breadth(
            issue.review_ids,
            raw_by_id,
            total_review_count,
        )
        recency = average_recency(issue.review_ids, raw_by_id, analysis_as_of=as_of)
        likes = average_likes(issue.review_ids, raw_by_id, like_p95)

        components = PriorityComponents(
            frequency=round(frequency, 4),
            negative_ratio=round(negative_ratio, 4),
            affected_customer_breadth=round(customer_breadth, 4),
            recency=round(recency, 4),
            likes=round(likes, 4),
        )
        score = 100 * sum(
            PRIORITY_WEIGHTS[name] * getattr(components, name)
            for name in PRIORITY_WEIGHTS
        )
        reasons = [
            f"관련 리뷰 {issue.related_review_count}건",
            f"해당 세부 의견의 부정 비율 {negative_ratio:.1%}(보정값)",
            f"최근성 점수 {recency:.2f}, 좋아요 점수 {likes:.2f}",
        ]
        if persona_reason := _matching_persona_reason(issue, persona_aspects):
            reasons.append(persona_reason)
        scored.append((issue, round(score, 2), components, reasons))

    scored.sort(
        key=lambda item: (
            -item[1],
            -item[0].related_review_count,
            -_date_ordinal(item[0].last_seen_at),
            item[0].issue_id,
        )
    )
    return [
        ImprovementPriority(
            rank=rank,
            issue_id=issue.issue_id,
            title=issue.title,
            score=score,
            components=components,
            reasons=reasons,
            review_ids=issue.review_ids,
            evidence=issue.evidence,
        )
        for rank, (issue, score, components, reasons) in enumerate(scored, start=1)
    ]
