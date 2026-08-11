"""자료 인덱싱 스크립트

data/ 폴더의 마크다운 자료를 읽어 키워드를 추출하고ㅡ
미출체 키워드로 질문을 생성해 DB에 저장한다.

사용법:
    uv run python scripts/index.py            # 질문 5개 생성 (기본값)
    uv run python scripts/index.py --quiz 10  # 질문 10개 생성
    uv run python scripts/index.py --quiz 0   # 자료·키워드만 등록, 질문 생성 안 함
"""

import argparse

from sprint_quiz.db.schema import init_db
from sprint_quiz.db.repository import (
    save_material,
    save_keywords,
    get_unused_keywords,
    save_quiz,
    get_pending_quizzes
)
from sprint_quiz.parser.base import read_document
from sprint_quiz.parser.markdown import list_markdown_files
from sprint_quiz.generator.keyword import extract_keywords
from sprint_quiz.generator.quiz import generate_quiz

DATA_DIR = "data/sample"

def index_materials() -> tuple[int, int]:
    """자료를 읽어 DB에 저장하고 키워드를 추출한다.
    Returns:
        (새로 등록된 자료 수, 새로 저장된 키워드 수)
    """

    files = list_markdown_files(DATA_DIR)
    print(f"자료 파일 {len(files)}개 발견\n")

    new_materials = 0
    new_keywords = 0

    for path in files:
        doc = read_document(path)

        # 이미 처리한 자료면 None이 반환된다 (content_hash UNIQU 제약)
        material_id = save_material(
            doc["filename"], doc["content"], doc["content_hash"]
        )

        if material_id is None:
            print(f" [스킵] {doc["filename"]} - 이미 등록됨")
            continue

        # 새 자료일 때만 키워드 추출 API를 호출한다
        keywords = extract_keywords(doc['content'], doc['filename'])
        saved = save_keywords(material_id, keywords)

        print(f" [등록] {doc['filename']} - 키워드 {saved}개")
        new_materials += 1
        new_keywords += saved

    return new_materials, new_keywords


def generate_quizzes(count: int) -> int:
    """미출제 키워드로 질문을 생성해 질문한다.
    
    Args:
        count: 생성할 질문 개수
    
    Returns:
        실제로 생성된 질문 수
    """

    if count <= 0 :
        return 0

    targets = get_unused_keywords(limit=count)

    if not targets:
        print("\n미출제 키워드가 없습니다.")
        return 0

    print(f"\n질문 생성 ({len(targets)}개)")
    generated = 0

    for kw in targets:
        try:
            quiz = generate_quiz(
                content=kw["content"],
                keyword=kw["keyword"],
                topic=kw["topic"],
                source=kw["filename"]
            )
            save_quiz(kw["id"], quiz)
            print(f" {quiz["question"]}")
            generated += 1
        except Exception as e:
            # 하나 실패해도 나머지는 계속 처리한다
            print(f" [실패] {kw['keyword']} - {e}")

    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description="학습 자료를 인덱싱하고 질문을 생성한다")
    parser.add_argument(
        "--quiz",
        type=int,
        default=5,
        help="생성할 질문 개수 (기본 5, 0이면 생성하지 않음)"
    )
    args = parser.parse_args()

    init_db()

    new_materials, new_keywords = index_materials()
    generated = generate_quizzes(args.quiz)
    pending = len(get_pending_quizzes())

    print("\n" + "=" * 40)
    print(f"신규 자료      {new_materials}개")
    print(f"신규 키워드    {new_keywords}개")
    print(f"생성된 질문    {generated}개")
    print(f"발송 대기      {pending}개")


if __name__ == "__main__":
    main()