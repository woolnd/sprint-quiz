"""자료 인덱싱 스크립트

data/ 폴더의 마크다운 자료를 읽어 키워드를 추출하고,
미출제 키워드로 질문을 생성·검증해 DB에 저장한다.

사용법:
    uv run python scripts/index.py            # 질문 5개 생성 (기본값)
    uv run python scripts/index.py --quiz 10  # 질문 10개 생성
    uv run python scripts/index.py --quiz 0   # 자료·키워드만 등록, 질문 생성 안 함
"""

import argparse
import asyncio

from sprint_quiz.db.schema import init_db
from sprint_quiz.db.repository import (
    save_material,
    save_keywords,
    get_unused_keywords,
    save_quiz,
    get_pending_quizzes,
    save_validation,
    get_recent_questions,
)
from sprint_quiz.parser.base import read_document
from sprint_quiz.parser.markdown import list_markdown_files
from sprint_quiz.generator.keyword import extract_keywords
from sprint_quiz.generator.quiz import generate_quiz
from sprint_quiz.generator.validator import validate_quiz

DATA_DIR = "data/sample"
MAX_RETRY = 2        # 재생성 최대 횟수 (최초 1회 + 재시도 2회 = 총 3번)
MAX_CONCURRENCY = 3  # 동시에 처리할 키워드 개수 상한


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

        # 이미 처리한 자료면 None이 반환된다 (content_hash UNIQUE 제약)
        material_id = save_material(
            doc["filename"], doc["content"], doc["content_hash"]
        )

        if material_id is None:
            print(f" [스킵] {doc['filename']} - 이미 등록됨")
            continue

        # 새 자료일 때만 키워드 추출 API를 호출한다
        keywords = extract_keywords(doc["content"], doc["filename"])
        saved = save_keywords(material_id, keywords)

        print(f" [등록] {doc['filename']} - 키워드 {saved}개")
        new_materials += 1
        new_keywords += saved

    return new_materials, new_keywords


async def generate_with_validation(content: str, kw: dict) -> dict | None:
    """질문을 생성하고 검증한다. 통과할 때까지 재시도한다.

    이 함수 내부는 순차로 진행된다.
    생성 결과가 있어야 검증할 수 있고, 검증 결과가 있어야
    재생성 여부를 정할 수 있어 병렬화할 수 없기 때문이다.

    Returns:
        {"quiz": 통과한 질문, "result": 판정 결과, "attempt": 시도 횟수}
        끝내 통과하지 못하면 None
    """
    recent = get_recent_questions(limit=10)

    for attempt in range(MAX_RETRY + 1):
        quiz = await generate_quiz(
            content=content,
            keyword=kw["keyword"],
            topic=kw.get("topic", ""),
            source=kw.get("filename", ""),
        )

        result = await validate_quiz(content, quiz, recent_questions=recent)

        if result["passed"]:
            return {"quiz": quiz, "result": result, "attempt": attempt}

        # 불합격 기록은 quiz_id 없이 남긴다.
        # 이 데이터가 Phase 3-B 분류기의 "나쁜 질문" 학습 샘플이 된다.
        save_validation(None, quiz, result, attempt)
        print(f"    [재생성 {attempt + 1}회] {kw['keyword']} - {result['reason']}")

    return None


async def process_keyword(kw: dict, semaphore: asyncio.Semaphore) -> bool:
    """키워드 하나를 처리한다. 성공하면 True.

    Semaphore로 동시 실행 개수를 제한한다.
    제한이 없으면 키워드 20개가 한꺼번에 API를 호출해
    rate limit에 걸리거나 비용이 순간적으로 튄다.
    """
    async with semaphore:
        try:
            outcome = await generate_with_validation(kw["content"], kw)

            if outcome is None:
                # 재시도를 다 써도 검증을 통과하지 못한 경우
                print(f"  [포기] {kw['keyword']} - 검증 통과 실패")
                return False

            quiz_id = save_quiz(kw["id"], outcome["quiz"])
            # 통과 기록은 quiz_id와 함께 남긴다
            save_validation(
                quiz_id, outcome["quiz"], outcome["result"], outcome["attempt"]
            )

            print(f"  {outcome['quiz']['question']}")
            return True

        except Exception as e:
            # 하나 실패해도 나머지는 계속 처리한다
            print(f"  [실패] {kw['keyword']} - {e}")
            return False


async def generate_quizzes(count: int) -> int:
    """미출제 키워드로 질문을 생성하고 검증해 저장한다.

    Args:
        count: 생성할 질문 개수

    Returns:
        실제로 생성된 질문 수
    """
    if count <= 0:
        return 0

    # sqlite3.Row는 .get()이 없어 dict로 변환해둔다
    targets = [dict(kw) for kw in get_unused_keywords(limit=count)]

    if not targets:
        print("\n미출제 키워드가 없습니다.")
        return 0

    print(f"\n질문 생성 ({len(targets)}개)")
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    # 캐시 워밍: 첫 건만 먼저 처리한다.
    # 캐시는 첫 응답이 시작된 뒤에야 사용 가능하므로,
    # 처음부터 전부 동시에 보내면 모두 캐시 미스가 나 쓰기 비용이 중복 발생한다.
    first_ok = await process_keyword(targets[0], semaphore)
    generated = 1 if first_ok else 0

    # 나머지는 병렬 처리한다
    if len(targets) > 1:
        tasks = [process_keyword(kw, semaphore) for kw in targets[1:]]
        # gather는 모든 작업을 동시에 시작하고 전부 끝날 때까지 기다린다.
        # return_exceptions=True면 하나가 예외로 터져도 나머지는 계속 진행된다.
        results = await asyncio.gather(*tasks, return_exceptions=True)
        generated += sum(1 for r in results if r is True)

    return generated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="학습 자료를 인덱싱하고 질문을 생성한다"
    )
    parser.add_argument(
        "--quiz",
        type=int,
        default=5,
        help="생성할 질문 개수 (기본 5, 0이면 생성하지 않음)",
    )
    args = parser.parse_args()

    init_db()

    new_materials, new_keywords = index_materials()
    # asyncio.run은 동기 코드에서 비동기 함수를 실행하는 진입점이다
    generated = asyncio.run(generate_quizzes(args.quiz))
    pending = len(get_pending_quizzes())

    print("\n" + "=" * 40)
    print(f"신규 자료      {new_materials}개")
    print(f"신규 키워드    {new_keywords}개")
    print(f"생성된 질문    {generated}개")
    print(f"발송 대기      {pending}개")
    print("=" * 40)


if __name__ == "__main__":
    main()