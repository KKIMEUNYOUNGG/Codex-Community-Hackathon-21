"""Validate crawler JSON files and upsert matching product/review pairs to Supabase."""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit


PRODUCT_FILE_RE = re.compile(r"^(\d+)_product_details\.json$")
REVIEW_FILE_RE = re.compile(r"^(\d+)_reviews\.json$")


class DataValidationError(ValueError):
    """Crawler output does not satisfy the database contract."""


@dataclass(frozen=True)
class CrawlerOutputPair:
    product_id: str
    product_file: Path
    review_file: Path


def normalize_supabase_url(url: str) -> str:
    """Accept either the project URL or a copied REST endpoint URL."""
    parsed = urlsplit(url.strip().rstrip("/"))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("SUPABASE_URL 형식이 올바르지 않습니다.")
    path = parsed.path.rstrip("/")
    if path == "/rest/v1":
        path = ""
    elif path:
        raise RuntimeError("SUPABASE_URL에는 프로젝트 기본 URL만 입력해야 합니다.")
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DataValidationError(f"JSON을 읽을 수 없습니다: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise DataValidationError(f"JSON 최상위 값은 객체여야 합니다: {path}")
    return value


def discover_pairs(outputs_dir: Path, product_ids: Iterable[str] | None = None) -> list[CrawlerOutputPair]:
    if not outputs_dir.is_dir():
        raise DataValidationError(f"출력 폴더가 없습니다: {outputs_dir}")

    requested = set(product_ids or [])
    products: dict[str, Path] = {}
    reviews: dict[str, Path] = {}
    for path in outputs_dir.iterdir():
        product_match = PRODUCT_FILE_RE.match(path.name)
        review_match = REVIEW_FILE_RE.match(path.name)
        if product_match:
            products[product_match.group(1)] = path
        elif review_match:
            reviews[review_match.group(1)] = path

    if requested:
        missing = sorted(pid for pid in requested if pid not in products or pid not in reviews)
        if missing:
            raise DataValidationError(
                "상품정보/리뷰 JSON 한 쌍이 모두 필요합니다. 누락 상품 ID: " + ", ".join(missing)
            )
        pair_ids = sorted(requested)
    else:
        pair_ids = sorted(products.keys() & reviews.keys())

    if not pair_ids:
        product_only = sorted(products.keys() - reviews.keys())
        review_only = sorted(reviews.keys() - products.keys())
        raise DataValidationError(
            "서로 같은 상품 ID의 JSON 쌍이 없습니다. "
            f"상품정보만 존재={product_only}, 리뷰만 존재={review_only}"
        )

    return [CrawlerOutputPair(pid, products[pid], reviews[pid]) for pid in pair_ids]


def normalize_product(pair: CrawlerOutputPair) -> dict[str, Any]:
    document = read_json(pair.product_file)
    detail = document.get("product_detail")
    if not isinstance(detail, dict) or not detail:
        raise DataValidationError(f"product_detail이 비어 있습니다: {pair.product_file}")

    product_id = str(detail.get("product_id") or "")
    if product_id != pair.product_id:
        raise DataValidationError(
            f"상품 ID 불일치: 파일={pair.product_id}, 내용={product_id}: {pair.product_file}"
        )
    if not detail.get("url") or not detail.get("product_name"):
        raise DataValidationError(f"url과 product_name은 필수입니다: {pair.product_file}")

    return {
        "product_id": product_id,
        "source_url": detail["url"],
        "product_name": detail["product_name"],
        "brand_name": detail.get("brand_name") or None,
        "price": detail.get("price"),
        "rating": detail.get("rating"),
        "review_count": detail.get("review_count"),
        "description_summary": detail.get("Description") or None,
        "description_raw": detail.get("description_raw") or None,
        "main_image_url": detail.get("main_image_url") or None,
    }


def normalize_reviews(pair: CrawlerOutputPair) -> list[dict[str, Any]]:
    document = read_json(pair.review_file)
    reviews = document.get("reviews")
    if not isinstance(reviews, list):
        raise DataValidationError(f"reviews는 배열이어야 합니다: {pair.review_file}")

    normalized: list[dict[str, Any]] = []
    seen_review_ids: set[str] = set()
    for index, review in enumerate(reviews):
        if not isinstance(review, dict):
            raise DataValidationError(f"reviews[{index}]는 객체여야 합니다: {pair.review_file}")
        product_id = str(review.get("product_id") or "")
        review_id = str(review.get("review_id") or "")
        if product_id != pair.product_id:
            raise DataValidationError(
                f"리뷰 상품 ID 불일치: 기대={pair.product_id}, 내용={product_id}, index={index}"
            )
        if not review_id:
            raise DataValidationError(f"review_id가 없습니다: {pair.review_file}, index={index}")
        if review_id in seen_review_ids:
            raise DataValidationError(f"중복 review_id={review_id}: {pair.review_file}")
        seen_review_ids.add(review_id)

        normalized.append(
            {
                "product_id": product_id,
                "source_review_id": review_id,
                "encrypted_user_id": review.get("encrypted_user_id"),
                "reviewer_nickname": review.get("reviewer_nickname"),
                "reviewed_at": review.get("date"),
                "rating": review.get("rating"),
                "purchased_option": review.get("option"),
                "reviewer_level": review.get("reviewer_level"),
                "reviewer_gender": review.get("reviewer_gender"),
                "reviewer_height_cm": review.get("reviewer_height_cm"),
                "reviewer_weight_kg": review.get("reviewer_weight_kg"),
                "review_type": review.get("review_type"),
                "review_text": review.get("review_text"),
                "photo_urls": review.get("photo_urls") or [],
                "like_count": review.get("like_count") or 0,
                "source_data": review,
            }
        )
    return normalized


def chunks(rows: list[dict[str, Any]], size: int = 500) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def get_supabase_client():
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise RuntimeError("먼저 `pip install -r requirements.txt`를 실행하세요.") from exc

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL과 SUPABASE_SECRET_KEY(또는 legacy SUPABASE_SERVICE_ROLE_KEY)가 필요합니다."
        )
    try:
        from supabase import create_client
    except ImportError as exc:
        raise RuntimeError("먼저 `pip install -r requirements.txt`를 실행하세요.") from exc
    return create_client(normalize_supabase_url(url), key)


def upload_pairs(pairs: list[CrawlerOutputPair], dry_run: bool = False) -> tuple[int, int]:
    prepared = [(normalize_product(pair), normalize_reviews(pair)) for pair in pairs]
    product_count = len(prepared)
    review_count = sum(len(reviews) for _, reviews in prepared)
    if dry_run:
        return product_count, review_count

    client = get_supabase_client()
    try:
        for product, reviews in prepared:
            client.table("products").upsert(product, on_conflict="product_id").execute()
            for batch in chunks(reviews):
                client.table("raw_reviews").upsert(
                    batch,
                    on_conflict="product_id,source_review_id",
                ).execute()
    except Exception as exc:
        raise RuntimeError(f"Supabase 적재 중 오류가 발생했습니다: {exc}") from exc
    return product_count, review_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--outputs-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "outputs",
    )
    parser.add_argument("--product-id", action="append", dest="product_ids")
    parser.add_argument("--dry-run", action="store_true", help="DB 연결 없이 파일 검증만 수행")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        pairs = discover_pairs(args.outputs_dir, args.product_ids)
        product_count, review_count = upload_pairs(pairs, dry_run=args.dry_run)
    except (DataValidationError, RuntimeError) as exc:
        print(f"[실패] {exc}")
        return 1

    action = "검증" if args.dry_run else "Supabase 적재"
    ids = ", ".join(pair.product_id for pair in pairs)
    print(f"[완료] {action}: 상품 {product_count}개, 리뷰 {review_count}개 (상품 ID: {ids})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
