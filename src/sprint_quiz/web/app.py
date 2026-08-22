"""FastAPI 앱

서비스 소개 페이지와 관리자 승인 페이지를 제공한다.
이후 스케줄러와 디스코드 봇도 이 앱에 함께 올린다.

실행:
    uv run uvicorn sprint_quiz.web.app:app --reload
"""

import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sprint_quiz.db.schema import init_db
from sprint_quiz.db.repository import (
    get_pending_quizzes, 
    get_quiz,
    approve_quiz,
    reject_quiz,
    get_quiz_stats,
    )

app = FastAPI(title="Sprint Quiz")
init_db()

# __file__은 이 파일의 경로다. 이를 기준으로 templates/static 위치를 잡으면
# 어느 디렉토리에서 실행하든 경로가 깨지지 않는다
BASE_DIR = Path(__file__).parent

templates = Jinja2Templates(directory=BASE_DIR / 'templates')

# /static 으로 시작하는 요청은 static 폴더의 파일을 그대로 내보낸다
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """서비스 소개 페이지"""
    # Jinja2 템플릿에 값을 넘길 때 request는 반드시 포함해야 한다
    # (템플릿 안에서 url_for 등을 쓰기 위해 필요)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.get("/admin/review", response_class=HTMLResponse)
async def admin_review(request: Request):
    """관리자 승인 대기열 페이지."""
    quizzes = get_pending_quizzes()
    stats = get_quiz_stats()
    return templates.TemplateResponse(
        request=request,
        name="admin_review.html",
        context={"quizzes": quizzes, "stats": stats}
    )



@app.get("/quiz/{quiz_id}", response_class=HTMLResponse)
async def quiz_review(request: Request, quiz_id: int):
    """질문/답변 리뷰 페이지. 이메일의 "정답 확인하기" 링크가 향하게 될 페이지다."""
    quiz = get_quiz(quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="퀴즈를 찾을 수 없습니다.")

    try:
        hints = json.loads(quiz["keywords_hint"] or "[]")
    except json.JSONDecodeError:
        hints = []

    return templates.TemplateResponse(
        request=request,
        name="quiz_review.html",
        context={"quiz": quiz, "hints": hints},
    )


@app.post("/admin/review/{quiz_id}/approve")
async def approve_quiz_route(quiz_id: int):
    if get_quiz(quiz_id) is None:
        raise HTTPException(status_code=404, detail="퀴즈를 찾을 수 없습니다.")
    approve_quiz(quiz_id)
    return RedirectResponse(url="/admin/review", status_code=303)


@app.post("/admin/review/{quiz_id}/reject")
async def reject_quiz_route(quiz_id: int):
    if get_quiz(quiz_id) is None:
        raise HTTPException(status_code=404, detail="퀴즈를 찾을 수 없습니다.")
    reject_quiz(quiz_id)
    return RedirectResponse(url="/admin/review", status_code=303)