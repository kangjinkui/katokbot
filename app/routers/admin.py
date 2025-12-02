"""
Admin Router - 관리 엔드포인트
"""
from fastapi import APIRouter, HTTPException, status
import logging

from app.database import db, session_repo, message_repo

logger = logging.getLogger(__name__)

admin_router = APIRouter(prefix="/api/admin", tags=["Admin"])


@admin_router.post(
    "/cleanup/sessions",
    summary="세션 정리",
    description="비활성 세션 정리 (30분 이상)"
)
async def cleanup_sessions(timeout_minutes: int = 30):
    """오래된 세션 정리"""
    try:
        count = session_repo.cleanup_old_sessions(timeout_minutes)

        return {
            "success": True,
            "cleaned_sessions": count,
            "message": f"{count}개의 세션이 정리되었습니다."
        }

    except Exception as e:
        logger.error(f"Session cleanup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"세션 정리 중 오류가 발생했습니다: {str(e)}"
        )


@admin_router.post(
    "/cleanup/messages",
    summary="메시지 정리",
    description="오래된 메시지 삭제"
)
async def cleanup_messages(days: int = 30):
    """오래된 메시지 삭제"""
    try:
        count = message_repo.delete_old_messages(days)

        return {
            "success": True,
            "deleted_messages": count,
            "message": f"{count}개의 메시지가 삭제되었습니다."
        }

    except Exception as e:
        logger.error(f"Message cleanup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"메시지 정리 중 오류가 발생했습니다: {str(e)}"
        )


@admin_router.post(
    "/db/vacuum",
    summary="데이터베이스 최적화",
    description="SQLite VACUUM 실행"
)
async def vacuum_database():
    """데이터베이스 최적화"""
    try:
        with db.get_connection() as conn:
            conn.execute("VACUUM")
            conn.execute("ANALYZE")

        return {
            "success": True,
            "message": "데이터베이스가 최적화되었습니다."
        }

    except Exception as e:
        logger.error(f"Database vacuum error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 최적화 중 오류가 발생했습니다: {str(e)}"
        )
