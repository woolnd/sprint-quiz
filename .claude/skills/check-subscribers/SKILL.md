---
name: check-subscribers
description: Sprint Quiz의 이메일 구독자가 실제로 등록됐는지 확인할 때 사용한다. "구독자 확인해줘", "등록됐는지 봐줘", "누가 가입했어", "이메일 목록 보여줘" 같은 요청에서 트리거된다. sprint_quiz.db의 subscribers 테이블을 조회해서 보여준다.
---

# 구독자 확인

`sprint_quiz.db`의 `subscribers` 테이블을 직접 조회해서 등록 현황을 보여준다.

## 절차

1. **전체 구독자 목록 조회** (최근 등록순)

```bash
   sqlite3 -header -column sprint_quiz.db \
     "SELECT id, channel, address, is_active, created_at FROM subscribers ORDER BY id DESC;"
```

2. **채널별 활성 구독자 수 요약**

```bash
   sqlite3 sprint_quiz.db \
     "SELECT channel, COUNT(*) AS total, SUM(is_active) AS active FROM subscribers GROUP BY channel;"
```

3. 특정 이메일 하나만 확인하고 싶다고 하면:

```bash
   sqlite3 sprint_quiz.db \
     "SELECT * FROM subscribers WHERE address = '<이메일>';"
```

## 주의

- `sprint_quiz.db`는 `.gitignore`에 걸려있는 로컬 파일이다 — 실제 구독자 개인정보이므로 결과를 커밋하거나 외부로 내보내지 않는다.
- 테스트용으로 넣은 더미 이메일(`ponytail-test-*@example.com` 등)이 섞여 있을 수 있으니, 실제 등록 여부를 판단할 때는 주소를 확인하고 필요하면 삭제를 제안한다.
