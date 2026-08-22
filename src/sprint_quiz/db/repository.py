import json
import sqlite3

from sprint_quiz.db.schema import get_connection


def save_material(filename: str, content: str, content_hash: str) -> int | None:
    """자료를 저장하고 id를 반환한다. 이미 저장된 자료면 None을 반환한다."""
    with get_connection() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO materials (filename, content, content_hash) VALUES (?, ?, ?)",
                (filename, content, content_hash)
            )
            return cur.lastrowid # 방금 저장된 행의 id
        except sqlite3.IntegrityError:
            # content_hash UNIQUE 위반 = 이미 처리한 자료
            return None


def get_material_by_hash(content_hash: str) -> sqlite3.Row | None:
    """해시로 자료를 조회한다."""
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM materials WHERE content_hash = ?", (content_hash,)
        )
        return cur.fetchone()


def save_keywords(material_id: int, keywords: list[dict]) -> int:
    """키워드 목록을 저장하고 실제로 저장된 개수를 반환한다."""
    saved = 0
    with get_connection() as conn:
        for kw in keywords:
            try:
                conn.execute(
                    "INSERT INTO keywords (material_id, keyword, topic) VALUES (?, ?, ?)",
                    (material_id, kw["keyword"], kw.get("topic", "")),
                )
                saved += 1
            except sqlite3.IntegrityError:
                # 이미 있는 키워드는 건너뛰고 나머지는 계속 저장한다
                continue
    return saved

def get_unused_keywords(limit: int = 10) -> list[sqlite3.Row]:
    """아직 출제하지 않은 키워드를 가져온다.
    질문을 만들려면 원본 자료 내용도 필요하므로 materials와 JOIN한다"""

    with get_connection() as conn:
        cur = conn.execute("""
            SELECT k.*, m.content, m.filename
            FROM keywords k
            JOIN materials m ON k.material_id = m.id
            WHERE k.is_used = 0
            ORDER BY k.id
            LIMIT ?
        """, (limit,))
        return cur.fetchall()


def save_quiz(keyword_id: int, quiz: dict) -> int:
    """생성된 질문을 저장하고, 해당 키워드를 출제 완료로 표시한다.
    두 작업을 같은 트랜잭션에서 처리해 하나만 반영되는 상황을 막는다.
    """
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO quizzes (keyword_id, question, answer, keywords_hint, topic, source)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                keyword_id,
                quiz["question"],
                quiz["answer"],
                # 리스트를 JSON 문자열로 변환. ensure_ascii=False라야 한글이 그대로 저장된다
                json.dumps(quiz.get("keywords", []), ensure_ascii=False),
                quiz.get("topic", ""),
                quiz.get("source", ""),
            ),
        )
        # 질문을 만들었으므로 이 키워드는 출제 완료 처리
        conn.execute(
            "UPDATE keywords SET is_used = 1, used_at = datetime('now', 'localtime') WHERE id = ?",
            (keyword_id,),
        )
        return cur.lastrowid

def get_quiz(quiz_id: int) -> sqlite3.Row | None:
    """id로 질문 하나를 가져온다."""
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,))
        return cur.fetchone()


def get_pending_quizzes() -> list[sqlite3.Row]:
    """아직 발송하지 않은 질문 목록을 가져온다."""
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM quizzes WHERE status = 'pending' ORDER BY id"
        )
        return cur.fetchall()


def save_validation(
        quiz_id: int | None,
        quiz: dict,
        result: dict,
        attempt: int = 0
) -> int:
    """검증 결과를 저장한다. 불합격한 경우 quiz_id는 None이다."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO validations
                (quiz_id, keyword, question, answer, passed,
                 groundedness, correctness, simplicity, duplicate, reason, attempt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                quiz_id,
                quiz["keyword"],
                quiz["question"],
                quiz["answer"],
                int(result["passed"]),
                int(result.get("groundedness", True)),
                int(result.get("correctness", True)),
                int(result.get("simplicity", True)),
                int(result.get("duplicate", True)),
                result.get("reason", ""),
                attempt
            )
        )

        return cur.lastrowid


def get_recent_questions(limit: int = 10) -> list[str]:
    """최근 생성된 질문 목록을 가져온다 (중복 판정용)."""
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT question FROM quizzes ORDER BY id DESC LIMIT ?", (limit,)
        )

        return [row["question"] for row in cur.fetchall()]


def add_subscriber(channel: str, address: str) -> int | None:
    """구독자를 등록한다. 이미 있으면 None을 반환한다."""
    with get_connection() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO subscribers (channel, address) VALUES (?, ?)",
                (channel, address),
            )
            return cur.lastrowid
        except sqlite3.IntegrityError:
            # (channel, address) UNIQUE 위반 = 이미 등록된 구독자
            return None

def get_active_subscribers(channel: str) -> list[sqlite3.Row]:
    """활성 구독자 목록을 채널별로 가져온다."""
    with get_connection() as conn:
        cur = conn.execute(
             "SELECT * FROM subscribers WHERE channel = ? AND is_active = 1",
             (channel,)
        )
        return cur.fetchall()

def get_next_pending_quiz() -> sqlite3.Row | None:
    """발송하지 않은 질문 중 가장 오래된 것 하나를 가져온다."""
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM quizzes WHERE status = 'pending' ORDER BY id LIMIT 1"
        )
        return cur.fetchone()

def mark_quiz_sent(quiz_id: int) -> None:
    """질문을 발송 완료로 표시한다."""
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE quizzes
            SET status = 'sent', sent_at = datetime('now', 'localtime')
            WHERE id = ?
            """,
            (quiz_id,),
        )