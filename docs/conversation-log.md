# Seller Copilot 작업 대화 로그

- 작업일: 2026-08-16
- 프로젝트: Codex Community Hackathon 21
- 원격 저장소: `https://github.com/KKIMEUNYOUNGG/Codex-Community-Hackathon-21.git`
- 작업 브랜치: `feat/add-crawler`

> 보안상 `.env`의 실제 Supabase 키와 OpenAI 키 값은 기록하지 않습니다.

## 1. HTML 실행 방법 확인

처음에는 `review_ai_ai_chat_final/code.html`을 브라우저에서 실행하는 방법을 확인했습니다.

확인한 방법:

- HTML 파일을 직접 브라우저로 열기
- 해당 폴더에서 `python -m http.server 8000` 실행
- 브라우저에서 `http://localhost:8000/code.html` 접속

외부 CDN을 사용하는 HTML이므로 인터넷 연결이 필요할 수 있다는 점도 확인했습니다.

## 2. Git 원격 저장소 연결

### 문제

`git pull origin main` 실행 시 다음 오류가 발생했습니다.

```text
fatal: 'origin' does not appear to be a git repository
fatal: Could not read from remote repository.
```

### 원인

현재 폴더에 `origin` 원격 저장소가 등록되어 있지 않았습니다.

### 처리

다음 저장소를 원격으로 연결했습니다.

```powershell
git remote add origin https://github.com/KKIMEUNYOUNGG/Codex-Community-Hackathon-21.git
git fetch origin
```

사용자가 `main`이 아니라 `feat/add-crawler` 브랜치를 요청하여 해당 브랜치로 전환했습니다.

```powershell
git checkout -b feat/add-crawler --track origin/feat/add-crawler
git pull origin feat/add-crawler
```

결과:

- 로컬 브랜치: `feat/add-crawler`
- 원격 추적 브랜치: `origin/feat/add-crawler`
- 원격 코드 상태: 최신 상태

## 3. 현재 코드 GitHub 업로드

현재 파일을 팀원들이 사용할 수 있도록 커밋하고 원격 브랜치에 push했습니다.

```powershell
git add .
git commit -m "Initial project import"
git push origin feat/add-crawler
```

## 4. 로컬 웹서비스 구성

사용자가 다음 구조의 서비스를 요청했습니다.

- 백엔드: FastAPI
- 프론트엔드: React + Vite
- 데이터베이스: PostgreSQL 계열 저장소
- 대화 저장: Redis 또는 유사 저장소
- 크롤러, DB, API, F01~F07 분석 기능 연결
- 우선 배포보다 로컬 서비스 완성

구성한 주요 영역:

- `backend/app/main.py`: FastAPI 진입점
- `backend/app/routes/products.py`: 상품 API
- `backend/app/routes/dashboard.py`: 대시보드 API
- `backend/app/routes/conversations.py`: 대화 API
- `frontend/src/App.jsx`: React 화면
- `frontend/src/main.jsx`: React 진입점
- `frontend/vite.config.js`: Vite 설정
- `Crawler/upload_to_supabase.py`: 크롤러 결과 Supabase 적재
- `analysis_engine/`: F03~F07 분석 로직
- `supabase/migrations/`: 크롤러 및 분석 테이블 정의

## 5. 실행 환경 구성

React 실행을 위해 Node.js LTS를 설치했습니다.

프론트엔드 의존성 설치:

```powershell
$env:Path = "$env:ProgramFiles\nodejs;" + $env:Path
Set-Location "D:\stitch_stitch_ai_seller_copilot_(1)\frontend"
npm install
```

프론트엔드 빌드:

```powershell
npm run build
```

결과:

- React/Vite 빌드 성공
- `dist/` 생성 완료

## 6. 백엔드 실행 및 확인

백엔드 실행 명령:

```powershell
Set-Location "D:\stitch_stitch_ai_seller_copilot_(1)"
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

확인한 API:

- `GET http://127.0.0.1:8000/health` → HTTP 200
- `GET http://127.0.0.1:8000/api/v1/products` → HTTP 200
- `GET http://127.0.0.1:8000/api/v1/dashboard/1001` → HTTP 200
- `POST http://127.0.0.1:8000/api/v1/conversations/demo/messages` → HTTP 200

## 7. `.env` 연결 작업

초기에는 `.env` 파일이 비어 있어 애플리케이션이 Supabase와 OpenAI 설정을 읽을 수 없었습니다.

추가한 처리:

- 백엔드 시작 시 프로젝트 루트 `.env` 자동 로드
- `SUPABASE_URL`의 `/rest/v1` 경로 정규화
- `SUPABASE_SECRET_KEY`와 legacy service role key 호환
- `OPENAI_API`를 `OPENAI_API_KEY`로 호환
- Supabase 연결이 가능하면 상품과 리뷰를 실데이터 우선 조회
- OpenAI 설정이 있으면 채팅 응답을 실제 모델에 요청
- 연결 실패 시 서비스가 중단되지 않도록 fallback 응답 사용

관련 파일:

- `backend/app/config.py`
- `backend/app/routes/products.py`
- `backend/app/routes/dashboard.py`
- `backend/app/routes/conversations.py`

검증 결과:

- `.env` 필수 값 로딩 테스트 통과
- 백엔드 API smoke test 통과
- 전체 테스트 결과: 22개 성공, 1개 스킵

## 8. 버튼과 채팅 UI 문제 해결

### 발견한 문제

브라우저에서 전송 버튼이 눌리지 않는 것처럼 보였습니다.

확인 결과:

- 버튼 DOM은 존재함
- 버튼은 disabled 상태가 아님
- 다른 요소가 버튼을 덮고 있지 않음
- 작은 화면에서는 버튼이 화면 아래로 밀려 자동 클릭이 실패할 수 있음
- OpenAI 요청 중 화면 변화가 없어 사용자가 클릭 실패로 인식할 수 있음

### 수정 내용

`frontend/src/App.jsx`:

- 사이드 메뉴 항목을 `div`에서 실제 `button`으로 변경
- Enter 키로 채팅 전송 가능
- 전송 중 `전송 중...` 표시
- API 오류 시 안내 메시지 표시
- 빈 메시지 전송 방지

`frontend/src/styles.css`:

- 채팅 입력창을 화면 하단에 고정
- 전송 버튼을 항상 보이는 위치에 배치
- 본문이 입력창에 가리지 않도록 하단 여백 추가
- 버튼에 pointer cursor와 disabled 스타일 추가

브라우저에서 실제 입력과 전송 이벤트가 동작하는 것을 확인했습니다.

## 9. 현재 실행 방법

### 백엔드

```powershell
Set-Location "D:\stitch_stitch_ai_seller_copilot_(1)"
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### 프론트엔드

```powershell
$env:Path = "$env:ProgramFiles\nodejs;" + $env:Path
Set-Location "D:\stitch_stitch_ai_seller_copilot_(1)\frontend"
npm run dev -- --host 0.0.0.0 --port 3000
```

접속 주소:

- 웹 화면: `http://localhost:3000/`
- 백엔드 상태: `http://localhost:8000/health`

## 10. 현재 상태와 남은 작업

완료된 항목:

- GitHub 원격 저장소 연결
- `feat/add-crawler` 브랜치 연결
- 현재 코드 push
- FastAPI 로컬 실행
- React/Vite 로컬 실행
- `.env` 로딩
- Supabase 조회 경로 연결
- OpenAI 채팅 호출 경로 연결
- 채팅 입력 및 버튼 동작 개선
- 프론트엔드 빌드 및 백엔드 API 검증

추가로 발전시킬 항목:

- 실제 크롤러 실행부터 적재까지의 비동기 job 관리
- Redis 또는 Supabase 기반 대화 이력 저장
- F03~F07 분석 결과를 대시보드에 직접 매핑
- 상품 등록 후 크롤링 상태 표시
- 사이드 메뉴별 실제 화면 라우팅
- 운영 배포 및 비밀키 재발급/보안 설정

## 11. 보안 메모

`.env`에는 인증 정보가 들어가므로 Git에 commit하지 않아야 합니다.

실제 키가 채팅 로그나 외부에 노출된 경우에는 다음 조치가 필요합니다.

- OpenAI API 키 재발급
- Supabase service role key 재발급
- `.gitignore`에 `.env` 포함 여부 확인
- 팀원에게는 `.env.example`만 공유
