"""FastAPI 앱

서비스 소개 페이지와 관리자 승인 페이지를 제공한다.
이후 스케줄러와 디스코드 봇도 이 앱에 함께 올린다.

실행:
    uv run uvicorn sprint_quiz.web.app:app --reload
"""

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Sprint Quiz")

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