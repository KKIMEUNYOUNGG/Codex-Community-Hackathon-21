from __future__ import annotations

import json
import os
import hashlib
import random
import time
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence

from .aspect_models import (
    AspectAnalysisArtifact,
    AspectBatchResponse,
    AspectSummary,
    ExtractedReview,
    ReviewAnalysis,
    Sentiment,
)
from .aspect_taxonomy import (
    OPINION_LABELS_KO,
    OPINION_ALLOWED_ASPECTS,
    TAXONOMY_VERSION,
    Aspect,
    AspectCategory,
    TAXONOMY_PROMPT,
)
from .persona import persona_from_review


PROMPT_VERSION = "f03-aspect-v3"
DEFAULT_MODEL = "gpt-5.6-luna"
MAX_REVIEW_CHARS = 8_000
MAX_BATCH_CHARS = 50_000
OPINION_CODE_PROMPT = ", ".join(
    f"{code.value}({label}; "
    + (
        "모든 Aspect"
        if OPINION_ALLOWED_ASPECTS[code] == frozenset(Aspect)
        else "/".join(sorted(aspect.value for aspect in OPINION_ALLOWED_ASPECTS[code]))
    )
    + ")"
    for code, label in OPINION_LABELS_KO.items()
)


SYSTEM_PROMPT = f"""
당신은 한국어 의류 고객 리뷰를 구조화하는 분석기다.
리뷰에 명시된 상품 속성에 대한 만족과 불만만 추출한다.

[허용 taxonomy]
{TAXONOMY_PROMPT}

[허용 opinion_code]
{OPINION_CODE_PROMPT}

[규칙]
1. 한 리뷰에서 여러 Aspect를 추출할 수 있다.
2. positive 또는 negative가 명확한 의견만 추출하고 중립적 사실은 생략한다.
3. evidence는 입력 review_text에 실제로 연속해서 존재하는 최소한의 원문 구절이어야 한다.
4. evidence를 바꾸거나 요약하거나 맞춤법을 교정하지 않는다.
5. opinion은 evidence의 뜻을 짧고 구체적인 한국어 구절로 정규화한다.
6. opinion_code는 sentiment 방향과 일치하는 가장 구체적인 코드를 선택한다.
7. TOO_LONG/TOO_SHORT처럼 반대 방향의 불만을 같은 코드로 합치지 않는다.
8. evidence_start와 evidence_end는 null로 반환한다. 서버가 검증 후 계산한다.
9. 체형, 색상, 사이즈 등 Persona 정보는 추론하지 않는다.
10. 판매량, 반품률, 매출 영향 등 입력에 없는 사실을 만들지 않는다.
11. 명확한 상품 속성 의견이 없으면 aspects를 빈 배열로 반환한다.
""".strip()


class AspectAnalysisError(RuntimeError):
    pass


class AspectProvider(Protocol):
    model: str

    def analyze_batch(self, reviews: Sequence[dict[str, str]]) -> AspectBatchResponse:
        ...


class OpenAIAspectProvider:
    def __init__(self, model: str | None = None, client: Any | None = None) -> None:
        self.model = model or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise AspectAnalysisError("`pip install -r requirements.txt`를 먼저 실행하세요.") from exc
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API")
            if not api_key:
                raise AspectAnalysisError(".env에 OPENAI_API_KEY가 필요합니다.")
            client = OpenAI(api_key=api_key)
        self.client = client

    def analyze_batch(self, reviews: Sequence[dict[str, str]]) -> AspectBatchResponse:
        payload = {"reviews": list(reviews)}
        response = self.client.responses.parse(
            model=self.model,
            reasoning={"effort": "low"},
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                },
            ],
            text_format=AspectBatchResponse,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise AspectAnalysisError("OpenAI가 구조화된 분석 결과를 반환하지 않았습니다.")
        return parsed


def load_review_document(path: Path) -> tuple[str, list[dict[str, Any]]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AspectAnalysisError(f"리뷰 JSON을 읽을 수 없습니다: {path}: {exc}") from exc

    reviews = document.get("reviews") if isinstance(document, dict) else None
    if not isinstance(reviews, list) or not reviews:
        raise AspectAnalysisError(f"reviews 배열이 비어 있거나 없습니다: {path}")

    product_ids = {str(review.get("product_id") or "") for review in reviews if isinstance(review, dict)}
    if len(product_ids) != 1 or "" in product_ids:
        raise AspectAnalysisError(f"하나의 상품 ID로 구성된 리뷰 파일이어야 합니다: {path}")

    review_ids: set[str] = set()
    for index, review in enumerate(reviews):
        if not isinstance(review, dict):
            raise AspectAnalysisError(f"reviews[{index}]는 객체여야 합니다.")
        review_id = str(review.get("review_id") or "")
        text = review.get("review_text")
        if not review_id or review_id in review_ids:
            raise AspectAnalysisError(f"누락 또는 중복 review_id: index={index}, id={review_id!r}")
        if not isinstance(text, str) or not text.strip():
            raise AspectAnalysisError(f"review_text가 비어 있습니다: review_id={review_id}")
        review_ids.add(review_id)

    return next(iter(product_ids)), reviews


def _validate_extracted_batch(
    source_reviews: Sequence[dict[str, Any]],
    extracted: AspectBatchResponse,
) -> dict[str, ExtractedReview]:
    source_by_id = {str(review["review_id"]): review for review in source_reviews}
    extracted_by_id: dict[str, ExtractedReview] = {}

    for result in extracted.reviews:
        if result.review_id in extracted_by_id:
            raise AspectAnalysisError(f"모델 결과에 중복 review_id가 있습니다: {result.review_id}")
        if result.review_id not in source_by_id:
            raise AspectAnalysisError(f"모델이 알 수 없는 review_id를 반환했습니다: {result.review_id}")

        review_text = source_by_id[result.review_id]["review_text"]
        seen_mentions: set[tuple[str, str, str, str]] = set()
        validated_mentions = []
        for mention in result.aspects:
            if mention.evidence not in review_text:
                raise AspectAnalysisError(
                    f"근거가 리뷰 원문에 없습니다: review_id={result.review_id}, evidence={mention.evidence!r}"
                )
            key = (
                mention.category.value,
                mention.aspect.value,
                mention.sentiment.value,
                mention.evidence,
            )
            if key in seen_mentions:
                raise AspectAnalysisError(f"중복 Aspect 근거입니다: review_id={result.review_id}, key={key}")
            seen_mentions.add(key)
            start = review_text.index(mention.evidence)
            validated_mentions.append(
                mention.model_copy(
                    update={"evidence_start": start, "evidence_end": start + len(mention.evidence)}
                )
            )
        extracted_by_id[result.review_id] = result.model_copy(update={"aspects": validated_mentions})

    missing = set(source_by_id) - set(extracted_by_id)
    if missing:
        raise AspectAnalysisError("모델 결과에서 review_id가 누락됐습니다: " + ", ".join(sorted(missing)))
    return extracted_by_id


def summarize_aspects(analyses: Sequence[ReviewAnalysis]) -> list[AspectSummary]:
    counts: dict[tuple[AspectCategory, Aspect], dict[Sentiment, set[str]]] = defaultdict(
        lambda: {Sentiment.POSITIVE: set(), Sentiment.NEGATIVE: set()}
    )
    for analysis in analyses:
        for mention in analysis.aspects:
            counts[(mention.category, mention.aspect)][mention.sentiment].add(analysis.review_id)

    return [
        AspectSummary(
            category=category,
            aspect=aspect,
            positive_reviews=len(counts[(category, aspect)][Sentiment.POSITIVE]),
            negative_reviews=len(counts[(category, aspect)][Sentiment.NEGATIVE]),
        )
        for category, aspect in sorted(counts, key=lambda item: (item[0].value, item[1].value))
    ]


def calculate_source_hash(reviews: Sequence[dict[str, Any]]) -> str:
    def normalized_date(value: Any) -> Any:
        return value.isoformat() if isinstance(value, (date, datetime)) else value

    canonical = [
        {
            "product_id": str(review.get("product_id") or ""),
            "review_id": str(review.get("review_id") or review.get("source_review_id") or ""),
            "review_text": review.get("review_text"),
            "encrypted_user_id": review.get("encrypted_user_id") or None,
            "reviewed_at": normalized_date(
                review.get("date") or review.get("reviewed_at") or None
            ),
            "like_count": int(review.get("like_count") or 0),
            "reviewer_gender": review.get("reviewer_gender") or None,
            "reviewer_height_cm": review.get("reviewer_height_cm"),
            "reviewer_weight_kg": review.get("reviewer_weight_kg"),
            "purchased_option": review.get("option") or review.get("purchased_option") or None,
        }
        for review in reviews
    ]
    encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def analyze_reviews(
    reviews: Sequence[dict[str, Any]],
    provider: AspectProvider,
    *,
    batch_size: int = 10,
    existing: Sequence[ReviewAnalysis] = (),
    max_attempts: int = 2,
    retry_delay_seconds: float = 1.0,
    on_batch: Callable[[list[ReviewAnalysis]], None] | None = None,
) -> list[ReviewAnalysis]:
    if batch_size < 1 or batch_size > 50:
        raise ValueError("batch_size는 1~50이어야 합니다.")
    if max_attempts < 1:
        raise ValueError("max_attempts는 1 이상이어야 합니다.")
    if retry_delay_seconds < 0:
        raise ValueError("retry_delay_seconds는 0 이상이어야 합니다.")

    source_by_id = {str(review["review_id"]): review for review in reviews}
    analyses_by_id: dict[str, ReviewAnalysis] = {}
    for analysis in existing:
        if analysis.review_id in analyses_by_id:
            raise AspectAnalysisError(f"체크포인트에 중복 review_id가 있습니다: {analysis.review_id}")
        review = source_by_id.get(analysis.review_id)
        if review is None:
            raise AspectAnalysisError(f"체크포인트에 원본에 없는 review_id가 있습니다: {analysis.review_id}")
        if analysis.persona != persona_from_review(review):
            raise AspectAnalysisError(f"체크포인트 Persona가 원본과 다릅니다: {analysis.review_id}")
        review_text = str(review["review_text"])
        for mention in analysis.aspects:
            if mention.evidence_start is None or mention.evidence_end is None:
                raise AspectAnalysisError(f"체크포인트 Evidence offset이 없습니다: {analysis.review_id}")
            if review_text[mention.evidence_start : mention.evidence_end] != mention.evidence:
                raise AspectAnalysisError(f"체크포인트 Evidence가 원문과 다릅니다: {analysis.review_id}")
        analyses_by_id[analysis.review_id] = analysis
    pending = [review for review in reviews if str(review["review_id"]) not in analyses_by_id]

    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        request_reviews = [
            {"review_id": str(review["review_id"]), "review_text": review["review_text"]}
            for review in batch
        ]
        if any(len(review["review_text"]) > MAX_REVIEW_CHARS for review in request_reviews):
            raise AspectAnalysisError(f"리뷰 한 건이 {MAX_REVIEW_CHARS}자를 초과합니다.")
        if sum(len(review["review_text"]) for review in request_reviews) > MAX_BATCH_CHARS:
            raise AspectAnalysisError(
                f"배치 리뷰 본문이 {MAX_BATCH_CHARS}자를 초과합니다. batch_size를 줄이세요."
            )

        last_error: Exception | None = None
        extracted_by_id: dict[str, ExtractedReview] | None = None
        for attempt in range(max_attempts):
            try:
                extracted = provider.analyze_batch(request_reviews)
            except Exception as exc:
                last_error = exc
                if not _is_transient_provider_error(exc) or attempt + 1 >= max_attempts:
                    break
                if retry_delay_seconds:
                    time.sleep(retry_delay_seconds * (2**attempt) + random.uniform(0, 0.25))
                continue
            # 원문에 없는 Evidence나 잘못된 ID는 재시도로 숨기지 않고 즉시 실패한다.
            extracted_by_id = _validate_extracted_batch(batch, extracted)
            break
        if extracted_by_id is None:
            raise AspectAnalysisError(f"Aspect 분석 배치가 {max_attempts}회 실패했습니다: {last_error}")

        for review in batch:
            review_id = str(review["review_id"])
            result = extracted_by_id[review_id]
            analyses_by_id[review_id] = ReviewAnalysis(
                review_id=review_id,
                persona=persona_from_review(review),
                aspects=result.aspects,
            )

        ordered = [analyses_by_id[str(review["review_id"])] for review in reviews if str(review["review_id"]) in analyses_by_id]
        if on_batch:
            on_batch(ordered)

    return [analyses_by_id[str(review["review_id"])] for review in reviews]


def _is_transient_provider_error(exc: Exception) -> bool:
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True
    status_code = getattr(exc, "status_code", None)
    if status_code in {408, 409, 429} or isinstance(status_code, int) and status_code >= 500:
        return True
    return exc.__class__.__name__ in {
        "APIConnectionError",
        "APITimeoutError",
        "RateLimitError",
        "InternalServerError",
    }


def build_artifact(
    product_id: str,
    model: str,
    source_hash: str,
    total_reviews: int,
    analyses: Sequence[ReviewAnalysis],
    *,
    completed: bool,
    source_review_count: int | None = None,
) -> AspectAnalysisArtifact:
    return AspectAnalysisArtifact(
        taxonomy_version=TAXONOMY_VERSION,
        prompt_version=PROMPT_VERSION,
        status="completed" if completed else "in_progress",
        product_id=product_id,
        model=model,
        source_hash=source_hash,
        total_reviews=total_reviews,
        source_review_count=source_review_count if source_review_count is not None else total_reviews,
        is_sample=(source_review_count if source_review_count is not None else total_reviews) > total_reviews,
        analyzed_reviews=len(analyses),
        analyses=list(analyses),
        summary=summarize_aspects(analyses),
    )


def write_artifact(path: Path, artifact: AspectAnalysisArtifact) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    temp_path.replace(path)
