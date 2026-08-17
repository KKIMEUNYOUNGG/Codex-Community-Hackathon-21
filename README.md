# Codex Community Hackathon 21

무신사 상품과 리뷰를 수집하고, 고객 Persona × 의류 Aspect를 분석해 Issue, Strength,
상품 개선 우선순위를 만드는 서비스입니다.

## 현재 구현

- Playwright 상품·리뷰 크롤러와 3상품 실행기
- Supabase PostgreSQL 원본/분석 테이블 migration
- OpenAI Responses API 기반 F03 Aspect 분석
- F04 Persona × Aspect, F05 Issue, F06 Strength, F07 개선 우선순위
- 원문 Evidence 및 offset, source hash, 표본/분석 설정 provenance 검증

## 빠른 시작

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m unittest discover -s tests -v
```

환경변수 예시는 `.env.example`, 전체 실행 방법은
[`docs/features-f01-f07.md`](docs/features-f01-f07.md)를 참고하세요.

실제 `.env`, crawler 원본 출력, 분석 artifact는 저장소에 포함하지 않습니다.
