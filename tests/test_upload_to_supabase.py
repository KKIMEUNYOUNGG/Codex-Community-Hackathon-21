from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Crawler"))

from upload_to_supabase import (  # noqa: E402
    DataValidationError,
    discover_pairs,
    normalize_product,
    normalize_reviews,
    normalize_supabase_url,
    upload_pairs,
)


class UploadToSupabaseTests(unittest.TestCase):
    def test_normalizes_copied_rest_endpoint(self) -> None:
        self.assertEqual(
            normalize_supabase_url("https://sample.supabase.co/rest/v1/"),
            "https://sample.supabase.co",
        )

    def write_pair(self, root: Path, product_id: str = "123") -> None:
        product = {
            "product_detail": {
                "product_id": product_id,
                "url": f"https://www.musinsa.com/products/{product_id}",
                "product_name": "테스트 상품",
                "brand_name": "테스트 브랜드",
                "price": 10000,
                "rating": 4.5,
                "review_count": 1,
                "Description": "요약",
                "description_raw": "원문",
                "main_image_url": "https://example.com/product.jpg",
            }
        }
        reviews = {
            "reviews": [
                {
                    "product_id": product_id,
                    "review_id": "review-1",
                    "date": "2026-08-16",
                    "rating": 5.0,
                    "option": "BLACK/M",
                    "review_text": "좋아요",
                    "photo_urls": ["https://example.com/review.jpg"],
                    "like_count": 2,
                }
            ]
        }
        (root / f"{product_id}_product_details.json").write_text(
            json.dumps(product, ensure_ascii=False), encoding="utf-8"
        )
        (root / f"{product_id}_reviews.json").write_text(
            json.dumps(reviews, ensure_ascii=False), encoding="utf-8"
        )

    def test_discovers_and_maps_matching_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_pair(root)

            pairs = discover_pairs(root)
            product = normalize_product(pairs[0])
            reviews = normalize_reviews(pairs[0])

            self.assertEqual([pair.product_id for pair in pairs], ["123"])
            self.assertEqual(product["description_summary"], "요약")
            self.assertEqual(reviews[0]["source_review_id"], "review-1")
            self.assertEqual(reviews[0]["purchased_option"], "BLACK/M")

    def test_dry_run_does_not_require_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_pair(root)
            counts = upload_pairs(discover_pairs(root), dry_run=True)
            self.assertEqual(counts, (1, 1))

    def test_rejects_orphan_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "123_reviews.json").write_text('{"reviews": []}', encoding="utf-8")
            with self.assertRaises(DataValidationError):
                discover_pairs(root)

    def test_rejects_review_with_different_product_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_pair(root)
            path = root / "123_reviews.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            document["reviews"][0]["product_id"] = "999"
            path.write_text(json.dumps(document), encoding="utf-8")

            with self.assertRaises(DataValidationError):
                normalize_reviews(discover_pairs(root)[0])


if __name__ == "__main__":
    unittest.main()
