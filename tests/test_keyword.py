from sprint_quiz.parser.base import read_document
from sprint_quiz.parser.markdown import list_markdown_files
from sprint_quiz.generator.keyword import extract_keywords


files = list_markdown_files("data/sample")

for f in files:
    doc = read_document(f)
    print(f"\n=== {doc['filename']} ===")

    keywords = extract_keywords(doc["content"], doc["filename"])

    print(f"추출된 키워드 {len(keywords)}개")
    for kw in keywords:
        print(f"  [{kw['topic']}] {kw['keyword']}")