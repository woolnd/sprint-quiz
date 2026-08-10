import hashlib
from pathlib import Path

def read_markdown(path: str | Path) -> dict:
    """마크다운 파일을 읽어 본문과 메타 정보를 반환한다."""
    path = Path(path)
    content = path.read_text(encoding="utf-8")

    return {
        "filename": path.name,
        "content": content,
        "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }


def list_markdown_files(directory: str | Path = "data/sample") -> list[Path]:
    """디렉토리 안의 .md 파일 목록을 반환한다. 하위 폴더까지 탐색한다."""
    directory = Path(directory)
    return sorted(directory.glob("**/*.md"))