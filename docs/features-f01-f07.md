# F01~F07 구현 및 실행 가이드

현재 구현은 크롤러/DB/분석 코드를 독립적으로 실행한다. FastAPI와 Supabase write path를
연결하는 작업은 다음 통합 단계에서 진행할 수 있도록 JSON artifact 계약을 고정했다.

## 구현 위치

| 기능 | 코드 | 출력 |
| --- | --- | --- |
| F01 상품 등록·크롤링 | `Crawler/run_three_products.py`, 기존 crawler 2개 | 상품/리뷰 JSON |
| F02 데이터 저장 | `Crawler/upload_to_supabase.py`, `supabase/migrations/*.sql` | Supabase tables |
| F03 Aspect 분석 | `analysis_engine/f03_aspect_analysis.py` | `*_review_analyses.json` |
| F04 Persona × Aspect | `analysis_engine/f04_persona_aspect.py` | product insight artifact 내부 |
| F05 Issue 탐지 | `analysis_engine/f05_issues.py` | product insight artifact 내부 |
| F06 Strength 탐지 | `analysis_engine/f06_strengths.py` | product insight artifact 내부 |
| F07 개선 우선순위 | `analysis_engine/f07_priorities.py` | `*_product_insights.json` |

## 준비

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

`.env`에는 다음 값이 필요하다.

```dotenv
SUPABASE_URL=https://PROJECT_REF.supabase.co
SUPABASE_SECRET_KEY=...
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.6-luna
```

기존 `OPENAI_API` 이름도 코드에서 호환하지만, 공식 SDK 기본 변수명인
`OPENAI_API_KEY` 사용을 권장한다. OpenAI API 사용 가능 billing/usage tier도 필요하다.

Supabase SQL Editor에서 migration을 번호 순서대로 실행한다.

1. `202608160001_create_crawler_tables.sql`
2. `202608160002_create_analysis_tables.sql`

두 번째 migration은 향후 연결할 `analysis_runs`, `review_analyses`,
`product_analyses`, `chat_history`의 저장 계약까지 만든다. 현재 분석 실행기는 의도적으로
DB에 쓰지 않고 JSON만 생성한다.

## 실행

### F01~F02

`Crawler/targets.example.json`을 `Crawler/targets.json`으로 복사하고 세 상품 URL을 넣은 뒤:

```powershell
python Crawler/run_three_products.py --config Crawler/targets.json
```

이미 생성된 JSON만 검증하려면:

```powershell
python Crawler/upload_to_supabase.py --dry-run `
  --product-id 4314937 --product-id 1014752 --product-id 5068730
```

### F03

```powershell
python -m analysis_engine.run_f03 `
  --input Crawler/outputs/1014752_reviews.json
```

기본 출력은 `analysis_outputs/1014752_review_analyses.json`이다. 배치마다 원자적으로
checkpoint를 쓰므로 같은 명령을 다시 실행하면 완료된 리뷰 다음부터 재개한다. 원문이나
Persona 메타데이터, 날짜, 좋아요, 회원 ID, 모델 또는 분석 버전이 바뀌면
`--overwrite`를 명시해야 한다.

개발용 소량 확인:

```powershell
python -m analysis_engine.run_f03 `
  --input Crawler/outputs/1014752_reviews.json `
  --limit 3 --batch-size 3 --overwrite
```

`--limit` 결과에는 전체 원본 리뷰 수와 `is_sample=true`가 함께 기록된다.

### F04~F07

```powershell
python -m analysis_engine.run_f04_f07 `
  --reviews Crawler/outputs/1014752_reviews.json `
  --aspects analysis_outputs/1014752_review_analyses.json `
  --as-of 2026-08-16
```

기본 출력은 `analysis_outputs/1014752_product_insights.json`이다. 이 단계는 OpenAI를
호출하지 않는 결정론적 집계이므로 같은 입력과 같은 기준일에는 같은 분석값을 만든다.
`--as-of`를 생략하면 실행일을 사용하며, 기준일·최소 지지수·중복 제거 전후 리뷰 수와
F07 가중치는 `analysis_config`에 저장된다.

## 분석 계약

- Persona는 성별·키·몸무게·구매 옵션 원본에서만 만들며 LLM이 추론하지 않는다.
- 키/몸무게는 5단위 구간으로 만들고, 단일 차원과 `키×사이즈`, `색상×사이즈` 등을 집계한다.
- F03은 고정 taxonomy의 `category`, `aspect`, `sentiment`, `opinion_code`를 사용한다.
  따라서 `소매가 너무 김`과 `소매가 너무 짧음`을 서로 다른 이슈로 유지한다.
- 의미상 호환되지 않는 `aspect`와 `opinion_code` 조합은 schema 검증에서 거부한다.
- 모든 F03 Evidence는 원문에 존재해야 하며 exclusive `start/end` offset을 저장한다.
- F04는 Persona×Aspect 전체 긍·부정 표와 세부 의견 집중 인사이트를 함께 만든다.
- Issue/Strength의 최소 지지 리뷰 수는 `max(3, ceil(분석 리뷰 수 × 2%))`이다.
- 중복 리뷰는 동일 회원 ID와 정규화된 동일 본문을 기준으로 한 번만 센다.
- F07 점수(`priority-v1`)는 빈도 30%, 부정비율 30%, 관련 고객 규모 20%,
  최근성 15%, 좋아요 5%의 고정 가중합이다.
- 최근성은 기록된 절대 분석 기준일과 180일 half-life로 계산하며 날짜 누락은 가점이 없다.
- 판매량·반품률·매출 영향도처럼 입력에 없는 지표는 계산하거나 생성하지 않는다.

## 검증

```powershell
python -m unittest discover -s tests -v
```

테스트는 URL/product ID 무결성, Persona 옵션 파싱, taxonomy, exact Evidence,
일시적 API 오류 재시도, Persona 교차분석, Issue/Strength 방향 분리, F07 순위,
절대 최근성·source hash·표본 provenance와 실제 세 fixture의 606개 리뷰를 확인한다.
