import time

from sprint_quiz.db.schema import init_db
from sprint_quiz.db.repository import get_unused_keywords, save_quiz
from sprint_quiz.generator.quiz import generate_quiz, generate_quiz_batch


init_db()

BATCH_SIZE = 5

targets = get_unused_keywords(limit=BATCH_SIZE)
if len(targets) < BATCH_SIZE:
    print(f"미출제 키워드가 {len(targets)}개 뿐입니다.")


content = targets[0]['content']
source = targets[0]['filename']

start = time.perf_counter() 
quizzes = generate_quiz_batch(
    content=content,
    keywords=[dict(kw) for kw in targets],
    source=source
)

elapsed = time.perf_counter() - start
print(f"배치 생성 완료 - {len(quizzes)}개, {elapsed:.1f}초\n")

for kw, quiz in zip(targets, quizzes):
    print(f"[{quiz['topic']}] {quiz['keyword']}")
    print(f"Q. {quiz['question']}")
    print(f"A. {quiz['answer']}")
    print(f"힌트: {', '.join(quiz['keywords'])}\n")
    save_quiz(kw["id"], quiz)