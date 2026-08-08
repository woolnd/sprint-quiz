import json
import os
from anthropic import Anthropic
from dotenv import load_dotenv


load_dotenv()

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """당신은 AI/ML 부트캠프 학생을 위한 복습 질문을 만드는 assistant입니다.

규칙:
- 질문은 "~에 대해서 설명해주세요" 형태의 서술형 개념 질문으로 만드세요.
- 응용, 비교, 계산 문제는 절대 만들지 마세요. 개념 확인 수준만 다룹니다.
- 비전공자도 답할 수 있는 쉬운 난이도로 만드세요.
- 질문은 반드시 주어진 자료에 나온 개념으로만 만드세요.
- 답변은 자료의 내용을 기반으로 하되, 이해를 돕기 위해 일반적으로 알려진 배경 설명이나 간단한 예시를 덧붙여도 됩니다.
- 단, 자료와 모순되는 내용은 절대 넣지 마세요.

답변은 아래 JSON 형식으로만 출력하세요. 다른 텍스트는 포함하지 마세요.
{
  "question": "질문",
  "answer": "3~4문장의 모범 답안",
  "keywords": ["키워드1", "키워드2", "키워드3"],
  "topic": "주제 분류"
}"""

def generate_quiz(content: str) -> dict:
    """학습 자료 테스트로부터 질문과 모범 답안을 생성한다."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"다음 학습 자료를 바탕으로 복습 질문 1개를 만들어주세요.\n\n{content}"}
        ]
    )

    text = response.content[0].text.strip()

    # 마크다운 코드블럭으로 감싸져 나오면 제거
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    return json.loads(text)