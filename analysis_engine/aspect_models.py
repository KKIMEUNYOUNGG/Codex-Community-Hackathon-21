from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .aspect_taxonomy import CATEGORY_ASPECTS, TAXONOMY_VERSION, Aspect, AspectCategory
from .aspect_taxonomy import (
    NEGATIVE_OPINION_CODES,
    OPINION_ALLOWED_ASPECTS,
    POSITIVE_OPINION_CODES,
    OpinionCode,
)


F03_SCHEMA_VERSION = "f03-aspect-v2"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


class Persona(StrictModel):
    gender: str | None = None
    height_cm: int | None = None
    weight_kg: int | None = None
    color: str | None = None
    size: str | None = None


class AspectMention(StrictModel):
    category: AspectCategory
    aspect: Aspect
    sentiment: Sentiment
    opinion_code: OpinionCode
    evidence: str = Field(min_length=1, max_length=300)
    evidence_start: int | None = Field(default=None, ge=0)
    evidence_end: int | None = Field(default=None, ge=1)
    opinion: str = Field(
        min_length=1,
        max_length=100,
        description="근거가 뜻하는 고객 의견을 짧은 한국어 구절로 정규화한 값",
    )

    @model_validator(mode="after")
    def category_matches_aspect(self) -> "AspectMention":
        if self.aspect not in CATEGORY_ASPECTS[self.category]:
            raise ValueError(f"{self.aspect.value}은(는) {self.category.value}에 속하지 않습니다")
        if self.sentiment == Sentiment.POSITIVE and self.opinion_code not in POSITIVE_OPINION_CODES:
            raise ValueError("positive 감정에는 positive opinion_code가 필요합니다")
        if self.sentiment == Sentiment.NEGATIVE and self.opinion_code not in NEGATIVE_OPINION_CODES:
            raise ValueError("negative 감정에는 negative opinion_code가 필요합니다")
        if self.aspect not in OPINION_ALLOWED_ASPECTS[self.opinion_code]:
            raise ValueError(
                f"{self.opinion_code.value}은(는) {self.aspect.value}에 사용할 수 없습니다"
            )
        if (self.evidence_start is None) != (self.evidence_end is None):
            raise ValueError("evidence_start와 evidence_end는 함께 제공해야 합니다")
        if self.evidence_start is not None and self.evidence_end is not None:
            if self.evidence_end <= self.evidence_start:
                raise ValueError("evidence_end는 evidence_start보다 커야 합니다")
            if self.evidence_end - self.evidence_start != len(self.evidence):
                raise ValueError("evidence offset 길이가 evidence 문자열 길이와 다릅니다")
        return self


class ExtractedReview(StrictModel):
    review_id: str = Field(min_length=1)
    aspects: list[AspectMention] = Field(default_factory=list)


class AspectBatchResponse(StrictModel):
    reviews: list[ExtractedReview] = Field(default_factory=list)


class ReviewAnalysis(StrictModel):
    review_id: str = Field(min_length=1)
    persona: Persona
    aspects: list[AspectMention]


class AspectSummary(StrictModel):
    category: AspectCategory
    aspect: Aspect
    positive_reviews: int = Field(ge=0)
    negative_reviews: int = Field(ge=0)


class AspectAnalysisArtifact(StrictModel):
    schema_version: Literal["f03-aspect-v2"] = F03_SCHEMA_VERSION
    taxonomy_version: str = TAXONOMY_VERSION
    prompt_version: str = "f03-aspect-v3"
    source_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["in_progress", "completed"]
    product_id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_reviews: int = Field(ge=0)
    source_review_count: int | None = Field(default=None, ge=0)
    is_sample: bool = False
    analyzed_reviews: int = Field(ge=0)
    analyses: list[ReviewAnalysis]
    summary: list[AspectSummary]

    @model_validator(mode="after")
    def counts_and_review_ids_are_consistent(self) -> "AspectAnalysisArtifact":
        if self.source_review_count is None:
            self.source_review_count = self.total_reviews
        if self.total_reviews > self.source_review_count:
            raise ValueError("total_reviews는 source_review_count보다 클 수 없습니다")
        if self.is_sample != (self.total_reviews < self.source_review_count):
            raise ValueError("is_sample이 source/selected review 수와 일치하지 않습니다")
        review_ids = [analysis.review_id for analysis in self.analyses]
        if len(review_ids) != len(set(review_ids)):
            raise ValueError("analyses에 중복 review_id가 있습니다")
        if self.analyzed_reviews != len(self.analyses):
            raise ValueError("analyzed_reviews와 analyses 길이가 다릅니다")
        if self.analyzed_reviews > self.total_reviews:
            raise ValueError("analyzed_reviews는 total_reviews보다 클 수 없습니다")
        if self.status == "completed" and self.analyzed_reviews != self.total_reviews:
            raise ValueError("completed artifact는 모든 리뷰 분석을 포함해야 합니다")
        return self
