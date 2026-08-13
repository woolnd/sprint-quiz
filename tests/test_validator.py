from sprint_quiz.db.schema import init_db
from sprint_quiz.db.repository import get_unused_keywords
from sprint_quiz.generator.validator import validate_quiz
from sprint_quiz.parser.base import read_document
from sprint_quiz.parser.markdown import list_markdown_files

init_db()

files = list_markdown_files("data/sample")
content = read_document(files[0])["content"]

# 각 기준을 하나씩 위반하도록 만든 테스트 케이스
cases = [
    {
        "name": "정상 (통과 기대)",
        "quiz": {
            "keyword": "Padding",
            "question": "Padding에 대해서 설명해주세요.",
            "answer": "Padding은 입력 데이터의 가장자리에 0을 추가해 입력 크기를 확장하는 기법입니다. 가장자리 정보 손실을 막고 원하는 출력 크기를 유지하는 데 사용됩니다.",
        },
    },
    {
        "name": "simplicity 위반 — 비교 질문",
        "quiz": {
            "keyword": "Padding",
            "question": "Padding이 Stride보다 중요한 이유를 설명해주세요.",
            "answer": "Padding은 정보 손실을 막고, Stride는 연산량을 줄입니다. 둘 중 Padding이 더 중요합니다.",
        },
    },
    {
        "name": "simplicity 위반 — 복합 질문",
        "quiz": {
            "keyword": "Stride",
            "question": "Stride가 무엇이고, 장점과 주의할 점은 무엇인지 설명해주세요.",
            "answer": "Stride는 필터의 이동 간격입니다. 연산량을 줄이는 장점이 있지만 정보가 누락될 수 있습니다.",
        },
    },
    {
        "name": "correctness 위반 — 틀린 설명",
        "quiz": {
            "keyword": "Max Pooling",
            "question": "Max Pooling에 대해서 설명해주세요.",
            "answer": "Max Pooling은 지정된 영역에서 최솟값을 선택하는 연산입니다. 학습 가능한 가중치가 있어 역전파로 갱신됩니다.",
        },
    },
    {
        "name": "groundedness 위반 — 자료에 없는 주제",
        "quiz": {
            "keyword": "Transformer",
            "question": "Transformer에 대해서 설명해주세요.",
            "answer": "Transformer는 Self-Attention 기반의 신경망 구조로, 자연어 처리에서 널리 쓰입니다. 이 학습 자료의 CNN 파트에서 자세히 다루고 있습니다.",
        },
    },
]

# 중복 판정 테스트용
recent = ["Padding에 대해서 설명해주세요."]

for case in cases:
    result = validate_quiz(content, case["quiz"], recent_questions=[])
    mark = "통과" if result["passed"] else "불합격"
    print(f"[{mark}] {case['name']}")
    print(f"  G={result['groundedness']} C={result['correctness']} "
          f"S={result['simplicity']} D={result['duplicate']}")
    if result["reason"]:
        print(f"  사유: {result['reason']}")
    print()

# 중복 케이스 별도 테스트
dup = validate_quiz(content, cases[0]["quiz"], recent_questions=recent)
mark = "통과" if dup["passed"] else "불합격"
print(f"[{mark}] duplicate 위반 — 최근 질문과 동일")
if dup["reason"]:
    print(f"  사유: {dup['reason']}")