#!/usr/bin/env bash
# PreToolUse 훅: Bash 도구 호출을 가로채서 git commit 실행 직전에
# .env / *.db / llm_calls.csv 가 스테이징돼 있으면 커밋을 차단한다.
#
# Claude Code는 이 스크립트에 도구 호출 정보를 JSON으로 stdin에 흘려준다.
# 우리는 그 JSON에서 command 필드만 꺼내서 "git commit"이 포함돼 있는지 본다.

set -euo pipefail

# stdin으로 들어온 JSON 전체를 읽는다
INPUT=$(cat)

# jq 없이도 동작하도록 command 필드를 grep+sed로 대충 추출
# (jq가 있으면 더 정확하게 뽑을 수 있어 우선 시도)
if command -v jq >/dev/null 2>&1; then
  COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
else
  COMMAND=$(echo "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"command"[[:space:]]*:[[:space:]]*"//;s/"$//')
fi

# git commit이 아니면 그냥 통과 (exit 0 = 허용)
if [[ "$COMMAND" != *"git commit"* ]]; then
  exit 0
fi

# 스테이징된 파일 목록에서 금지 패턴을 찾는다
BLOCKED=$(git diff --cached --name-only 2>/dev/null | grep -E '(^|/)\.env($|\.)|\.db$|llm_calls\.csv$' || true)

if [[ -n "$BLOCKED" ]]; then
  # exit code 2 = 차단. stderr 메시지가 Claude에게 그대로 전달돼
  # 왜 막혔는지 알고 다음 행동을 조정할 수 있다.
  echo "🚫 커밋 차단: 다음 파일은 절대 커밋하면 안 됩니다 (CLAUDE.md 절대 규칙)" >&2
  echo "$BLOCKED" >&2
  echo "git reset HEAD <파일>로 스테이징을 해제한 뒤 다시 커밋하세요." >&2
  exit 2
fi

exit 0
