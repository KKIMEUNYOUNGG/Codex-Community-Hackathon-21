from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from analysis_engine.aspect_models import (  # noqa: E402
    AspectBatchResponse,
    AspectMention,
    ExtractedReview,
    Persona,
    ReviewAnalysis,
    Sentiment,
)
from analysis_engine.aspect_taxonomy import (  # noqa: E402
    Aspect,
    AspectCategory,
    OpinionCode,
)
from analysis_engine.f03_aspect_analysis import (  # noqa: E402
    AspectAnalysisError,
    analyze_reviews,
    build_artifact,
    calculate_source_hash,
    load_review_document,
    summarize_aspects,
)
from analysis_engine.f04_persona_aspect import analyze_persona_aspects  # noqa: E402
from analysis_engine.f04_persona_aspect import summarize_persona_aspects  # noqa: E402
from analysis_engine.f05_issues import detect_issues  # noqa: E402
from analysis_engine.f06_strengths import detect_strengths  # noqa: E402
from analysis_engine.f07_priorities import rank_improvement_priorities  # noqa: E402
from analysis_engine.persona import parse_color_and_size, persona_from_review  # noqa: E402
from analysis_engine.pipeline import ProductInsightError, build_product_insights  # noqa: E402
from analysis_engine.aggregation_utils import average_recency, raw_reviews_by_id  # noqa: E402


def make_raw(
    index: int,
    text: str,
    *,
    height: int | None = None,
    weight: int | None = None,
    option: str | None = "BROWN · M",
    gender: str | None = "여성",
    reviewed_at: str = "2026-08-01",
    likes: int = 0,
) -> dict[str, object]:
    return {
        "product_id": "p1",
        "review_id": f"r{index}",
        "encrypted_user_id": f"u{index}",
        "review_text": text,
        "reviewer_gender": gender,
        "reviewer_height_cm": height,
        "reviewer_weight_kg": weight,
        "option": option,
        "date": reviewed_at,
        "like_count": likes,
    }


def make_mention(
    evidence: str,
    *,
    aspect: Aspect = Aspect.SLEEVE_LENGTH,
    category: AspectCategory = AspectCategory.SIZE_FIT,
    sentiment: Sentiment = Sentiment.NEGATIVE,
    opinion_code: OpinionCode = OpinionCode.TOO_LONG,
    opinion: str = "소매가 김",
    source_text: str | None = None,
) -> AspectMention:
    offsets: dict[str, int] = {}
    if source_text is not None:
        start = source_text.index(evidence)
        offsets = {"evidence_start": start, "evidence_end": start + len(evidence)}
    return AspectMention(
        category=category,
        aspect=aspect,
        sentiment=sentiment,
        opinion_code=opinion_code,
        evidence=evidence,
        opinion=opinion,
        **offsets,
    )


class StaticProvider:
    model = "fake-model"

    def __init__(self, response: AspectBatchResponse, failures: list[Exception] | None = None) -> None:
        self.response = response
        self.failures = list(failures or [])
        self.calls = 0

    def analyze_batch(self, _reviews):
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return self.response


class AnalysisContractTests(unittest.TestCase):
    def test_rejects_taxonomy_sentiment_and_bad_offsets(self) -> None:
        with self.assertRaises(ValidationError):
            make_mention(
                "예뻐요",
                aspect=Aspect.COLOR,
                category=AspectCategory.DESIGN,
                sentiment=Sentiment.POSITIVE,
                opinion_code=OpinionCode.GOOD_COLOR,
            )
        with self.assertRaises(ValidationError):
            make_mention(
                "길어요",
                sentiment=Sentiment.POSITIVE,
                opinion_code=OpinionCode.TOO_LONG,
            )
        with self.assertRaises(ValidationError):
            AspectMention(
                category=AspectCategory.SIZE_FIT,
                aspect=Aspect.SLEEVE_LENGTH,
                sentiment=Sentiment.NEGATIVE,
                opinion_code=OpinionCode.TOO_LONG,
                evidence="길어요",
                evidence_start=0,
                evidence_end=2,
                opinion="소매가 김",
            )
        with self.assertRaises(ValidationError):
            make_mention(
                "너무 길어요",
                aspect=Aspect.THICKNESS,
                category=AspectCategory.MATERIAL,
                opinion_code=OpinionCode.TOO_LONG,
            )

    def test_persona_is_normalized_from_raw_metadata(self) -> None:
        self.assertEqual(parse_color_and_size("BROWN · M"), ("BROWN", "M"))
        self.assertEqual(parse_color_and_size("색상: ivory / 사이즈: 00s"), ("IVORY", "00S"))
        self.assertEqual(parse_color_and_size("XXL"), (None, "XXL"))
        persona = persona_from_review(
            {"reviewer_gender": "female", "purchased_option": "navy | 2XL"}
        )
        self.assertEqual(persona.gender, "여성")
        self.assertEqual((persona.color, persona.size), ("NAVY", "2XL"))

    def test_f03_validates_exact_evidence_and_computes_offsets(self) -> None:
        raw = make_raw(1, "색은 예쁜데 소매가 길어요", height=162)
        response = AspectBatchResponse(
            reviews=[
                ExtractedReview(
                    review_id="r1",
                    aspects=[make_mention("소매가 길어요")],
                )
            ]
        )
        provider = StaticProvider(response)
        analyses = analyze_reviews([raw], provider, retry_delay_seconds=0)
        mention = analyses[0].aspects[0]
        self.assertEqual(raw["review_text"][mention.evidence_start : mention.evidence_end], mention.evidence)
        self.assertEqual(analyses[0].persona.height_cm, 162)

    def test_f03_does_not_retry_hallucinated_evidence(self) -> None:
        raw = make_raw(1, "소매가 길어요")
        provider = StaticProvider(
            AspectBatchResponse(
                reviews=[ExtractedReview(review_id="r1", aspects=[make_mention("원문에 없음")])]
            )
        )
        with self.assertRaises(AspectAnalysisError):
            analyze_reviews([raw], provider, max_attempts=3, retry_delay_seconds=0)
        self.assertEqual(provider.calls, 1)

    def test_f03_retries_transient_provider_error(self) -> None:
        raw = make_raw(1, "소매가 길어요")
        provider = StaticProvider(
            AspectBatchResponse(
                reviews=[ExtractedReview(review_id="r1", aspects=[make_mention("소매가 길어요")])]
            ),
            failures=[ConnectionError("temporary")],
        )
        self.assertEqual(
            len(analyze_reviews([raw], provider, max_attempts=2, retry_delay_seconds=0)),
            1,
        )
        self.assertEqual(provider.calls, 2)

    def test_f03_summary_keeps_detailed_aspects_separate(self) -> None:
        analyses = [
            ReviewAnalysis(
                review_id="r1",
                persona=Persona(),
                aspects=[
                    make_mention("소매가 길어요"),
                    make_mention(
                        "얇아요",
                        aspect=Aspect.THICKNESS,
                        category=AspectCategory.MATERIAL,
                        opinion_code=OpinionCode.TOO_THIN,
                        opinion="원단이 얇음",
                    ),
                ],
            )
        ]
        summary = summarize_aspects(analyses)
        self.assertEqual({item.aspect for item in summary}, {Aspect.SLEEVE_LENGTH, Aspect.THICKNESS})

    def test_source_hash_includes_every_downstream_signal(self) -> None:
        first = make_raw(1, "좋아요", height=160)
        for changed in (
            dict(first, reviewer_height_cm=165),
            dict(first, date="2020-01-01"),
            dict(first, like_count=99),
            dict(first, encrypted_user_id="another-user"),
        ):
            self.assertNotEqual(calculate_source_hash([first]), calculate_source_hash([changed]))

        db_alias = dict(first)
        db_alias["source_review_id"] = db_alias.pop("review_id")
        db_alias["reviewed_at"] = db_alias.pop("date")
        db_alias["purchased_option"] = db_alias.pop("option")
        self.assertEqual(calculate_source_hash([first]), calculate_source_hash([db_alias]))

    def test_artifact_records_sample_scope_and_rejects_false_completion(self) -> None:
        raw = make_raw(1, "소매가 길어요")
        analysis = ReviewAnalysis(review_id="r1", persona=persona_from_review(raw), aspects=[])
        artifact = build_artifact(
            "p1",
            "fake",
            calculate_source_hash([raw]),
            1,
            [analysis],
            completed=True,
            source_review_count=10,
        )
        self.assertTrue(artifact.is_sample)
        self.assertEqual(artifact.source_review_count, 10)
        with self.assertRaises(ValidationError):
            build_artifact(
                "p1",
                "fake",
                calculate_source_hash([raw]),
                2,
                [analysis],
                completed=True,
            )


class AggregateFeatureTests(unittest.TestCase):
    def test_f04_finds_height_size_concentration_and_keeps_direction(self) -> None:
        analyses: list[ReviewAnalysis] = []
        for index in range(20):
            persona = Persona(height_cm=162 if index < 5 else 172, size="M")
            aspects = [make_mention("길어요")] if index < 3 else []
            analyses.append(ReviewAnalysis(review_id=f"r{index}", persona=persona, aspects=aspects))
        insights = analyze_persona_aspects(
            analyses,
            dimension_sets=(("height_band", "size"),),
        )
        target = next(item for item in insights if item.segment["height_band"] == "160~164cm")
        self.assertTrue(target.is_insight)
        self.assertEqual(target.insight_kind, "negative")
        self.assertEqual(target.opinion_code, OpinionCode.TOO_LONG)
        self.assertGreaterEqual(target.lift, 1.5)

    def test_f04_also_produces_aspect_level_positive_negative_rollup(self) -> None:
        analyses = []
        for index in range(5):
            aspects = []
            if index == 0:
                aspects = [
                    make_mention(
                        "길이가 좋아요",
                        aspect=Aspect.LENGTH,
                        sentiment=Sentiment.POSITIVE,
                        opinion_code=OpinionCode.GOOD_LENGTH,
                        opinion="길이가 적절함",
                    )
                ]
            elif index == 1:
                aspects = [
                    make_mention(
                        "기장이 길어요",
                        aspect=Aspect.LENGTH,
                        opinion_code=OpinionCode.TOO_LONG,
                        opinion="기장이 김",
                    )
                ]
            analyses.append(
                ReviewAnalysis(review_id=f"r{index}", persona=Persona(size="M"), aspects=aspects)
            )
        summaries = summarize_persona_aspects(
            analyses,
            dimension_sets=(("size",),),
            min_segment_reviews=5,
        )
        self.assertEqual(len(summaries), 1)
        self.assertEqual((summaries[0].positive_reviews, summaries[0].negative_reviews), (1, 1))
        self.assertEqual((summaries[0].positive_ratio, summaries[0].negative_ratio), (0.5, 0.5))

    def test_f05_and_f06_group_unique_reviews_by_direction(self) -> None:
        raw_reviews = [make_raw(i, f"리뷰 {i}") for i in range(1, 11)]
        analyses: list[ReviewAnalysis] = []
        for index in range(1, 11):
            aspects: list[AspectMention] = []
            if index <= 3:
                aspects.append(make_mention("길어요"))
            if 4 <= index <= 6:
                aspects.append(
                    make_mention(
                        "짧아요",
                        opinion_code=OpinionCode.TOO_SHORT,
                        opinion="소매가 짧음",
                    )
                )
            if 7 <= index <= 9:
                aspects.append(
                    make_mention(
                        "예뻐요",
                        aspect=Aspect.DESIGN,
                        category=AspectCategory.DESIGN,
                        sentiment=Sentiment.POSITIVE,
                        opinion_code=OpinionCode.GOOD_DESIGN,
                        opinion="디자인이 좋음",
                    )
                )
            analyses.append(ReviewAnalysis(review_id=f"r{index}", persona=Persona(), aspects=aspects))

        issues = detect_issues("p1", analyses, raw_reviews)
        strengths = detect_strengths("p1", analyses, raw_reviews)
        self.assertEqual({item.opinion_code for item in issues}, {OpinionCode.TOO_LONG, OpinionCode.TOO_SHORT})
        self.assertEqual(strengths[0].opinion_code, OpinionCode.GOOD_DESIGN)
        self.assertEqual(strengths[0].related_review_count, 3)

    def test_f07_uses_only_review_signals_and_is_deterministic(self) -> None:
        raw_reviews: list[dict[str, object]] = []
        analyses: list[ReviewAnalysis] = []
        for index in range(1, 21):
            is_long = index <= 5
            is_short = 6 <= index <= 8
            reviewed_at = "2026-08-15" if is_long else "2025-01-01"
            raw_reviews.append(make_raw(index, f"리뷰 {index}", reviewed_at=reviewed_at, likes=10 if is_long else 0))
            aspects = []
            if is_long:
                aspects = [make_mention("길어요")]
            elif is_short:
                aspects = [make_mention("짧아요", opinion_code=OpinionCode.TOO_SHORT, opinion="소매가 짧음")]
            analyses.append(ReviewAnalysis(review_id=f"r{index}", persona=Persona(), aspects=aspects))
        issues = detect_issues("p1", analyses, raw_reviews)
        priorities = rank_improvement_priorities(issues, analyses, raw_reviews)
        self.assertEqual(priorities[0].title, next(item.title for item in issues if item.opinion_code == OpinionCode.TOO_LONG))
        self.assertEqual([item.rank for item in priorities], [1, 2])
        self.assertGreater(priorities[0].score, priorities[1].score)
        components_by_issue = {item.issue_id: item.components for item in priorities}
        long_issue = next(item for item in issues if item.opinion_code == OpinionCode.TOO_LONG)
        short_issue = next(item for item in issues if item.opinion_code == OpinionCode.TOO_SHORT)
        self.assertEqual(components_by_issue[long_issue.issue_id].negative_ratio, 0.6)
        self.assertEqual(components_by_issue[short_issue.issue_id].negative_ratio, 0.4)
        self.assertEqual(
            priorities,
            rank_improvement_priorities(issues, analyses, raw_reviews),
        )

    def test_pipeline_rejects_stale_source_and_builds_all_outputs(self) -> None:
        texts = ["소매가 길어요", "소매가 아주 길어요", "디자인이 예뻐요"]
        raw_reviews = [make_raw(index, text) for index, text in enumerate(texts, start=1)]
        analyses = [
            ReviewAnalysis(
                review_id="r1",
                persona=persona_from_review(raw_reviews[0]),
                aspects=[make_mention("소매가 길어요", source_text=texts[0])],
            ),
            ReviewAnalysis(
                review_id="r2",
                persona=persona_from_review(raw_reviews[1]),
                aspects=[make_mention("길어요", source_text=texts[1])],
            ),
            ReviewAnalysis(
                review_id="r3",
                persona=persona_from_review(raw_reviews[2]),
                aspects=[
                    make_mention(
                        "디자인이 예뻐요",
                        aspect=Aspect.DESIGN,
                        category=AspectCategory.DESIGN,
                        sentiment=Sentiment.POSITIVE,
                        opinion_code=OpinionCode.GOOD_DESIGN,
                        opinion="디자인이 좋음",
                        source_text=texts[2],
                    )
                ],
            ),
        ]
        artifact = build_artifact(
            "p1",
            "fake-model",
            calculate_source_hash(raw_reviews),
            len(raw_reviews),
            analyses,
            completed=True,
        )
        result = build_product_insights(
            artifact,
            raw_reviews,
            min_issue_support=1,
            min_strength_support=1,
            analysis_as_of=date(2026, 8, 16),
        )
        self.assertEqual((len(result.issues), len(result.strengths), len(result.priorities)), (1, 1, 1))
        self.assertEqual(result.analysis_config.issue_min_support, 1)
        self.assertEqual(result.analysis_config.analysis_as_of, date(2026, 8, 16))
        self.assertEqual(
            (result.source_review_count, result.selected_review_count, result.is_sample),
            (3, 3, False),
        )
        stale = [dict(review) for review in raw_reviews]
        stale[0]["review_text"] = "원문 변경"
        with self.assertRaises(ProductInsightError):
            build_product_insights(artifact, stale, min_issue_support=1, min_strength_support=1)

        tampered_analysis = analyses[0].model_copy(update={"persona": Persona(size="XL")})
        tampered_artifact = build_artifact(
            "p1",
            "fake-model",
            calculate_source_hash(raw_reviews),
            len(raw_reviews),
            [tampered_analysis, *analyses[1:]],
            completed=True,
        )
        with self.assertRaises(ProductInsightError):
            build_product_insights(
                tampered_artifact,
                raw_reviews,
                min_issue_support=1,
                min_strength_support=1,
            )

    def test_recency_uses_absolute_analysis_date_and_missing_is_zero(self) -> None:
        old = make_raw(1, "오래된 리뷰", reviewed_at="2021-07-02")
        missing = make_raw(2, "날짜 없음")
        missing["date"] = None
        by_id = raw_reviews_by_id([old, missing])
        self.assertLess(
            average_recency(["r1"], by_id, analysis_as_of=date(2026, 8, 16)),
            0.01,
        )
        self.assertEqual(
            average_recency(["r2"], by_id, analysis_as_of=date(2026, 8, 16)),
            0.0,
        )
        recent = make_raw(3, "최신 리뷰", reviewed_at="2026-08-16")
        mixed = raw_reviews_by_id([missing, recent])
        self.assertEqual(
            average_recency(["r2", "r3"], mixed, analysis_as_of=date(2026, 8, 16)),
            0.5,
        )

    def test_three_crawler_fixtures_total_606_reviews(self) -> None:
        expected = {"1014752": 319, "4314937": 123, "5068730": 164}
        paths = {
            product_id: PROJECT_ROOT / "Crawler" / "outputs" / f"{product_id}_reviews.json"
            for product_id in expected
        }
        if any(not path.exists() for path in paths.values()):
            self.skipTest("로컬 crawler fixture가 없어 606건 통합 검증을 건너뜁니다")
        actual = {}
        for product_id, path in paths.items():
            loaded_id, reviews = load_review_document(path)
            actual[loaded_id] = len(reviews)
        self.assertEqual(actual, expected)
        self.assertEqual(sum(actual.values()), 606)


if __name__ == "__main__":
    unittest.main()
