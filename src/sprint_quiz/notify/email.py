"""이메일 발송

Resend API로 복습 질문을 이메일 구독자에게 보낸다.
답변은 본문 하단에 구분선으로 나눠 포함한다 (MVP 방식).
Phase 5에서 답변 확인 페이지가 생기면 링크 방식으로 전환한다.
"""

import json
import resend
import os
from dotenv import load_dotenv

from sprint_quiz.db.repository import (
    get_next_pending_quiz,
    mark_quiz_sent,
    get_active_subscribers,
)

load_dotenv()

resend.api_key = os.environ["RESEND_API_KEY"]

# 도메인 인증 전에는 Resend 테스트 도메인으로만 발신 가능하며,
# 수신도 계정 소유자 본인 이메일로만 된다.
# 팀원들에게 보내려면 본인 도메인을 등록하고 DNS 인증을 거쳐야 한다.
FROM_ADDRESS = "Sprint Quiz <onboarding@resend.dev>"

def format_email_html(quiz) -> str:
    """이메일 본문을 HTML로 만든다.

    다크모드 대응:
    - color-scheme 메타 태그로 다크모드를 인지한다고 알린다
    - prefers-color-scheme 미디어쿼리 (Apple Mail 등에서 동작)
    - 배경색과 글자색을 명시해 클라이언트가 임의로 반전시킬 여지를 줄인다
    """
    try:
        hints = json.loads(quiz["keywords_hint"] or "[]")
    except json.JSONDecodeError:
        hints = []

    hints_html = (
        f'<p class="sub" style="color:#666666;font-size:13px;">'
        f'💡 핵심 단어: {", ".join(hints)}</p>'
        if hints
        else ""
    )

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <!-- 이 메일이 라이트/다크 양쪽을 지원한다고 클라이언트에 알린다.
       이게 없으면 일부 클라이언트가 강제로 색을 반전시킨다. -->
  <meta name="color-scheme" content="light dark">
  <meta name="supported-color-schemes" content="light dark">
  <style>
    /* Apple Mail, iOS Mail 등 미디어쿼리를 지원하는 클라이언트에서 동작한다.
       Gmail은 미디어쿼리를 무시하고 자체 반전 로직을 쓴다. */
    @media (prefers-color-scheme: dark) {{
      .wrapper {{ background-color: #1a1a1a !important; }}
      .body    {{ color: #e8e8e8 !important; }}
      .sub     {{ color: #a0a0a0 !important; }}
      .divider {{ border-color: #444444 !important; }}
    }}
  </style>
</head>
<body style="margin:0;padding:0;">
  <div class="wrapper" style="background-color:#ffffff;padding:24px 0;">
    <div class="body" style="font-family:sans-serif;max-width:480px;
                             margin:0 auto;padding:0 16px;color:#1a1a1a;">

      <p class="sub" style="color:#888888;font-size:13px;margin:0;">
        📚 오늘의 복습 질문 · {quiz['topic']}
      </p>

      <h2 style="margin:8px 0 0 0;">{quiz['question']}</h2>

      <p class="sub" style="color:#999999;font-size:13px;margin-top:32px;">
        먼저 스스로 떠올려본 뒤 아래 답변을 확인해보세요.
      </p>

      <hr class="divider" style="border:none;border-top:1px solid #dddddd;margin:16px 0;">

      <p style="font-weight:bold;margin:0;">A. {quiz['answer']}</p>
      {hints_html}

    </div>
  </div>
</body>
</html>"""


def send_quiz_email(to_address: str, quiz) -> None:
    """구독자 한 명에게 질문 메일을 보낸다.
    실패하면 예외가 그대로 올라간ㄷ. 호출하는 쪽에서 처리한다.
    """

    resend.Emails.send({
        "from": FROM_ADDRESS,
        "to": to_address,
        "subject": f"[Sprint Quiz] {quiz['question']}",
        "html": format_email_html(quiz),
    })


def send_daily_email()-> bool:
    """발송 대기 중인 질문 하나를 이메일 구독자 전체에게 보낸다.

    Returns:
        발송했으면 True, 보낼 질문이나 구독자가 없으면 False
    """
    quiz = get_next_pending_quiz()
    if quiz is None:
        print("발송한 질문이 없습니다.")
        return False

    subscribers = get_active_subscribers(channel="email")
    if not subscribers:
        print("이메일 구독자가 없습니다.")
        return False

    print(f"이메일 발송 ({len(subscribers)}명)")

    for sub in subscribers:
        try:
            send_quiz_email(sub["address"], quiz)
            print(f"  발송 완료 → {sub['address']}")
        except Exception as e:
            # 한 명이 실패해도 나머지는 계속 발송한다
            print(f"  [실패] {sub['address']} - {e}")

    # 발송을 시도했으므로 이 질문은 sent로 표시한다
    mark_quiz_sent(quiz["id"])
    print(f"발송 처리 완료: {quiz['question']}")
    return True