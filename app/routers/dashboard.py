"""
Dashboard Router - 대시보드 API 엔드포인트
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from typing import List, Dict, Any
import logging

from app.database import db

logger = logging.getLogger(__name__)

dashboard_router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


# ====================================
# Level 1: 방 목록
# ====================================

@dashboard_router.get(
    "/rooms",
    summary="방 목록 조회",
    description="모든 카톡방 목록과 통계"
)
async def get_rooms():
    """
    방 목록 조회

    Returns:
        - room_name: 방 이름
        - user_count: 사용자 수
        - total_messages: 총 메시지 수
        - last_active: 마지막 활동 시간
        - created_at: 생성 시간
    """
    try:
        query = """
        SELECT
            u.room_name,
            COUNT(DISTINCT u.user_id) as user_count,
            SUM(u.total_messages) as total_messages,
            MAX(u.last_active_at) as last_active,
            MIN(u.created_at) as created_at
        FROM users u
        WHERE u.is_active = 1
        GROUP BY u.room_name
        ORDER BY last_active DESC
        """

        rooms = db.execute_query(query)

        return {
            "success": True,
            "rooms": rooms,
            "total_count": len(rooms)
        }

    except Exception as e:
        logger.error(f"방 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ====================================
# Level 2: 사용자 목록 (특정 방)
# ====================================

@dashboard_router.get(
    "/rooms/{room_name}/users",
    summary="방별 사용자 목록",
    description="특정 방의 모든 사용자"
)
async def get_users_in_room(room_name: str):
    """
    특정 방의 사용자 목록

    Args:
        room_name: 카톡방 이름

    Returns:
        사용자 목록 및 통계
    """
    try:
        query = """
        SELECT
            user_id,
            room_name,
            author_name,
            nickname,
            preferred_character,
            is_active,
            created_at,
            last_active_at,
            total_messages
        FROM users
        WHERE room_name = ?
        ORDER BY last_active_at DESC
        """

        users = db.execute_query(query, (room_name,))

        if not users:
            return {
                "success": True,
                "users": [],
                "total_count": 0,
                "message": f"방 '{room_name}'에 사용자가 없습니다"
            }

        return {
            "success": True,
            "room_name": room_name,
            "users": users,
            "total_count": len(users)
        }

    except Exception as e:
        logger.error(f"사용자 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ====================================
# Level 3: 대화 내역 (특정 사용자)
# ====================================

@dashboard_router.get(
    "/users/{user_id}/messages",
    summary="사용자 대화 내역",
    description="특정 사용자의 모든 메시지"
)
async def get_user_messages(user_id: int, limit: int = 50):
    """
    사용자 대화 내역 조회

    Args:
        user_id: 사용자 ID
        limit: 가져올 메시지 수
    """
    try:
        # 사용자 확인
        user_query = "SELECT * FROM users WHERE user_id = ?"
        user = db.execute_query(user_query, (user_id,))

        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

        # 메시지 조회
        messages_query = """
        SELECT
            cm.message_id,
            cm.session_id,
            cm.message_type,
            cm.content,
            cm.created_at,
            cm.tokens_used
        FROM chat_messages cm
        JOIN chat_sessions cs ON cm.session_id = cs.session_id
        WHERE cs.user_id = ?
        ORDER BY cm.created_at DESC
        LIMIT ?
        """

        messages = db.execute_query(messages_query, (user_id, limit))
        messages.reverse()  # 오래된 것부터 표시

        return {
            "success": True,
            "user": user[0],
            "messages": messages,
            "total_count": len(messages)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"대화 내역 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ====================================
# 전체 통계
# ====================================

@dashboard_router.get(
    "/stats/overview",
    summary="전체 통계",
    description="대시보드 전체 통계"
)
async def get_overview_stats():
    """전체 통계 조회"""
    try:
        # 방 개수
        rooms_query = """
        SELECT COUNT(DISTINCT room_name) as total_rooms
        FROM users
        WHERE is_active = 1
        """
        rooms_result = db.execute_query(rooms_query)

        # 활성 사용자 수
        users_query = """
        SELECT COUNT(*) as total_users
        FROM users
        WHERE is_active = 1
        """
        users_result = db.execute_query(users_query)

        # 총 메시지 수
        messages_query = """
        SELECT COUNT(*) as total_messages
        FROM chat_messages
        """
        messages_result = db.execute_query(messages_query)

        # 총 토큰 사용량
        tokens_query = """
        SELECT SUM(tokens_used) as total_tokens
        FROM chat_messages
        WHERE message_type = 'ai'
        """
        tokens_result = db.execute_query(tokens_query)

        return {
            "success": True,
            "stats": {
                "total_rooms": rooms_result[0]["total_rooms"] if rooms_result else 0,
                "total_users": users_result[0]["total_users"] if users_result else 0,
                "total_messages": messages_result[0]["total_messages"] if messages_result else 0,
                "total_tokens": tokens_result[0]["total_tokens"] or 0 if tokens_result else 0,
            }
        }

    except Exception as e:
        logger.error(f"전체 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ====================================
# 검색 기능
# ====================================

@dashboard_router.get(
    "/search",
    summary="통합 검색",
    description="방, 사용자, 메시지 통합 검색"
)
async def search(q: str, search_type: str = "all"):
    """
    통합 검색

    Args:
        q: 검색어
        search_type: 검색 타입 (all, rooms, users, messages)
    """
    try:
        results = {}

        if search_type in ["all", "rooms"]:
            # 방 검색
            rooms_query = """
            SELECT DISTINCT room_name
            FROM users
            WHERE room_name LIKE ?
            AND is_active = 1
            """
            rooms = db.execute_query(rooms_query, (f"%{q}%",))
            results["rooms"] = rooms

        if search_type in ["all", "users"]:
            # 사용자 검색
            users_query = """
            SELECT user_id, room_name, author_name, nickname
            FROM users
            WHERE (author_name LIKE ? OR nickname LIKE ?)
            AND is_active = 1
            LIMIT 20
            """
            users = db.execute_query(users_query, (f"%{q}%", f"%{q}%"))
            results["users"] = users

        if search_type in ["all", "messages"]:
            # 메시지 검색
            messages_query = """
            SELECT
                cm.message_id,
                cm.content,
                cm.created_at,
                u.room_name,
                u.author_name
            FROM chat_messages cm
            JOIN chat_sessions cs ON cm.session_id = cs.session_id
            JOIN users u ON cs.user_id = u.user_id
            WHERE cm.content LIKE ?
            ORDER BY cm.created_at DESC
            LIMIT 20
            """
            messages = db.execute_query(messages_query, (f"%{q}%",))
            results["messages"] = messages

        return {
            "success": True,
            "query": q,
            "results": results
        }

    except Exception as e:
        logger.error(f"검색 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ====================================
# 활동 타임라인
# ====================================

@dashboard_router.get(
    "/timeline",
    summary="활동 타임라인",
    description="최근 활동 목록"
)
async def get_timeline(limit: int = 50):
    """최근 활동 타임라인"""
    try:
        query = """
        SELECT
            cm.message_id,
            cm.message_type,
            cm.content,
            cm.created_at,
            u.room_name,
            u.author_name
        FROM chat_messages cm
        JOIN chat_sessions cs ON cm.session_id = cs.session_id
        JOIN users u ON cs.user_id = u.user_id
        ORDER BY cm.created_at DESC
        LIMIT ?
        """

        timeline = db.execute_query(query, (limit,))

        return {
            "success": True,
            "timeline": timeline,
            "total_count": len(timeline)
        }

    except Exception as e:
        logger.error(f"타임라인 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
