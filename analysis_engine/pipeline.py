from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Sequence

from .aggregation_utils import SUPPORT_RATE, deduplicate_inputs, minimum_support, raw_reviews_by_id
from .aspect_models import AspectAnalysisArtifact, ReviewAnalysis
from .f03_aspect_analysis import calculate_source_hash
from .f04_persona_aspect import analyze_persona_aspects, summarize_persona_aspects
from .f05_issues import detect_issues
from .f06_strengths import detect_strengths
from .f07_priorities import PRIORITY_WEIGHTS, rank_improvement_priorities
from .insight_models import ProductInsightConfig, ProductInsightsArtifact
from .persona import persona_from_review


class ProductInsightError(RuntimeError):
    pass


def load_aspect_artifact(path: Path) -> AspectAnalysisArtifact:
    try:
        return AspectAnalysisArtifact.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ProductInsightError(f"F03 분석 결과를 읽을 수 없습니다: {path}: {exc}") from exc


def validate_analysis_evidence(
    artifact: AspectAnalysisArtifact,
    raw_reviews: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    if artifact.status != "completed":
        raise ProductInsightError("완료된 F03 분석 결과만 후속 분석에 사용할 수 있습니다.")
    if artifact.analyzed_reviews != len(artifact.analyses):
        raise ProductInsightError("F03 analyzed_reviews와 analyses 길이가 다릅니다.")

    raw_by_id = raw_reviews_by_id(raw_reviews)
    analysis_ids = [analysis.review_id for analysis in artifact.analyses]
    if len(analysis_ids) != len(set(analysis_ids)):
        raise ProductInsightError("F03 결과에 중복 review_id가 있습니다.")
    missing = [review_id for review_id in analysis_ids if review_id not in raw_by_id]
    if missing:
        raise ProductInsightError("원본 리뷰에 없는 review_id: " + ", ".join(missing[:10]))

    selected_raw = [raw_by_id[review_id] for review_id in analysis_ids]
    product_ids = {str(review.get("product_id") or "") for review in selected_raw}
    if product_ids != {artifact.product_id}:
        raise ProductInsightError("F03 상품 ID와 원본 리뷰 상품 ID가 다릅니다.")
    if calculate_source_hash(selected_raw) != artifact.source_hash:
        raise ProductInsightError("F03 이후 원본 리뷰 또는 Persona 메타데이터가 변경됐습니다.")

    for analysis in artifact.analyses:
        review_text = str(raw_by_id[analysis.review_id].get("review_text") or "")
        if analysis.persona != persona_from_review(raw_by_id[analysis.review_id]):
            raise ProductInsightError(
                f"F03 Persona가 원본 메타데이터와 다릅니다: review_id={analysis.review_id}"
            )
        for mention in analysis.aspects:
            if mention.evidence_start is None or mention.evidence_end is None:
                raise ProductInsightError(
                    f"Evidence offset이 없습니다: review_id={analysis.review_id}"
                )
            if review_text[mention.evidence_start : mention.evidence_end] != mention.evidence:
                raise ProductInsightError(
                    f"Evidence가 원문 offset과 다릅니다: review_id={analysis.review_id}"
                )
    return selected_raw


def build_product_insights(
    artifact: AspectAnalysisArtifact,
    raw_reviews: Sequence[dict[str, Any]],
    *,
    min_issue_support: int | None = None,
    min_strength_support: int | None = None,
    analysis_as_of: date | None = None,
) -> ProductInsightsArtifact:
    selected_raw = validate_analysis_evidence(artifact, raw_reviews)
    analyses, deduplicated_raw = deduplicate_inputs(artifact.analyses, selected_raw)
    as_of = analysis_as_of or date.today()
    issue_support = min_issue_support if min_issue_support is not None else minimum_support(len(analyses))
    strength_support = (
        min_strength_support
        if min_strength_support is not None
        else minimum_support(len(analyses))
    )
    persona_aspect_summary = summarize_persona_aspects(analyses)
    persona_aspect = analyze_persona_aspects(analyses)
    issues = detect_issues(
        artifact.product_id,
        analyses,
        deduplicated_raw,
        min_support=issue_support,
        persona_aspects=persona_aspect,
    )
    strengths = detect_strengths(
        artifact.product_id,
        analyses,
        deduplicated_raw,
        min_support=strength_support,
        analysis_as_of=as_of,
        persona_aspects=persona_aspect,
    )
    priorities = rank_improvement_priorities(
        issues,
        analyses,
        deduplicated_raw,
        persona_aspects=persona_aspect,
        analysis_as_of=as_of,
    )
    return ProductInsightsArtifact(
        product_id=artifact.product_id,
        source_aspect_schema_version=artifact.schema_version,
        source_hash=artifact.source_hash,
        taxonomy_version=artifact.taxonomy_version,
        prompt_version=artifact.prompt_version,
        source_review_count=artifact.source_review_count or artifact.total_reviews,
        selected_review_count=artifact.total_reviews,
        is_sample=artifact.is_sample,
        analysis_config=ProductInsightConfig(
            analysis_as_of=as_of,
            input_review_count=len(artifact.analyses),
            deduplicated_review_count=len(analyses),
            issue_min_support=issue_support,
            strength_min_support=strength_support,
            support_rate=SUPPORT_RATE,
            priority_weights=dict(PRIORITY_WEIGHTS),
        ),
        analyzed_review_count=len(analyses),
        persona_aspect_summary=persona_aspect_summary,
        persona_aspect=persona_aspect,
        issues=issues,
        strengths=strengths,
        priorities=priorities,
    )


def write_product_insights(path: Path, artifact: ProductInsightsArtifact) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    temp_path.replace(path)


def load_raw_reviews(path: Path) -> list[dict[str, Any]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductInsightError(f"원본 리뷰를 읽을 수 없습니다: {path}: {exc}") from exc
    reviews = document.get("reviews") if isinstance(document, dict) else None
    if not isinstance(reviews, list):
        raise ProductInsightError(f"reviews 배열이 없습니다: {path}")
    return reviews
