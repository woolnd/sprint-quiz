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


BATCH_SYSTEM_PROMPT = """당신은 AI/ML 부트캠프 학생을 위한 복습 질문을 만드는 assistant입니다.

질문 형식:
- 질문은 반드시 "{키워드}에 대해서 설명해주세요." 한 문장으로만 만드세요.
- 요청받은 키워드 각각에 대해 질문을 하나씩 만드세요.
- 여러 키워드를 한 질문에 묶지 마세요. 키워드 하나당 질문 하나입니다.

좋은 질문 예시:
- "CNN에 대해서 설명해주세요."
- "Padding에 대해서 설명해주세요."
- "Max Pooling에 대해서 설명해주세요."

절대 만들면 안 되는 형태:
- "A가 B보다 나은 이유를 설명해주세요."  (비교)
- "A의 장점과 주의할 점을 설명해주세요."  (여러 항목 요구)
- "A가 무엇이고, 왜 사용하는지 설명해주세요."  (복합 질문)
- "A와 B에 대해서 설명해주세요."  (키워드 묶기)

답변 작성:
- 3문장을 넘기지 마세요.
- 비전공자도 이해할 수 있게 쉽게 쓰세요.
- 학습 자료의 내용을 기반으로 하되, 이해를 돕기 위해 일반적으로 알려진 배경 설명이나 간단한 예시를 덧붙여도 됩니다.
- 단, 자료와 모순되는 내용은 절대 넣지 마세요.
- 뒤쪽 키워드도 앞쪽과 같은 수준으로 성의 있게 작성하세요.

답변은 아래 JSON 형식으로만 출력하세요. 다른 텍스트는 포함하지 마세요.
items 배열의 순서는 요청받은 키워드 순서와 같아야 합니다.
{
  "items": [
    {
      "keyword": "요청받은 키워드",
      "question": "질문",
      "answer": "3문장 이내의 모범 답안",
      "keywords": ["답변에 포함되면 좋을 핵심 단어 3개"]
    }
  ]
}"""

def generate_quiz_batch(
        content: str,
        keywords: list[dict],
        source: str = ""
) -> list[dict]:
    """여러 키워드의 질문을 한번의 API 호출로 생성한다.

    Args:
        content: 학습 자료 원문
        keywords: [{"keyword": ..., "topic": ..., "id": ...}, ...] 형태의 목록
        source: 원본 파일명

    Returns:
        생성된 질문 목록. 요청 순서와 동일하게 반환된다.
    """
    # 프롬프트에 넣을 키워드 목록을 번호 매겨 나열한다
    keyword_list = "\n".join(
        f"{i}. {kw['keyword']}" for i, kw in enumerate(keywords, start=1)
    )

    user_message = f"""아래 학습 자료를 참고해서 다음 {len(keywords)}개 키워드 각각에 대해 복습 질문을 만들어주세요.

[키워드 목록]
{keyword_list}

[학습 자료]
{content}"""

    with Timer() as timer:
        response = client.messages.create(
            model=MODEL,
            max_tokens=500 * len(keywords) + 500,
            system=BATCH_SYSTEM_PROMPT,
            messages=[{"role":'user', 'content':user_message}]
        )

    text = response.content[0].text.strip()

    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    parse_success = True
    try:
        data = json.loads(text)
        items = data['items']
    except (json.JSONDecodeError, KeyError):
        parse_success = False
        items = None

    log_call(
        purpose="quiz_generate_batch",
        model=MODEL,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        latency_ms=timer.elapsed_ms,
        parse_success=parse_success,
        note=f"batch_size={len(keywords)}"
    )

    if not parse_success:
        raise ValueError(f"JSON 파싱 실패 (batch_size={len(keywords)})")

    # 요청한 개수와 응답 개수가 다르면 짝이 어긋나므로 중단한다
    if len(items) != len(keywords):
        raise ValueError(
            f"요청 {len(keywords)}개, 응답 {len(items)}개로 개수가 맞지 않습니다."
        )

    # 요청 순서를 기준으로 topic, source를 코드에서 채운데
    quizzes = []
    for kw, item in zip(keywords, items):
        item['keyword'] = kw['keyword']
        item['topic'] = kw.get('topic', '')
        item['source'] = source
        quizzes.append(item)

    return quizzes