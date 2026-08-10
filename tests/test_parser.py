from sprint_quiz.parser.base import read_document
from sprint_quiz.parser.markdown import list_markdown_files


files = list_markdown_files("data/sample")
print(f"발견된 파일: {len(files)}개")

for f in files:
    doc = read_document(f)
    print(f"\n--- {doc['filename']} ---")
    print(f"길이: {len(doc['content'])}자")
    print(f"해시: {doc['content_hash'][:12]}...")
    print(doc["content"][:200])