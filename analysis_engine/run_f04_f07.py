from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from .pipeline import (
    build_product_insights,
    load_aspect_artifact,
    load_raw_reviews,
    write_product_insights,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="F04~F07: Persona 교차분석·Issue·Strength·개선 우선순위")
    parser.add_argument("--reviews", type=Path, required=True, help="원본 *_reviews.json")
    parser.add_argument("--aspects", type=Path, required=True, help="F03 *_review_analyses.json")
    parser.add_argument("--output", type=Path, help="F04~F07 결과 JSON")
    parser.add_argument("--min-issue-support", type=int)
    parser.add_argument("--min-strength-support", type=int)
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        help="최근성 분석 기준일 YYYY-MM-DD (기본값: 실행일)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        aspect_artifact = load_aspect_artifact(args.aspects)
        output = args.output or (
            PROJECT_ROOT / "analysis_outputs" / f"{aspect_artifact.product_id}_product_insights.json"
        )
        result = build_product_insights(
            aspect_artifact,
            load_raw_reviews(args.reviews),
            min_issue_support=args.min_issue_support,
            min_strength_support=args.min_strength_support,
            analysis_as_of=args.as_of,
        )
        write_product_insights(output, result)
    except Exception as exc:
        print(f"[실패] {exc}")
        return 1

    print(
        f"[완료] 상품 {result.product_id}: Persona×Aspect 표 "
        f"{len(result.persona_aspect_summary)}개, 집중 인사이트 {len(result.persona_aspect)}개, "
        f"Issue {len(result.issues)}개, Strength {len(result.strengths)}개 → {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
