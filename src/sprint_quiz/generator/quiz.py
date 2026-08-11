import json
import os
from anthropic import Anthropic
from dotenv import load_dotenv

from sprint_quiz.logger import log_call, Timer

load_dotenv()

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """당신은 AI/ML 부트캠프 학생을 위한 복습 질문을 만드는 assistant입니다.

질문 형식:
- 질문은 반드시 "{키워드}에 대해서 설명해주세요." 한 문장으로만 만드세요.
- 지정된 키워드 하나에 대해서만 질문을 만드세요. 다른 개념으로 새지 마세요.

좋은 질문 예시:
- "CNN에 대해서 설명해주세요."
- "Padding에 대해서 설명해주세요."
- "Max Pooling에 대해서 설명해주세요."

절대 만들면 안 되는 형태:
- "A가 B보다 나은 이유를 설명해주세요."  (비교)
- "A의 장점과 주의할 점을 설명해주세요."  (여러 항목 요구)
- "A가 무엇이고, 왜 사용하는지 설명해주세요."  (복합 질문)
- "A가 무엇인지, 특히 어떻게 작동하는지 설명해주세요."  (조건 추가)

답변 작성:
- 3문장을 넘기지 마세요.
- 비전공자도 이해할 수 있게 쉽게 쓰세요.
- 학습 자료의 내용을 기반으로 하되, 이해를 돕기 위해 일반적으로 알려진 배경 설명이나 간단한 예시를 덧붙여도 됩니다.
- 단, 자료와 모순되는 내용은 절대 넣지 마세요.

답변은 아래 JSON 형식으로만 출력하세요. 다른 텍스트는 포함하지 마세요.
{
  "question": "질문",
  "answer": "3문장 이내의 모범 답안",
  "keywords": ["답변에 포함되면 좋을 핵심 단어 3개"]
}"""

def generate_quiz(content: str, keyword: str, topic: str = "", source: str = "") -> dict:
    """지정한 키워드에 대한 복습 질문과 모범 답안을 생성한다."""
    user_message = f"""아래 학습 자료를 참고해서 "{keyword}" 개념에 대한 복습 질문 1개를 만들어주세요.

[학습 자료]
{content}"""

    with Timer() as timer:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

    text = response.content[0].text.strip()

    # 마크다운 코드블록으로 감싸져 나오면 제거
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    parse_success = True
    try:
        quiz = json.loads(text)
    except json.JSONDecodeError:
        parse_success = False
        quiz = None

    log_call(
        purpose="quiz_generate",
        model=MODEL,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        latency_ms=timer.elapsed_ms,
        parse_success=parse_success,
        note=keyword,
    )

    if not parse_success:
        raise ValueError(f"JSON 파싱 실패: {keyword}")

    # LLM이 판단할 필요 없는 정보는 코드에서 직접 넣는다
    quiz["keyword"] = keyword
    quiz["topic"] = topic
    quiz["source"] = source

    return quiz