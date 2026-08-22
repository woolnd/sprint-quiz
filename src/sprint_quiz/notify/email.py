"""이메일 발송

Resend API로 복습 질문을 이메일 구독자에게 보낸다.
답변은 본문 하단에 구분선으로 나눠 포함한다 (MVP 방식).
Phase 5에서 답변 확인 페이지가 생기면 링크 방식으로 전환한다.
"""

import html
import json
import resend
import os
from datetime import date
from pathlib import Path
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

_ICON_DIR = Path(__file__).resolve().parent.parent / "web" / "static" / "icons"


def _inline_icon(filename: str, content_id: str) -> resend.Attachment:
    """PNG 아이콘을 CID 인라인 첨부로 만든다.

    Gmail은 <img src="data:...">(base64 인라인)를 보안상 렌더링하지 않는다.
    CID 첨부 + <img src="cid:...">만 Gmail 포함 대부분 클라이언트에서 보인다.
    """
    return {
        "filename": filename,
        "content": list((_ICON_DIR / filename).read_bytes()),
        "content_type": "image/png",
        "content_id": content_id,
    }


# 모듈 로드 시 한 번만 읽어서 재사용한다.
# fire.png("5일 연속" 배지용)는 실제 스트릭 데이터가 없어 이번에도 붙이지 않는다.
ICON_ATTACHMENTS = [
    _inline_icon("logo.png", "header-logo"),
    _inline_icon("help.png", "question-icon"),
]


def format_email_html(quiz) -> str:
    """이메일 본문을 HTML로 만든다.

    이메일 클라이언트(특히 Outlook)는 flexbox·CSS 변수·외부 폰트/아이콘을
    지원하지 않으므로 table 레이아웃 + 인라인 스타일로 작성한다.

    다크모드 대응:
    - color-scheme 메타 태그로 다크모드를 인지한다고 알린다
    - prefers-color-scheme 미디어쿼리 (Apple Mail 등에서 동작)
    - 배경색과 글자색을 명시해 클라이언트가 임의로 반전시킬 여지를 줄인다
    """
    try:
        hints = json.loads(quiz["keywords_hint"] or "[]")
    except json.JSONDecodeError:
        hints = []

    topic = html.escape(quiz["topic"])
    question = html.escape(quiz["question"])
    answer = html.escape(quiz["answer"])
    today = date.today().strftime("%Y년 %-m월 %-d일")

    hints_html = (
        f'<p style="margin:16px 0 0;font-size:13px;color:#444653;">'
        f'💡 핵심 단어: {html.escape(", ".join(hints))}</p>'
        if hints
        else ""
    )

    font_stack = "'Inter',-apple-system,'Segoe UI',Roboto,sans-serif"

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <!-- 이 메일이 라이트/다크 양쪽을 지원한다고 클라이언트에 알린다.
       이게 없으면 일부 클라이언트가 강제로 색을 반전시킨다. -->
  <meta name="color-scheme" content="light dark">
  <meta name="supported-color-schemes" content="light dark">
  <title>Sprint Quiz - 오늘의 퀴즈</title>
  <!-- Inter를 시도하되, 대부분의 메일 클라이언트(Gmail/Outlook)는 <link> 웹폰트를
       무시하므로 -apple-system 등 시스템 폰트로 자연스럽게 폴백된다. -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    /* Apple Mail, iOS Mail 등 미디어쿼리를 지원하는 클라이언트에서 동작한다.
       Gmail은 미디어쿼리를 무시하고 자체 반전 로직을 쓴다. */
    @media (prefers-color-scheme: dark) {{
      .bg-page   {{ background-color: #121212 !important; }}
      .bg-card   {{ background-color: #1e1e1e !important; border-color: #333333 !important; }}
      .bg-quiz   {{ background-color: #262626 !important; border-color: #383838 !important; }}
      .bg-note   {{ background-color: #262626 !important; }}
      .bg-footer {{ background-color: #1a1a1a !important; border-color: #333333 !important; }}
      .text-main {{ color: #e8e8e8 !important; }}
      .text-sub  {{ color: #a0a0a0 !important; }}
      .divider   {{ border-color: #383838 !important; }}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background-color:#f3f4f5;">
  <table role="presentation" class="bg-page" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f3f4f5;">
    <tr>
      <td align="center" style="padding:48px 16px;">
        <table role="presentation" class="bg-card" width="600" cellpadding="0" cellspacing="0"
               style="max-width:600px;width:100%;background-color:#ffffff;border:1px solid #e1e3e4;border-radius:12px;">
          <!-- Header -->
          <tr>
            <td align="center" style="padding:24px 32px;border-bottom:1px solid #e1e3e4;">
              <table role="presentation" cellpadding="0" cellspacing="0">
                <tr>
                  <td valign="middle">
                    <img src="cid:header-logo" width="32" height="32" alt="" style="display:block;border-radius:8px;">
                  </td>
                  <td style="padding-left:8px;font-family:{font_stack};font-size:24px;font-weight:700;color:#00288e;">
                    Sprint Quiz
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td class="text-main" style="padding:48px 32px;font-family:{font_stack};color:#191c1d;">
              <p style="margin:0 0 8px;text-align:center;font-size:14px;font-weight:600;
                        letter-spacing:0.01em;text-transform:uppercase;color:#00288e;">
                오늘의 퀴즈 - {today}
              </p>
              <p class="text-main" style="margin:0 0 24px;text-align:center;font-size:18px;
                        font-weight:600;line-height:1.5;color:#191c1d;">
                {topic}에 대해서 복습하는 질문입니다!
              </p>

              <!-- Quiz card -->
              <table role="presentation" class="bg-quiz" width="100%" cellpadding="0" cellspacing="0"
                     style="background-color:#f8f9fa;border:1px solid #e1e3e4;border-radius:12px;">
                <tr>
                  <td style="padding:32px;">
                    <table role="presentation" cellpadding="0" cellspacing="0">
                      <tr>
                        <td valign="middle">
                          <img src="cid:question-icon" width="32" height="32" alt="" style="display:block;">
                        </td>
                        <td style="padding-left:16px;font-family:{font_stack};font-size:18px;
                                   font-weight:600;line-height:1.4;color:#191c1d;">
                          {question}
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <p class="text-sub" style="margin:24px 0 0;font-size:13px;color:#999999;">
                먼저 스스로 떠올려본 뒤 아래 답변을 확인해보세요.
              </p>

              <hr class="divider" style="border:none;border-top:1px solid #dddddd;margin:16px 0;">

              <!-- Answer -->
              <table role="presentation" class="bg-note" width="100%" cellpadding="0" cellspacing="0"
                     style="background-color:#f3f4f5;border-radius:8px;">
                <tr>
                  <td style="padding:16px;">
                    <p style="margin:0;font-size:16px;font-weight:700;line-height:1.6;">A. {answer}</p>
                  </td>
                </tr>
              </table>
              {hints_html}
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td class="bg-footer" align="center" style="padding:32px;background-color:#edeeef;
                                                          border-top:1px solid #e1e3e4;border-radius:0 0 12px 12px;
                                                          font-family:{font_stack};
                                                          font-size:12px;color:#444653;">
              © {date.today().year} Sprint Quiz · 본 메일은 발신 전용입니다.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
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
        "attachments": ICON_ATTACHMENTS,
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
