import sqlite3
from pathlib import Path

# DB 파일은 프로젝트 루트에 생성된다 (.gitignore 처리 필요)
DB_PATH = Path("sprint_quiz.db")

SCHEMA = """
-- 학습 자료 (Notion에서 내보낸 마크다운)
CREATE TABLE IF NOT EXISTS materials (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    filename      TEXT NOT NULL,
    content       TEXT NOT NULL,
    -- 내용 해시. UNIQUE라서 같은 파일을 두 번 넣으면 DB가 거부한다
    content_hash  TEXT NOT NULL UNIQUE,
    created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 자료에서 추출한 복습 대상 개념
CREATE TABLE IF NOT EXISTS keywords (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id  INTEGER NOT NULL,
    keyword      TEXT NOT NULL,
    topic        TEXT,
    -- 출제 여부. SQLite에 boolean이 없어 0/1로 관리
    is_used      INTEGER NOT NULL DEFAULT 0,
    used_at      TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (material_id) REFERENCES materials(id),
    -- 같은 자료에서 같은 키워드가 중복 저장되는 것을 방지
    UNIQUE (material_id, keyword)
);

-- 생성된 질문 (문제은행)
CREATE TABLE IF NOT EXISTS quizzes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword_id     INTEGER NOT NULL,
    question       TEXT NOT NULL,
    answer         TEXT NOT NULL,
    -- 답변에 포함되면 좋을 단어들. 리스트를 JSON 문자열로 저장
    keywords_hint  TEXT,
    topic          TEXT,
    source         TEXT,
    -- pending(생성됨) → validated(검증통과) → sent(발송됨)
    status         TEXT NOT NULL DEFAULT 'pending',
    created_at     TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    sent_at        TEXT,
    FOREIGN KEY (keyword_id) REFERENCES keywords(id)
);

-- 구독자 (Phase 4에서 사용)
CREATE TABLE IF NOT EXISTS subscribers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    channel     TEXT NOT NULL,   -- 'email' 또는 'discord'
    address     TEXT NOT NULL,   -- 이메일 주소 또는 디스코드 채널 ID
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (channel, address)
);

-- 응답 기록 (Phase 6 개인화 대비. 지금은 비워둔다)
CREATE TABLE IF NOT EXISTS responses (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id        INTEGER NOT NULL,
    subscriber_id  INTEGER NOT NULL,
    recalled       INTEGER,   -- 1이면 떠올랐음, 0이면 못 떠올림
    responded_at   TEXT,
    FOREIGN KEY (quiz_id) REFERENCES quizzes(id),
    FOREIGN KEY (subscriber_id) REFERENCES subscribers(id)
);

-- Validator 판정 결과 (Phase 3-B 분류기 학습 데이터가 된다)
CREATE TABLE IF NOT EXISTS validations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id       INTEGER,          -- 통과한 경우에만 채워진다
    keyword       TEXT NOT NULL,
    question      TEXT NOT NULL,
    answer        TEXT NOT NULL,
    -- 판정 결과: 1이면 통과, 0이면 불합격
    passed        INTEGER NOT NULL,
    -- 항목별 판정 (각 0/1)
    groundedness  INTEGER,
    correctness   INTEGER,
    simplicity    INTEGER,
    duplicate     INTEGER,
    -- 불합격 사유 (LLM이 작성)
    reason        TEXT,
    -- 몇 번째 시도였는지 (0부터 시작)
    attempt       INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (quiz_id) REFERENCES quizzes(id)
);
"""


def get_connection() -> sqlite3.Connection:
    """DB 연결을 반환한다."""
    conn = sqlite3.connect(DB_PATH)
    # row["filename"]처럼 컬럼명으로 값에 접근할 수 있게 한다
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """테이블이 없으면 생성한다. 여러 번 실행해도 안전하다."""
    with get_connection() as conn:
        # executescript는 여러 SQL문을 한 번에 실행한다
        conn.executescript(SCHEMA)



