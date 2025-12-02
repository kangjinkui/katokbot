"""
서버 실행 스크립트
uvicorn을 사용하여 FastAPI 서버 실행
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=9000,
        reload=True,  # 개발 모드에서 자동 리로드
        log_level="info"
    )
