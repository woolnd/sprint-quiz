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

    Args:
        quiz: quizzes 테이블의 한 행 (question, answer, topic, keywords_hint)

    Returns:
        인라인 스타일이 적용된 HTML 문자열
    """

    try:
        hints = json.loads(quiz["keywords_hint"] or "[]")
    except json.JSONDecodeError:
        hints = []

    hints_html = (
        f'<p style="color:#666;font-size:13px;">💡 핵심 단어: {", ".join(hints)}</p>'
        if hints
        else ""
    )

    # 이메일 클라이언트는 <style> 태그나 외부 CSS를 무시하는 경우가 많아
    # 각 태그에 인라인 스타일로 직접 넣는다
    return f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;">
      <p style="color:#888;font-size:13px;">📚 오늘의 복습 질문 · {quiz['topic']}</p>

      <h2 style="margin-top:8px;">{quiz['question']}</h2>

      <p style="color:#999;font-size:13px;margin-top:32px;">
        먼저 스스로 떠올려본 뒤 아래 답변을 확인해보세요.
      </p>

      <hr style="border:none;border-top:1px solid #ddd;margin:16px 0;">

      <p style="font-weight:bold;">A. {quiz['answer']}</p>
      {hints_html}
    </div>
    """


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