from pathlib import Path
from sprint_quiz.parser.markdown import read_markdown

def read_document(path: str | Path) -> dict:
    """확장자에 맞는 파서로 문서를 읽는다"""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".md":
        return read_markdown(path)
    raise ValueError(f"지원하지 않는 파일 형식입니다. {suffix}")