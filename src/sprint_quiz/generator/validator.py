import json
import os

from anthropic import Anthropic
from dotenv import load_dotenv

from sprint_quiz.logger import log_call, Timer

load_dotenv()

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# 판별은 생성보다 쉬운 태스크라 같은 Haiku로 충분하다.
# (Phase 3-B에서 이 판정 결과가 자체 분류기의 학습 라벨이 된다)
MODEL = "claude-haiku-4-5-20251001"

VALIDATOR_SYSTEM_PROMPT = """당신은 AI/ML 복습 질문의 품질을 검증하는 assistant입니다.
주어진 학습 자료와 질문·답변을 보고, 아래 4가지 기준을 각각 판정하세요.

1. groundedness — 답변 내용이 학습 자료에 근거하는가?
   - 자료에 없는 배경 설명이나 일반 상식을 덧붙이는 것은 허용됩니다.
   - 다만 자료의 내용과 모순되거나, 자료에서 전혀 다루지 않은 주제를 사실처럼 설명하면 불합격입니다.

2. correctness — 답변이 사실로서 정확한가?
   - 명백한 오류나 잘못된 설명이 있으면 불합격입니다.

3. simplicity — 개념 확인 수준의 간단한 질문인가?
   - 질문이 "{키워드}에 대해서 설명해주세요." 형태여야 합니다.
   - 비교("A가 B보다 나은 이유"), 복합 질문("무엇이고 왜 사용하는지"),
     여러 항목 요구("장점과 단점"), 계산 문제는 모두 불합격입니다.

4. duplicate — 최근 출제된 질문들과 중복되지 않는가?
   - 최근 질문 목록이 주어지면, 사실상 같은 개념을 묻는 질문인지 확인하세요.
   - 목록이 비어 있으면 통과로 판정하세요.

각 기준은 서로 독립적으로 판정하세요.
- simplicity는 질문의 형식만 봅니다. 답변 내용이 아무리 부실해도
  질문이 "{키워드}에 대해서 설명해주세요." 형태면 simplicity는 통과입니다.
- groundedness는 "자료에 근거가 있는가"만 봅니다.
  자료 밖의 내용이어도 그 내용 자체가 사실이면 correctness는 통과입니다.
- correctness는 "내용이 사실로 맞는가"만 봅니다.
  자료에 없는 내용이라는 이유만으로 correctness를 불합격 처리하지 마세요.
- 한 기준이 불합격이라고 해서 다른 기준까지 불합격으로 판정하지 마세요.
  각 항목을 따로따로 판단하세요.

판정 기준:
- 4가지가 모두 통과여야 최종 통과(passed=true)입니다.
- 애매한 경우는 통과로 판정하세요. 명백한 문제가 있을 때만 불합격 처리합니다.

아래 JSON 형식으로만 출력하세요. 다른 텍스트는 포함하지 마세요.
{
  "groundedness": true,
  "correctness": true,
  "simplicity": true,
  "duplicate": true,
  "passed": true,
  "reason": "불합격 항목이 있으면 그 이유를 한 문장으로. 통과면 빈 문자열."
}"""


def validate_quiz(
        content: str,
        quiz: dict,
        recent_questions: list[str] | None = None
) -> dict:
    """생성된 질문·답변을 검증한다.

    Args:
        content: 학습 자료 원문 (groundedness 판정 근거)
        quiz: question, answer, keyword를 담은 딕셔너리
        recent_questions: 중복 판정용 최근 질문 목록

    Returns:
        판정 결과 (passed, groundedness, correctness, simplicity, duplicate, reason)
    """

    recent = recent_questions or []
    recent_text = "\n".join(f"- {q}" for q in recent) if recent else "(없음)"

    user_message = f"""아래 질문·답변을 검증해주세요.
[키워드]
{quiz["keyword"]}

[질문]
{quiz["question"]}

[답변]
{quiz["answer"]}

[최근 출제된 질문]
{recent_text}

[학습 자료]
{content}"""

    with Timer() as timer:
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,   # 판정 결과만 받으므로 짧게
            system=VALIDATOR_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

    text = response.content[0].text.strip()

    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    parse_success = True
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        parse_success = False
        result = None

    log_call(
        purpose="quiz_validate",
        model=MODEL,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        latency_ms=timer.elapsed_ms,
        parse_success=parse_success,
        note=quiz["keyword"],
    )

    if not parse_success:
        raise ValueError(f"검증 결과 JSON 파싱 실패: {quiz['keyword']}")

    return result