"""
Statistics Router - 통계 관련 엔드포인트
"""
from fastapi import APIRouter, HTTPException, status
import logging

from app.models import UserStatistics
from app.database import db, user_repo

logger = logging.getLogger(__name__)

stats_router = APIRouter(prefix="/api/stats", tags=["Statistics"])


@stats_router.get(
    "/users/{user_id}",
    response_model=UserStatistics,
    summary="사용자 통계",
    description="특정 사용자의 사용 통계"
)
async def get_user_statistics(user_id: int):
    """사용자 통계 조회"""
    try:
        # 사용자 정보
        user = user_repo.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )

        # 토큰 사용량 및 메시지 통계
        query = """
        SELECT
            SUM(CASE WHEN cm.message_type = 'ai' THEN cm.tokens_used ELSE 0 END) as total_tokens,
            MIN(cm.created_at) as first_message,
            MAX(cm.created_at) as last_message
        FROM users u
        JOIN chat_sessions cs ON u.user_id = cs.user_id
        JOIN chat_messages cm ON cs.session_id = cm.session_id
        WHERE u.user_id = ?
        """
        result = db.execute_query(query, (user_id,))

        stats_data = result[0] if result else {}

        return UserStatistics(
            user_id=user_id,
            author_name=user["author_name"],
            room_name=user["room_name"],
            total_messages=user["total_messages"],
            total_tokens_used=stats_data.get("total_tokens", 0) or 0,
            first_message_at=stats_data.get("first_message"),
            last_message_at=stats_data.get("last_message")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User statistics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}"
        )


@stats_router.get(
    "/top-users",
    summary="활발한 사용자 TOP 10",
    description="메시지 수가 많은 상위 사용자"
)
async def get_top_users(limit: int = 10):
    """활발한 사용자 TOP N"""
    try:
        query = """
        SELECT
            u.user_id,
            u.author_name,
            u.room_name,
            u.total_messages,
            u.last_active_at
        FROM users u
        WHERE u.is_active = 1
        ORDER BY u.total_messages DESC
        LIMIT ?
        """
        users = db.execute_query(query, (limit,))

        return users

    except Exception as e:
        logger.error(f"Top users error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TOP 사용자 조회 중 오류가 발생했습니다: {str(e)}"
        )
