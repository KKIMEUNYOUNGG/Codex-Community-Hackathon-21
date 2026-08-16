from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal

from pydantic import Field, model_validator

from .aspect_models import StrictModel
from .aspect_taxonomy import Aspect, AspectCategory, OpinionCode


class EvidenceRef(StrictModel):
    review_id: str = Field(min_length=1)
    evidence: str = Field(min_length=1)


class PersonaAspectInsight(StrictModel):
    dimensions: list[str]
    segment: dict[str, str]
    segment_review_count: int = Field(ge=1)
    category: AspectCategory
    aspect: Aspect
    opinion_code: OpinionCode
    mentioned_reviews: int = Field(ge=1)
    positive_reviews: int = Field(ge=0)
    negative_reviews: int = Field(ge=0)
    positive_ratio: float = Field(ge=0, le=1)
    negative_ratio: float = Field(ge=0, le=1)
    mention_rate: float = Field(ge=0, le=1)
    baseline_rate: float = Field(ge=0, le=1)
    lift: float = Field(ge=0)
    dimension_coverage: float = Field(ge=0, le=1)
    coverage_warning: bool
    is_insight: bool
    insight_kind: Literal["positive", "negative"] | None
    evidence: list[EvidenceRef]


class PersonaAspectSummary(StrictModel):
    dimensions: list[str]
    segment: dict[str, str]
    segment_review_count: int = Field(ge=1)
    category: AspectCategory
    aspect: Aspect
    mentioned_reviews: int = Field(ge=1)
    positive_reviews: int = Field(ge=0)
    negative_reviews: int = Field(ge=0)
    positive_ratio: float = Field(ge=0, le=1)
    negative_ratio: float = Field(ge=0, le=1)
    mention_rate: float = Field(ge=0, le=1)
    dimension_coverage: float = Field(ge=0, le=1)
    coverage_warning: bool
    evidence: list[EvidenceRef]


class OpinionCount(StrictModel):
    opinion: str
    review_count: int = Field(ge=1)


class Issue(StrictModel):
    issue_id: str
    title: str
    category: AspectCategory
    aspect: Aspect
    opinion_code: OpinionCode
    related_review_count: int = Field(ge=1)
    aspect_review_count: int = Field(ge=1)
    negative_ratio: float = Field(ge=0, le=1)
    mention_count: int = Field(ge=1)
    first_seen_at: str | None = None
    last_seen_at: str | None = None
    threshold_version: Literal["issue-v1"] = "issue-v1"
    affected_personas: list[str]
    dominant_opinions: list[OpinionCount]
    review_ids: list[str]
    evidence: list[EvidenceRef]

    @model_validator(mode="after")
    def counts_and_evidence_are_consistent(self) -> "Issue":
        ids = set(self.review_ids)
        if len(ids) != len(self.review_ids) or len(ids) != self.related_review_count:
            raise ValueError("Issue review_ids와 related_review_count가 일치하지 않습니다")
        if self.related_review_count > self.aspect_review_count:
            raise ValueError("Issue 관련 리뷰 수는 Aspect 리뷰 수보다 클 수 없습니다")
        if abs(self.negative_ratio - self.related_review_count / self.aspect_review_count) > 0.0001:
            raise ValueError("Issue negative_ratio가 리뷰 수와 일치하지 않습니다")
        if any(item.review_id not in ids for item in self.evidence):
            raise ValueError("Issue evidence는 관련 review_id를 참조해야 합니다")
        return self


class Strength(StrictModel):
    strength_id: str
    title: str
    category: AspectCategory
    aspect: Aspect
    opinion_code: OpinionCode
    related_review_count: int = Field(ge=1)
    aspect_review_count: int = Field(ge=1)
    positive_ratio: float = Field(ge=0, le=1)
    score: float = Field(ge=0, le=100)
    mention_count: int = Field(ge=1)
    first_seen_at: str | None = None
    last_seen_at: str | None = None
    threshold_version: Literal["strength-v1"] = "strength-v1"
    affected_personas: list[str]
    dominant_opinions: list[OpinionCount]
    review_ids: list[str]
    evidence: list[EvidenceRef]

    @model_validator(mode="after")
    def counts_and_evidence_are_consistent(self) -> "Strength":
        ids = set(self.review_ids)
        if len(ids) != len(self.review_ids) or len(ids) != self.related_review_count:
            raise ValueError("Strength review_ids와 related_review_count가 일치하지 않습니다")
        if self.related_review_count > self.aspect_review_count:
            raise ValueError("Strength 관련 리뷰 수는 Aspect 리뷰 수보다 클 수 없습니다")
        if abs(self.positive_ratio - self.related_review_count / self.aspect_review_count) > 0.0001:
            raise ValueError("Strength positive_ratio가 리뷰 수와 일치하지 않습니다")
        if any(item.review_id not in ids for item in self.evidence):
            raise ValueError("Strength evidence는 관련 review_id를 참조해야 합니다")
        return self


class PriorityComponents(StrictModel):
    frequency: float = Field(ge=0, le=1)
    negative_ratio: float = Field(ge=0, le=1)
    affected_customer_breadth: float = Field(ge=0, le=1)
    recency: float = Field(ge=0, le=1)
    likes: float = Field(ge=0, le=1)


class ImprovementPriority(StrictModel):
    rank: int = Field(ge=1)
    issue_id: str
    title: str
    score: float = Field(ge=0, le=100)
    formula_version: Literal["priority-v1"] = "priority-v1"
    components: PriorityComponents
    reasons: list[str]
    review_ids: list[str]
    evidence: list[EvidenceRef]


class ProductInsightConfig(StrictModel):
    analysis_as_of: date
    input_review_count: int = Field(ge=0)
    deduplicated_review_count: int = Field(ge=0)
    issue_min_support: int = Field(ge=1)
    strength_min_support: int = Field(ge=1)
    support_rate: float = Field(default=0.02, ge=0, le=1)
    recency_half_life_days: int = Field(default=180, ge=1)
    deduplication: Literal["encrypted_user_id+normalized_text"] = (
        "encrypted_user_id+normalized_text"
    )
    priority_weights: dict[str, float]


class ProductInsightsArtifact(StrictModel):
    schema_version: Literal["f04-f07-v2"] = "f04-f07-v2"
    product_id: str
    source_aspect_schema_version: str
    source_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    taxonomy_version: str
    prompt_version: str
    source_review_count: int = Field(ge=0)
    selected_review_count: int = Field(ge=0)
    is_sample: bool
    analysis_config: ProductInsightConfig
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    analyzed_review_count: int = Field(ge=0)
    persona_aspect_summary: list[PersonaAspectSummary]
    persona_aspect: list[PersonaAspectInsight]
    issues: list[Issue]
    strengths: list[Strength]
    priorities: list[ImprovementPriority]

    @model_validator(mode="after")
    def artifact_links_are_consistent(self) -> "ProductInsightsArtifact":
        issue_ids = [item.issue_id for item in self.issues]
        strength_ids = [item.strength_id for item in self.strengths]
        if len(issue_ids) != len(set(issue_ids)):
            raise ValueError("중복 issue_id가 있습니다")
        if len(strength_ids) != len(set(strength_ids)):
            raise ValueError("중복 strength_id가 있습니다")
        if [item.rank for item in self.priorities] != list(range(1, len(self.priorities) + 1)):
            raise ValueError("Priority rank는 1부터 연속이어야 합니다")
        if any(item.issue_id not in set(issue_ids) for item in self.priorities):
            raise ValueError("Priority가 존재하지 않는 issue_id를 참조합니다")
        if self.analysis_config.deduplicated_review_count != self.analyzed_review_count:
            raise ValueError("deduplicated_review_count와 analyzed_review_count가 다릅니다")
        if self.analysis_config.input_review_count < self.analyzed_review_count:
            raise ValueError("입력 리뷰 수는 중복 제거 후 리뷰 수보다 작을 수 없습니다")
        if self.selected_review_count > self.source_review_count:
            raise ValueError("선택 리뷰 수는 원본 리뷰 수보다 클 수 없습니다")
        if self.is_sample != (self.selected_review_count < self.source_review_count):
            raise ValueError("ProductInsights is_sample 범위가 일치하지 않습니다")
        if self.analysis_config.input_review_count != self.selected_review_count:
            raise ValueError("selected_review_count와 분석 입력 리뷰 수가 다릅니다")
        return self
