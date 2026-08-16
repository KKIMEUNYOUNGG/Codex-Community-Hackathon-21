from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Crawler"))

from run_three_products import load_targets, product_id_from_url  # noqa: E402


class CrawlerRunnerTests(unittest.TestCase):
    def test_accepts_only_musinsa_product_and_review_urls(self) -> None:
        self.assertEqual(
            product_id_from_url("https://www.musinsa.com/products/4314937"),
            "4314937",
        )
        self.assertEqual(
            product_id_from_url(
                "https://www.musinsa.com/review/goods/4314937?sort=up_cnt_desc"
            ),
            "4314937",
        )
        with self.assertRaises(ValueError):
            product_id_from_url("https://example.com/products/4314937")

    def test_requires_exactly_three_matching_unique_products(self) -> None:
        products = []
        for product_id in ("1", "2", "3"):
            products.append(
                {
                    "product_url": f"https://www.musinsa.com/products/{product_id}",
                    "review_url": f"https://www.musinsa.com/review/goods/{product_id}",
                }
            )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "targets.json"
            path.write_text(json.dumps({"products": products}), encoding="utf-8")
            self.assertEqual(
                [target["product_id"] for target in load_targets(path)],
                ["1", "2", "3"],
            )
            products[2]["review_url"] = "https://www.musinsa.com/review/goods/999"
            path.write_text(json.dumps({"products": products}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_targets(path)


if __name__ == "__main__":
    unittest.main()
