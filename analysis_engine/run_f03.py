from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from .aspect_models import F03_SCHEMA_VERSION, AspectAnalysisArtifact
from .aspect_taxonomy import TAXONOMY_VERSION
from .f03_aspect_analysis import (
    OpenAIAspectProvider,
    PROMPT_VERSION,
    analyze_reviews,
    build_artifact,
    calculate_source_hash,
    load_review_document,
    write_artifact,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="F03: 리뷰별 Aspect·감정·Evidence 추출")
    parser.add_argument("--input", type=Path, required=True, help="*_reviews.json")
    parser.add_argument("--output", type=Path, help="분석 결과 JSON")
    parser.add_argument("--model", help="기본값: OPENAI_MODEL 또는 gpt-5.6-luna")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--limit", type=int, help="개발 확인용 앞 N개 리뷰")
    parser.add_argument("--overwrite", action="store_true", help="기존 체크포인트 무시")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv(PROJECT_ROOT / ".env")
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API")):
        print("[실패] .env에 OPENAI_API_KEY가 필요합니다. (OPENAI_API도 호환 지원)")
        return 1

    try:
        product_id, all_reviews = load_review_document(args.input)
        if args.limit is not None and args.limit < 1:
            raise ValueError("--limit은 1 이상이어야 합니다.")
        reviews = all_reviews[: args.limit] if args.limit else all_reviews
        source_hash = calculate_source_hash(reviews)
        output = args.output or PROJECT_ROOT / "analysis_outputs" / f"{product_id}_review_analyses.json"
        provider = OpenAIAspectProvider(model=args.model)

        existing = []
        if output.exists() and not args.overwrite:
            previous = AspectAnalysisArtifact.model_validate_json(output.read_text(encoding="utf-8"))
            if (
                previous.product_id != product_id
                or previous.schema_version != F03_SCHEMA_VERSION
                or previous.model != provider.model
                or previous.source_hash != source_hash
                or previous.prompt_version != PROMPT_VERSION
                or previous.taxonomy_version != TAXONOMY_VERSION
            ):
                raise ValueError(
                    "기존 결과의 상품·모델·원본 hash·분석 버전이 다릅니다. "
                    "--overwrite를 사용하세요."
                )
            existing = previous.analyses

        def checkpoint(current):
            artifact = build_artifact(
                product_id,
                provider.model,
                source_hash,
                len(reviews),
                current,
                completed=False,
                source_review_count=len(all_reviews),
            )
            write_artifact(output, artifact)
            print(f"[진행] {len(current)}/{len(reviews)}")

        analyses = analyze_reviews(
            reviews,
            provider,
            batch_size=args.batch_size,
            existing=existing,
            on_batch=checkpoint,
        )
        artifact = build_artifact(
            product_id,
            provider.model,
            source_hash,
            len(reviews),
            analyses,
            completed=True,
            source_review_count=len(all_reviews),
        )
        write_artifact(output, artifact)
    except Exception as exc:
        print(f"[실패] {exc}")
        return 1

    print(f"[완료] 상품 {product_id}: 리뷰 {len(analyses)}개 분석 → {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
