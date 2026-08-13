import csv
import time
from datetime import datetime
from pathlib import Path


LOG_PATH = Path("logs/llm_calls.csv")

FIELDS = [
    "timestamp",      # 호출 시각
    "purpose",        # 용도 (keyword_extract / quiz_generate)
    "model",          # 사용한 모델
    "input_tokens",   # 입력 토큰 수
    "output_tokens",  # 출력 토큰 수
    "cache_creation", # 캐시를 새로 만들며 쓴 토큰
    "cache_read",     # 캐시에서 읽은 토큰
    "latency_ms",     # 응답 시간 (밀리초)
    "parse_success",  # JSON 파싱 성공 여부
    "retry_count",    # 재시도 횟수
    "note",           # 비고 (키워드명 등)
]


def log_call(
    purpose: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    parse_success: bool,
    retry_count: int = 0,
    note: str = "",
    cache_creation: int = 0,
    cache_read: int = 0,
) -> None:
    """LLM 호출 결과를 CSV 파일에 한 줄 기록한다."""
    is_new = not LOG_PATH.exists()

    with LOG_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new:
            writer.writeheader()

        writer.writerow({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "purpose": purpose,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation": cache_creation,
            "cache_read": cache_read,
            "latency_ms": latency_ms,
            "parse_success": parse_success,
            "retry_count": retry_count,
            "note": note,
        })

class Timer:
    """with 블록의 실행 시간을 밀리초로 측정한다."""
    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = int((time.perf_counter() - self.start) * 1000)

