"""Run both existing crawlers for exactly three products, then upload their JSON files."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from upload_to_supabase import discover_pairs, upload_pairs


PRODUCT_ID_RE = re.compile(r"/(?:goods|products)/(\d+)")
CRAWLER_DIR = Path(__file__).resolve().parent


def product_id_from_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not (
        hostname == "musinsa.com" or hostname.endswith(".musinsa.com")
    ):
        raise ValueError(f"무신사 URL만 사용할 수 있습니다: {url}")
    match = PRODUCT_ID_RE.search(parsed.path)
    if not match:
        raise ValueError(f"상품 ID를 URL에서 찾을 수 없습니다: {url}")
    return match.group(1)


def load_targets(path: Path) -> list[dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    targets = document.get("products") if isinstance(document, dict) else None
    if not isinstance(targets, list) or len(targets) != 3:
        raise ValueError("설정 파일의 products 배열에는 정확히 상품 3개가 있어야 합니다.")

    seen: set[str] = set()
    for index, target in enumerate(targets):
        if not isinstance(target, dict):
            raise ValueError(f"products[{index}]는 객체여야 합니다.")
        product_url = str(target.get("product_url") or "")
        review_url = str(target.get("review_url") or "")
        product_id = product_id_from_url(product_url)
        review_product_id = product_id_from_url(review_url)
        if product_id != review_product_id:
            raise ValueError(
                f"products[{index}]의 상품/리뷰 URL ID가 다릅니다: {product_id} != {review_product_id}"
            )
        if product_id in seen:
            raise ValueError(f"중복 상품 ID입니다: {product_id}")
        seen.add(product_id)
        target["product_id"] = product_id
    return targets


def run_crawler(script_name: str, url: str, headed: bool) -> None:
    env = os.environ.copy()
    env["CRAWLER_HEADLESS"] = "0" if headed else "1"
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    process = subprocess.run(
        [sys.executable, str(CRAWLER_DIR / script_name)],
        input=url + "\n",
        text=True,
        cwd=CRAWLER_DIR.parent,
        env=env,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(f"{script_name} 실행 실패 (exit={process.returncode})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=CRAWLER_DIR / "targets.json",
    )
    parser.add_argument("--headed", action="store_true", help="브라우저 창을 표시")
    parser.add_argument("--reviews-only", action="store_true", help="상품 JSON은 유지하고 리뷰만 다시 수집")
    parser.add_argument("--skip-upload", action="store_true", help="JSON 생성과 검증까지만 수행")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        targets = load_targets(args.config)
        for position, target in enumerate(targets, start=1):
            print(f"\n[{position}/3] 상품 {target['product_id']} 수집")
            if not args.reviews_only:
                run_crawler("Crawler_product_updated.py", target["product_url"], args.headed)
            run_crawler("Crawler_review_updated.py", target["review_url"], args.headed)

        product_ids = [target["product_id"] for target in targets]
        pairs = discover_pairs(CRAWLER_DIR / "outputs", product_ids)
        product_count, review_count = upload_pairs(pairs, dry_run=args.skip_upload)
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        print(f"[실패] {exc}")
        return 1

    action = "검증" if args.skip_upload else "Supabase 적재"
    print(f"[완료] {action}: 상품 {product_count}개, 리뷰 {review_count}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
