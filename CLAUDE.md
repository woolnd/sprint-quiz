# CLAUDE.md

Sprint Quiz — 정리한 학습 노트를 기반으로 AI가 매일 오전 8시에 복습 질문을 생성해 이메일/디스코드로 발송하는 서비스.

## 프로젝트 성격

- 개인 포트폴리오 프로젝트. **측정 기반 의사결정**이 핵심 가치다.
- "품질이 좋아졌다" 같은 주관적 서술을 쓰지 않는다. 토큰 수, 지연시간, 비용, 통과율 등 로그로 확인 가능한 숫자로 말한다.
- 무언가를 **넣지 않기로 한 결정**도 결과물이다 (예: RAG 유보). 근거 숫자와 함께 기록한다.

## 기술 스택

| 영역 | 사용 |
|---|---|
| 언어/패키지 | Python, uv (`uv run`, `uv add`) |
| LLM | Anthropic Claude API (Haiku), AsyncAnthropic |
| DB | SQLite |
| 웹 | FastAPI + Jinja2 + Tailwind CDN |
| 스케줄러 | APScheduler (Phase 4) |
| 발송 | Resend (이메일), discord.py (디스코드) |
| 배포 | Docker + Docker Compose → GCP Compute Engine (e2-micro, Always Free) |

프론트엔드 프레임워크(React 등)는 도입하지 않는다. 페이지가 소수이고 서버가 완성된 HTML을 반환하는 구조다.

## 디렉토리 구조

```
src/sprint_quiz/
  parser/       # base.py(확장자 분기), markdown.py(로딩 + content_hash)
  generator/    # keyword.py, quiz.py, validator.py
  notify/       # email.py
  db/           # schema.py, repository.py
  web/          # app.py, templates/, static/
  logger.py     # LLM 호출 CSV 로깅 + Timer
scripts/
  index.py      # 자료 인덱싱 → 키워드 추출 → 질문 생성 → 검증 end-to-end
data/           # Notion에서 내보낸 마크다운 자료
```

## 자주 쓰는 명령

```bash
uv run python scripts/index.py            # 자료 인덱싱 + 질문 생성
uv run python scripts/index.py --quiz 5   # 생성 개수 지정
uv run uvicorn sprint_quiz.web.app:app --reload
```

## 아키텍처 핵심 규칙

### 파이프라인
```
마크다운 자료 → 키워드 추출 → 배치 질문 생성 → Validator 검증
→ (사람) 승인 큐 → 08:00 발송
```

- **생성과 발송은 분리한다.** 발송 경로에 LLM 호출을 넣지 않는다. 08:00에 하는 일은 승인 큐에서 1건 꺼내 보내는 것뿐이다.
- **질문 형식은 고정이다.** `{키워드}에 대해서 설명해주세요.` 한 문장. 비교/응용/복합 질문은 이탈로 간주한다. 목적이 변별이 아니라 리마인드이기 때문이다.
- **답변은 3문장 이내.** 질문은 자료 범위로 제한하되, 답변은 배경 설명 추가를 허용한다.
- **배치 크기는 5로 고정.** 8로 늘리면 답변이 짧아지는 경향이 확인됐다. 바꾸려면 재측정 후 근거를 남긴다.
- **quizzes.status 흐름**: `pending → validated → approved → sent` (+ `rejected`). 미승인분 자동 발송 폴백은 두지 않는다.
- **재생성 루프는 순차**로 유지한다 (이전 판정에 의존). 독립적인 검증 호출만 `asyncio.gather` + `Semaphore(3)`로 병렬화한다.
- **캐시 워밍**: 배치 처리 시 첫 건만 순차 실행 후 나머지를 병렬로 돌린다. Prompt Caching은 첫 응답 시작 이후에야 적중한다.

### Validator
- 4개 기준(Groundedness / Correctness / Simplicity / Duplicate)은 **서로 독립적으로** 판정하도록 프롬프트에 명시돼 있다. 이 블록을 제거하지 않는다.
- 1차 필터(Phase 3-B)는 **Precision 우선**이다. 확신 높은 불합격만 Reject하고 애매한 것은 전부 2차로 넘긴다.
- 불합격분도 `quiz_id=None`으로 validations에 기록한다. Phase 3-B 학습 데이터다.

## 코드 작성 규칙 (Ponytail 활성화)

**Ponytail** 스킬이 활성화되어 있습니다. 코드를 짜기 전에 다음을 확인합니다:

1. 이미 코드베이스에 있는가?
2. 표준 라이브러리/내장 기능으로 충분한가?
3. 설치된 의존성으로 가능한가?
4. 한 줄짜리로 해결되는가?
5. 정말 필요한가?

**절대 타협 없는 것:**
- 입력 검증, 에러 처리
- 보안 (API 키 안전, SQL injection 방지)
- 접근성, 데이터 무결성

**강도 조정:**
```bash
/ponytail lite    # 최소 (필수만)
/ponytail full    # 기본값
/ponytail ultra   # 최대 (더 공격적)
```

목표는 "게으른" 게 아니라 "효율적인" 코드입니다. 불필요한 라인은 줄이되, 필요한 것은 한 줄도 빠뜨리지 않습니다.

## 절대 규칙

- **구독자 이메일이 든 DB 파일은 커밋하지 않는다.** `.gitignore` 유지 필수.
- **API 키는 `.env` / 배포 환경변수로만 관리한다.** 코드·문서·커밋 어디에도 넣지 않는다.
- **`llm_calls.csv`는 커밋하지 않는다.**
- **자료 원문(`materials.content`)을 비우는 처리는 되돌릴 수 없다.** 프롬프트가 안정된 뒤에만 적용한다.
- LLM 호출을 추가하면 **반드시 `logger.py`로 로깅**한다. 지금 안 남기면 지표를 소급할 수 없다.
- 성능 개선 작업은 **적용 전후 수치를 함께 남긴다.** 비교값 없는 최적화는 하지 않는다.
- 관리자 페이지(`/admin/review`)는 인증 없이 노출하지 않는다.

## 현재 위치

Phase 4 완료 (MVP 완료 지점).

- ✅ Phase 1 Baseline, Phase 2-A 배치 생성, Phase 3-A Validator + Prompt Caching + 비동기 병렬 처리
- ✅ Phase 4: 이메일 발송(Resend), FastAPI 앱 + 서비스 소개 페이지, 관리자 승인 페이지, 답변 확인 페이지, APScheduler(매일 08:00), Docker + GCP 배포
- 보류(최후순위): 디스코드 봇
- 진행 중: Phase 5 GitHub Actions CI/CD (GCP VM 자동 배포)
- 이후: Phase 3-B 자체 분류기 (MVP 이후), Phase 5 구독 등록/해지 페이지·자료 업로드, Phase 6 SM-2

## 컨벤션

### Branch
```
feat/#11-calendar-view
fix/#11-calendar-bug
```

### Commit
```
feat: 캘린더 뷰 구현
fix: 캘린더 날짜 오류 수정
chore: 개발 환경 세팅
design: 캘린더 UI 수정
docs: README 업데이트
refactor: 캘린더 뷰 리팩토링
```

### Issue / PR 제목
```
[Feat] 캘린더 뷰 구현
[Fix] 캘린더 날짜 오류 수정
[Chore] 개발 환경 세팅
[Design] 캘린더 UI 수정
[Docs] README 업데이트
[Refactor] 캘린더 뷰 리팩토링
```

### 작업 흐름
1. 이슈를 먼저 생성한다 (`.github/ISSUE_TEMPLATE/` 양식 사용)
2. 이슈 번호로 브랜치를 판다
3. 커밋은 작업 단위로 쪼갠다
4. PR은 `.github/pull_request_template.md` 양식을 채운다 — 특히 "테스트 및 검증 내역"과 "스크린샷 / 출력 결과"는 비워두지 않는다

## 응답 방식

- 코드를 줄 때는 코드 설명을 함께 붙이고, 코드 안에 주석도 단다.
- ML/DL 학습 과정을 설명할 때는 코드 없이 절차 위주로 설명한다.
