---
name: web-preview
description: Sprint Quiz의 FastAPI 로컬 웹 서버를 띄우거나 재시작할 때 사용한다. "서버 켜줘", "웹 띄워줘", "로컬에서 확인해줘", "포트 이미 쓰고 있대", "uvicorn 재시작", "소개 페이지 확인" 같은 요청에서 트리거된다. 기존에 떠 있던 프로세스를 정리하고 새로 띄운 뒤 정상 응답까지 확인한다.
---

# 웹 서버 실행 & 재시작

Sprint Quiz의 FastAPI 앱(`sprint_quiz.web.app`)을 로컬에서 띄우는 반복 작업을 처리한다.

## 절차

1. **기존 프로세스 확인 및 정리**

   8000번 포트를 이미 쓰고 있는 프로세스가 있는지 확인하고, 있으면 종료한다.

```bash
   lsof -ti:8000 | xargs kill -9 2>/dev/null || true
```

2. **서버 실행**

   `--reload` 옵션으로 백그라운드 실행한다.

```bash
   uv run uvicorn sprint_quiz.web.app:app --reload --host 0.0.0.0 --port 8000 > /tmp/sprint-quiz-server.log 2>&1 &
```

3. **기동 확인**

```bash
   for i in 1 2 3 4 5; do
     if curl -sf http://localhost:8000/ > /dev/null; then
       echo "✅ 서버 정상 기동"
       break
     fi
     sleep 1
   done
```

   실패하면:
```bash
   tail -n 30 /tmp/sprint-quiz-server.log
```

4. **결과 안내**

   `http://localhost:8000` 주소 안내. 확인할 특정 페이지 있으면 전체 경로 안내.

## 주의

- `--reload` 켜져 있어 코드만 고치면 재시작 불필요. "적용이 안 된다" 하면 먼저 브라우저 강제 새로고침 안내.
- 백그라운드 실행 시 로그 경로(`/tmp/sprint-quiz-server.log`) 기억.
- 작업 종료 시 서버 내리기:
```bash
  lsof -ti:8000 | xargs kill -9 2>/dev/null || true
```
