from sprint_quiz.parser.base import read_document
from sprint_quiz.parser.markdown import list_markdown_files
from sprint_quiz.generator.keyword import extract_keywords
from sprint_quiz.generator.quiz import generate_quiz

files = list_markdown_files("data/sample")
doc = read_document(files[0])

keywords = extract_keywords(doc["content"], doc["filename"])

for kw in keywords:
    quiz = generate_quiz(
        content=doc["content"],
        keyword=kw["keyword"],
        topic=kw["topic"],
        source=kw["source"]
    )

    print(f"\n{'=' * 50}")
    print(f"[{quiz['topic']}] {quiz['keyword']}")
    print(f"\nQ. {quiz['question']}")
    print(f"\nA. {quiz['answer']}")
    print(f"\n힌트: {', '.join(quiz['keywords'])}")