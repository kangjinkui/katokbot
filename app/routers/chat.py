"""
Chat Router - 채팅 관련 엔드포인트
"""
from fastapi import APIRouter, HTTPException, status
import logging

from app.models import (
    ChatRequest,
    ChatResponse,
    ChatHistoryRequest,
    ChatHistoryResponse,
    MessageResponse,
)
from app.database import (
    db,
    user_repo,
    session_repo,
    message_repo,
)

logger = logging.getLogger(__name__)

chat_router = APIRouter(prefix="/api/chat", tags=["Chat"])


@chat_router.post(
    "/message",
    response_model=ChatResponse,
    summary="채팅 메시지 전송",
    description="메신저봇에서 사용자 메시지를 받아 AI 응답 생성"
)
async def send_message(request: ChatRequest):
    """
    채팅 메시지 처리

    - 사용자 정보 생성/조회
    - 세션 생성/조회
    - 대화 기록 저장
    - AI 응답 생성 (별도 함수 필요)
    """
    try:
        # 1. 사용자 생성 또는 조회
        user_id = user_repo.create_or_get_user(
            room_name=request.room_name,
            author_name=request.author_name,
            preferred_character=request.preferred_character
        )

        # 2. 세션 생성 또는 조회
        session_key = f"{request.room_name}_{request.author_name}"
        session_id = session_repo.create_or_get_session(user_id, session_key)

        # 3. 사용자 메시지 저장
        message_repo.create_message(
            session_id=session_id,
            message_type="user",
            content=request.content,
            tokens_used=0
        )

        # 4. AI 응답 생성 (TODO: 실제 AI API 연동)
        # 여기서는 임시 응답
        ai_response = f"'{request.content}'에 대한 AI 응답입니다."
        tokens_used = 0

        # 5. AI 응답 저장
        message_repo.create_message(
            session_id=session_id,
            message_type="ai",
            content=ai_response,
            tokens_used=tokens_used
        )

        # 6. 카운트 업데이트
        session_repo.increment_message_count(session_id)
        user_repo.increment_message_count(user_id)

        # 7. 세션 정보 조회
        session = session_repo.get_session(session_id)

        return ChatResponse(
            success=True,
            response=ai_response,
            session_id=session_id,
            message_count=session["message_count"],
            tokens_used=tokens_used
        )

    except Exception as e:
        logger.error(f"Chat message error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"메시지 처리 중 오류가 발생했습니다: {str(e)}"
        )


@chat_router.post(
    "/history",
    response_model=ChatHistoryResponse,
    summary="대화 기록 조회",
    description="특정 사용자의 대화 기록 조회"
)
async def get_chat_history(request: ChatHistoryRequest):
    """
    대화 기록 조회

    - 세션 조회
    - 최근 N개 메시지 반환
    """
    try:
        # 세션 키 생성
        session_key = f"{request.room_name}_{request.author_name}"

        # 세션 조회
        query = "SELECT session_id FROM chat_sessions WHERE session_key = ?"
        result = db.execute_query(query, (session_key,))

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="대화 기록을 찾을 수 없습니다."
            )

        session_id = result[0]["session_id"]

        # 메시지 조회
        messages = message_repo.get_session_messages(session_id, request.limit)

        # Pydantic 모델로 변환
        message_responses = [
            MessageResponse(**msg) for msg in messages
        ]

        return ChatHistoryResponse(
            session_id=session_id,
            messages=message_responses,
            total_count=len(message_responses)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat history error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"대화 기록 조회 중 오류가 발생했습니다: {str(e)}"
        )


@chat_router.delete(
    "/session/{room_name}/{author_name}",
    summary="세션 초기화",
    description="대화 세션 비활성화 (새 대화 시작)"
)
async def clear_session(room_name: str, author_name: str):
    """
    세션 초기화

    - 세션 비활성화
    - 새로운 대화 시작 가능
    """
    try:
        session_key = f"{room_name}_{author_name}"
        session_repo.clear_session(session_key)

        return {
            "success": True,
            "message": "세션이 초기화되었습니다."
        }

    except Exception as e:
        logger.error(f"Session clear error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"세션 초기화 중 오류가 발생했습니다: {str(e)}"
        )
