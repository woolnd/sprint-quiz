import json
import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """당신은 AI/ML 학습 노트에서 복습할 가치가 있는 핵심 개념을 뽑아내는 assistant입니다.

추출 기준:
- 정의를 물어볼 수 있는 구체적인 기술 용어만 추출하세요.
- 글에서 실제로 설명된 개념만 추출하세요. 단순히 언급만 된 것은 제외합니다.
- 너무 일반적이라 질문이 성립하지 않는 단어는 제외하세요.
  (제외 예: 모델, 데이터, 학습, 성능, 함수, 알고리즘, 파이썬, 코드)
- 같은 개념의 다른 표현은 하나로 합치세요. (예: "합성곱"과 "Convolution"은 하나로)
- 글의 주제가 되는 큰 개념도 반드시 포함하세요. (예: 글 전체가 CNN을 다룬다면 "CNN" 자체도 키워드입니다)
- 글에서 소제목으로 다뤄진 개념은 우선적으로 포함하세요.
- 최대 15개까지 추출하되, 억지로 채우지 마세요.

topic은 아래 목록에서 하나만 고르세요. 다른 값은 절대 사용하지 마세요.
- 데이터사이언스
- 머신러닝
- 딥러닝

아래 JSON 형식으로만 출력하세요. 다른 텍스트는 포함하지 마세요.
{
  "keywords": [
    {"keyword": "키워드", "topic": "딥러닝"},
    {"keyword": "키워드", "topic": "머신러닝"}
  ]
}"""

def extract_keywords(content: str, filename: str = "") -> list[dict]:
    """학습 노트에서 AI/ML 관련 키워드를 추출한다."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"다음 학습 노트에서 복습할 개념을 추출해주세요.\n\n{content}"}
        ]
    )

    text = response.content[0].text.strip()

    # 마크다운 코드블록으로 감싸져 나오면 제거
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    data = json.loads(text)
    keywords = data["keywords"]

    # 출처 파일명을 각 키워드에 붙인다
    for kw in keywords:
        kw["source"] = filename

    return keywords