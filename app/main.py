"""
FastAPI Main Application for KaTokBot
카톡봇 백엔드 서버 메인 애플리케이션
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime
import logging
import os

from app.routers import (
    chat_router,
    user_router,
    stats_router,
    admin_router,
    qa_router,
    dashboard_router,
)
from app.models import HealthResponse
from app.database import db

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="KaTokBot API",
    description="메신저봇 백엔드 API - 멀티턴 대화 및 사용자 관리",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 미들웨어 추가 (메신저봇에서 접근 가능하도록)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 마운트
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 라우터 등록
app.include_router(chat_router)
app.include_router(user_router)
app.include_router(stats_router)
app.include_router(admin_router)
app.include_router(dashboard_router)
app.include_router(qa_router)


# ====================================
# Root & Health Check Endpoints
# ====================================

@app.get("/", response_class=HTMLResponse, summary="대시보드")
async def root():
    """대시보드 HTML 반환"""
    TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    html_path = os.path.join(TEMPLATES_DIR, "index.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return {
            "message": "KaTokBot API Server",
            "version": "1.0.0",
            "docs": "/docs",
            "dashboard": "/dashboard (not found)",
            "timestamp": datetime.now().isoformat()
        }


@app.get("/api", summary="API 정보")
async def api_info():
    """API 정보"""
    return {
        "message": "KaTokBot API Server",
        "version": "1.0.0",
        "docs": "/docs",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", response_model=HealthResponse, summary="헬스체크")
async def health_check():
    """서버 상태 확인"""
    db_healthy = db.check_health()

    return HealthResponse(
        status="healthy" if db_healthy else "unhealthy",
        timestamp=datetime.now(),
        database_connected=db_healthy,
        version="1.0.0"
    )


# ====================================
# Startup & Shutdown Events
# ====================================

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행"""
    logger.info("🚀 KaTokBot API Server Starting...")
    logger.info(f"📊 Database: {db.db_path}")
    logger.info(f"✅ Server Ready")


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 실행"""
    logger.info("🛑 KaTokBot API Server Shutting Down...")


# ====================================
# Error Handlers
# ====================================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """404 에러 핸들러"""
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": "Not Found",
            "detail": f"경로를 찾을 수 없습니다: {request.url.path}"
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """500 에러 핸들러"""
    logger.error(f"Internal Server Error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal Server Error",
            "detail": "서버 내부 오류가 발생했습니다."
        }
    )
