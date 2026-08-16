# 코덱스 사용 기록

## 1. 작업 개요

해커톤 프로젝트에서 **패션 판매자 의사결정 AI Agent**의 기능 정의와 분석 구조를 구체화하기 위해 AI 도구를 활용했다.

서비스의 핵심 목표는 무신사 상품 및 리뷰 데이터를 분석하여 단순 리뷰 요약을 넘어서,

- 어떤 고객군에서
- 어떤 상품 문제가 발생하고 있는지
- 어떤 문제가 가장 우선적으로 개선되어야 하는지
- 판매자가 현재 무엇을 개선할 수 있는지
- 다음 상품 소싱 시 어떤 조건을 확인해야 하는지

를 실제 리뷰 근거와 함께 제안하는 **AI Seller Copilot** 구조를 설계하는 것이었다.

개인 식별 정보, 계정 정보, API Key, 이메일, 연락처 등 개인정보·민감정보는 본 기록에서 제외했다.

## 2. 주요 사용 프롬프트 및 요청

### 2.1 서비스 방향 설정

**프롬프트 요약**

> 무신사 상품 데이터와 리뷰 데이터를 크롤링하고, 리뷰를 분석해 판매자에게 도움을 주는 AI Agent를 만들고 싶다.

**수행 작업**

- 단순 리뷰 요약 서비스와 판매자 의사결정 Agent의 차이 정의
- 리뷰 분석 결과를 실제 Seller Action으로 연결하는 방향 제안
- 판매자 관점에서 활용 가능한 기능 범위 정리

**결과**

서비스 방향을 다음과 같이 정리했다.

`리뷰 분석 → 문제 발견 → 영향 고객군 탐색 → 우선순위 판단 → 개선 Action → 다음 소싱 조건 → 근거 확인 → 추가 질의`

### 2.2 판매·소싱 의사결정 Agent로 방향 수정

**프롬프트 요약**

> 의류 판매자는 자체 제작보다 도매·업체 선정 방식도 많으므로, 실제 판매자가 통제 가능한 의사결정을 중심으로 설계하고 싶다.

**수행 작업**

- 제품 자체 변경만 권장하는 기존 방향 수정
- 판매자 통제 범위를 고려한 Action 재정의
- 판매 개선과 다음 상품 소싱을 구분

**결과**

Action을 다음 두 축으로 분리했다.

- **Now Action**: 현재 판매 중인 상품에서 바로 할 수 있는 개선
- **Next Sourcing**: 다음 상품 선정 시 확인해야 할 조건

예시:

- 사이즈 실측 정보 보강
- 체형별 착용 정보 안내
- 특정 옵션의 문제 안내
- 다음 소싱 시 더 적합한 사이즈 스펙 확인

## 3. 기능 정의 정리

### 3.1 전체 사용자 흐름

최종적으로 다음 흐름으로 정리했다.

`상품 URL 입력`

→ `상품·리뷰 수집`

→ `데이터 품질 검사`

→ `리뷰 Aspect/VOC 구조화`

→ `Customer Segment × Aspect 분석`

→ `Issue & Strength 탐지`

→ `개선 우선순위 계산`

→ `Now Action 생성`

→ `Next Sourcing Criteria 생성`

→ `Evidence 연결`

→ `AI 분석 보고서`

→ `Seller AI Chatbot`

### 3.2 핵심 기능

| ID | 기능 | 설명 |
|---|---|---|
| F01 | 상품·리뷰 데이터 수집 | 상품 URL에서 상품 기본정보와 리뷰 데이터 수집 |
| F02 | Data Quality Guard | 중복·결측·표본 수를 검사하고 분석 가능한 범위 판단 |
| F03 | Aspect/VOC 분석 | 한 리뷰에서 여러 상품 요소의 긍·부정 반응과 근거 문장 추출 |
| F04 | Customer Segment 분석 | 키·몸무게·성별·옵션 기준으로 문제가 집중되는 고객군 탐색 |
| F05 | Issue 탐지 | 반복되는 부정 이슈 도출 |
| F06 | Strength 탐지 | 반복적으로 긍정 평가되는 상품 강점 도출 |
| F07 | Trend 분석 | 최근 리뷰와 과거 리뷰의 문제 비율 변화 확인 |
| F08 | Priority 분석 | 빈도·평점 영향·고객군 집중도·최근 추세를 기반으로 개선 우선순위 계산 |
| F09 | Now Action 생성 | 현재 상품에서 바로 실행 가능한 개선안 제시 |
| F10 | Next Sourcing Criteria 생성 | 다음 상품 선정 시 유지·개선해야 할 조건 제안 |
| F11 | Evidence Viewer | AI 판단에 사용된 실제 리뷰 원문 연결 |
| F12 | AI 분석 보고서 | 요약 보고서와 상세 보고서 제공 |
| F13 | Seller AI Chatbot | 현재 상품 데이터와 리뷰 분석 결과 기반 추가 질의 |

## 4. 리뷰 분석 구조 설계

### 4.1 Aspect 구조

리뷰를 단순 긍정/부정으로만 분류하지 않고 하나의 리뷰에서 여러 Aspect를 추출하도록 설계했다.

최종 대분류 예시:

- `SIZE_FIT`
- `MATERIAL`
- `COLOR`
- `DESIGN`
- `COMFORT_FUNCTION`
- `QUALITY_DURABILITY`
- `PRICE_VALUE`
- `DELIVERY_PACKAGING`
- `ETC`

각 Aspect에는 다음 정보를 저장하도록 했다.

- `detail`
- `sentiment`
- `evidence`

예시:

```json
{
  "aspect": "SIZE_FIT",
  "detail": "어깨",
  "sentiment": "negative",
  "evidence": "어깨가 생각보다 좁아요"
}
```

한 리뷰에는 여러 Aspect를 동시에 허용한다.

### 4.2 Customer Segment 구조

가상의 Persona를 생성하지 않고 실제 리뷰 데이터에서 확인 가능한 정보만 사용하도록 기준을 정했다.

사용 정보 예시:

- 성별
- 키 구간
- 몸무게 구간
- 구매 사이즈
- 구매 색상

예시:

`160~164cm × M 사이즈 구매자`

이 그룹에서 특정 Aspect의 부정률, 평균 평점, 관련 리뷰 수를 계산해 문제 집중 고객군을 찾는다.

## 5. 데이터 구조화

각 단계의 결과를 긴 자연어가 아니라 JSON/테이블 형태로 저장하도록 설계했다.

### 5.1 product

상품 기본 정보

```text
product_id / brand / product_name / category / price / rating / review_count / image_url
```

### 5.2 raw_review / clean_review

리뷰 원본 및 정제 데이터

```text
review_id / product_id / rating / review_date / review_text / gender / height / weight / size / color / like_count
```

### 5.3 review_analysis

리뷰별 Aspect 분석 결과

```text
review_id / aspect / detail / sentiment / evidence
```

### 5.4 segment_analysis

고객군별 분석 결과

```text
segment_id / criteria / review_count / avg_rating / negative_aspect / negative_review_count / negative_ratio
```

### 5.5 issue

상품 주요 문제

```text
issue_id / category / detail / review_count / ratio / avg_rating / main_segment / evidence_review_ids
```

### 5.6 strength

상품 주요 강점

```text
strength_id / category / positive_review_count / positive_ratio / evidence_review_ids
```

### 5.7 priority

개선 우선순위

```text
issue_id / frequency_score / rating_impact_score / segment_score / trend_score / priority_score / status
```

### 5.8 action

판매자 Action

```text
issue_id / now_action / next_sourcing / rationale / evidence_review_ids
```

## 6. 개선 우선순위 설계

LLM이 임의로 긴급도를 판단하지 않고, 구조화된 데이터로 Priority Score를 계산하고 LLM은 결과를 설명하도록 역할을 분리했다.

MVP 기준 예시:

- 문제 발생 빈도: 40%
- 평점 영향: 25%
- 고객군·옵션 집중도: 20%
- 최근 증가세: 15%

예시 결과:

| Issue | Priority Score | 상태 |
|---|---:|---|
| 사이즈·핏 | 82 | 우선 개선 |
| 소재·촉감 | 61 | 개선 검토 |
| 배송 | 24 | 관찰 |

## 7. AI 분석 보고서 구조

보고서는 **요약 + 상세 보고서**의 2단 구조로 설계했다.

### 7.1 요약 보고서

판매자가 빠르게 의사결정할 수 있도록 다음을 한 화면에서 제공한다.

- 가장 시급한 문제
- 관련 리뷰 수 및 비율
- 다른 이슈 대비 비교
- 문제 집중 고객군
- 평균 평점
- 부정률
- AI Diagnosis
- 유지할 Strength
- Now Action
- Next Sourcing
- 근거 리뷰 보기

예시:

> 가장 시급한 문제 — 사이즈·핏  
> 부정 리뷰 84건 중 32건(38%)이 사이즈·핏 관련 문제이며,  
> 특히 M 옵션 · 160~165cm 고객군에서 문제가 집중됨.

### 7.2 상세 보고서

다음 순서로 근거를 확인할 수 있도록 설계했다.

`전체 리뷰 현황`

→ `긍정 Strength TOP`

→ `부정 Issue TOP`

→ `문제 세부 원인`

→ `문제 집중 고객군`

→ `최근 변화`

→ `Priority`

→ `Now Action`

→ `Next Sourcing`

→ `실제 근거 리뷰`

## 8. Evidence 설계

모든 AI 판단에서 실제 리뷰까지 추적할 수 있도록 `review_id`를 연결하도록 했다.

AI가 근거 리뷰 문장을 새로 생성하지 않고, 실제 수집 리뷰를 Evidence로 제공하는 방식을 채택했다.

예시:

```text
Issue: SIZE_FIT
Evidence Review IDs:
- 86868095
- 86868122
- 86868314
```

이를 통해

`AI 판단 → 계산된 지표 → 실제 리뷰`

순서로 검증 가능하도록 했다.

## 9. Seller AI Chatbot 설계

Seller AI Chatbot은 일반적인 자유 대화 챗봇이 아니라 현재 분석한 상품 데이터와 실제 리뷰만을 근거로 답변하도록 설계했다.

질문 예시:

- 왜 사이즈·핏이 가장 시급한 문제야?
- M 옵션 불만 리뷰만 보여줘.
- 160cm 전후 고객의 반응은 어때?
- 이 상품에서 지금 가장 먼저 무엇을 개선해야 해?
- 다음에는 어떤 상품을 가져오는 게 좋아?
- 특정 사이즈의 발주량을 얼마나 줄여야 해?

마지막 질문처럼 판매량·재고·반품률 등 현재 데이터에 없는 정보가 필요한 경우에는 임의 추정하지 않고 다음과 같이 제한하도록 했다.

> 현재 데이터에는 판매량·재고·반품률 정보가 없어 정확한 발주 수량을 판단할 수 없습니다.

## 10. 팀 기능 정의 통합

팀원들이 각각 정리한 기능 정의를 비교해 공통 구조와 차별화 요소를 통합했다.

통합한 주요 내용:

- 상품·리뷰 수집
- 리뷰 정제 및 데이터 검증
- Aspect/VOC 분석
- Customer Segment 분석
- Issue / Strength 탐지
- 개선 우선순위
- 실제 리뷰 Evidence
- Seller Action
- AI Report
- Seller AI Chatbot

추가 아이디어 중 상세페이지 설명과 실제 고객 경험을 비교하는 `Product-Customer Gap` 기능은 상세페이지 데이터를 안정적으로 수집할 수 있어야 하므로 핵심 MVP가 아닌 확장 기능으로 분류했다.

## 11. MVP 범위 정리

짧은 해커톤 구현 시간을 고려해 다음 기능을 우선 구현 대상으로 정리했다.

### P0

- 상품·리뷰 데이터 로드
- Data Quality Guard
- Aspect + Sentiment + Evidence 추출
- Issue / Strength 탐지
- Customer Segment 분석
- Priority Score 계산
- Now Action
- Next Sourcing Criteria
- Evidence Viewer
- 요약/상세 보고서
- Seller AI Chatbot

### P1

- 최근 리뷰 Trend 분석
- Product-Customer Gap
- FAQ 자동 생성
- 마케팅 문구 생성
- 상세 Evidence 필터

### P2

- 경쟁상품 비교
- 소싱 후보 상품 자동 추천
- 리뷰 이미지 멀티모달 분석
- 판매량·재고·반품률 연동
- 실제 발주 수량 추천
- 장기 리뷰 모니터링

## 12. 수정한 파일

이번 채팅에서는 기능 설계와 데이터 구조 정의를 중심으로 진행했으며, 실제 서비스 코드 파일은 직접 수정하지 않았다.

### 생성 파일

- `코덱스 사용기록/README.md`
  - 해커톤 제출용 AI 도구 사용 기록 정리

### 실제 코드 수정

- 없음

향후 구현 단계에서는 본 문서에서 정의한 구조를 기준으로 크롤러, 리뷰 분석 로직, Priority 계산, 보고서 UI, Seller AI Chatbot 등을 연결할 수 있다.

## 13. 최종 결과

최종적으로 서비스의 핵심 흐름을 다음과 같이 정리했다.

```text
Review
→ Aspect
→ Customer Segment
→ Issue & Strength
→ Priority
→ Evidence
→ Now Action
→ Next Sourcing
→ AI Report
→ Seller Chat
```

최종 서비스 정의:

> **고객 리뷰를 단순 요약하는 것이 아니라, 실제 리뷰 데이터를 근거로 어떤 고객군에서 어떤 문제가 발생하는지 찾아내고, 무엇을 먼저 개선해야 하는지와 다음 상품을 어떤 조건으로 소싱할지 제안하는 AI Seller Copilot**

