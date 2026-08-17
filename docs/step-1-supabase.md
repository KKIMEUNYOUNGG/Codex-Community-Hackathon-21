# 1단계: 상품·리뷰를 Supabase에 적재하기

## 이번 단계의 범위

두 Playwright 크롤러는 로컬 PC나 향후 별도 크롤러 컨테이너에서 실행한다. Supabase에는 크롤러 코드가 아니라 수집 결과를 저장한다.

- `products`: 상품당 1행
- `raw_reviews`: 리뷰당 1행
- 같은 상품을 다시 수집하면 `upsert`하여 갱신
- `review_analyses`, `product_analyses`, `chat_history`는 2단계 이후에 추가

Supabase Hosted Edge Functions는 Chromium 전체를 실행하는 장시간 크롤러용 런타임이 아니다. 현재 공식 제한은 메모리 256MB, 요청당 CPU 2초이므로 Playwright 실행 위치를 분리한다.

## 1. 새 Supabase 프로젝트 생성

1. Supabase Dashboard에서 새 프로젝트를 만든다.
2. `Project Settings > API Keys`에서 다음 값을 확인한다.
   - Project URL
   - Secret key (`sb_secret_...`)
3. Secret key는 백엔드 전용이며 Git, 프론트엔드, 채팅에 올리지 않는다.

프로젝트 루트에서 `.env.example`을 `.env`로 복사하고 실제 값을 넣는다.

```dotenv
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_SECRET_KEY=sb_secret_REPLACE_ME
```

## 2. DB 스키마 적용

권장 방식은 Supabase CLI로 마이그레이션 이력을 남기는 것이다.

```powershell
npx supabase login
npx supabase link --project-ref YOUR_PROJECT_REF
npx supabase db push
```

CLI를 아직 쓰지 않는 초기 실습에서는 Dashboard의 SQL Editor에서 `supabase/migrations/202608160001_create_crawler_tables.sql` 내용을 한 번 실행해도 된다.

두 테이블 모두 RLS가 활성화되며 `anon`, `authenticated` 접근은 차단된다. 적재기는 Secret key로만 접근한다.

## 3. Python 환경 준비

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

## 4. 상품 3개 설정

`Crawler/targets.example.json`을 `Crawler/targets.json`으로 복사하고 각 상품의 실제 URL 두 개를 입력한다.

- `product_url`: `https://www.musinsa.com/products/{상품ID}`
- `review_url`: 무신사에서 상품의 후기 전체보기로 이동한 뒤 나온 `https://www.musinsa.com/review/goods/{같은 상품ID}...` URL

한 항목의 두 URL에 들어 있는 상품 ID는 반드시 같아야 한다.

## 5. 수집 및 적재

처음에는 브라우저를 보면서 JSON 생성까지만 검증한다.

```powershell
python Crawler/run_three_products.py --headed --skip-upload
```

성공하면 Supabase 적재까지 실행한다.

```powershell
python Crawler/run_three_products.py --headed
```

브라우저 창이 없는 서버나 컨테이너에서는 `--headed`를 제외한다.

이미 JSON을 만들어 둔 경우 크롤링 없이 적재하거나 검증할 수 있다.

```powershell
python Crawler/upload_to_supabase.py --dry-run --product-id 123 --product-id 456 --product-id 789
python Crawler/upload_to_supabase.py --product-id 123 --product-id 456 --product-id 789
```

## 6. 적재 확인

Dashboard의 SQL Editor에서 다음 쿼리를 실행한다.

```sql
select product_id, product_name, review_count, updated_at
from public.products
order by updated_at desc;

select product_id, count(*) as stored_review_count
from public.raw_reviews
group by product_id
order by product_id;
```

상품 3행과 각 상품별 리뷰 수가 보이면 1단계가 끝난다.

## 현재 샘플 파일 상태

현재 저장된 샘플은 상품정보가 `6202285`, 리뷰가 `6618666`으로 서로 다른 상품이다. 적재기는 이 상태를 오류로 처리한다. 실제 상품마다 동일한 ID의 `*_product_details.json`, `*_reviews.json` 한 쌍을 만들어야 한다.
