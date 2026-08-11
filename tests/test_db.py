# tests/test_db.py
from sprint_quiz.db.schema import init_db
from sprint_quiz.db.repository import (
    save_material, save_keywords, get_unused_keywords,
    save_quiz, get_pending_quizzes,
)
from sprint_quiz.parser.base import read_document
from sprint_quiz.parser.markdown import list_markdown_files
from sprint_quiz.generator.keyword import extract_keywords
from sprint_quiz.generator.quiz import generate_quiz

# 테이블 생성 (이미 있으면 그대로 둔다)
init_db()

# 1. 자료 저장
files = list_markdown_files("data/sample")
doc = read_document(files[0])
material_id = save_material(doc["filename"], doc["content"], doc["content_hash"])

if material_id is None:
    # 두 번째 실행부터는 여기로 온다 = 중복 방지 동작
    print(f"이미 처리한 자료입니다: {doc['filename']}")
else:
    print(f"자료 저장 완료 (id={material_id})")

    # 2. 키워드 추출 및 저장 (자료가 새로 들어온 경우에만 API 호출)
    keywords = extract_keywords(doc["content"], doc["filename"])
    saved = save_keywords(material_id, keywords)
    print(f"키워드 {saved}개 저장")

# 3. 미출제 키워드 2개로 질문 생성 (비용 절약을 위해 2개만)
targets = get_unused_keywords(limit=2)
print(f"\n미출제 키워드 {len(targets)}개로 질문 생성")

for kw in targets:
    quiz = generate_quiz(
        content=kw["content"],    # JOIN으로 함께 가져온 원본 자료
        keyword=kw["keyword"],
        topic=kw["topic"],
        source=kw["filename"],
    )
    quiz_id = save_quiz(kw["id"], quiz)
    print(f"  저장 완료 (id={quiz_id}) — {quiz['question']}")

# 4. 저장 결과 확인
print(f"\n발송 대기 질문: {len(get_pending_quizzes())}개")