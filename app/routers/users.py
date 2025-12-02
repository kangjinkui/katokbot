"""
User Router - 사용자 관리 엔드포인트
"""
from fastapi import APIRouter, HTTPException, status
from typing import List
import logging

from app.models import (
    UserResponse,
    UserCreate,
    UserUpdate,
)
from app.database import db, user_repo

logger = logging.getLogger(__name__)

user_router = APIRouter(prefix="/api/users", tags=["Users"])


@user_router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="사용자 생성",
    description="새로운 사용자 생성"
)
async def create_user(user: UserCreate):
    """사용자 생성"""
    try:
        user_id = user_repo.create_or_get_user(
            room_name=user.room_name,
            author_name=user.author_name,
            nickname=user.nickname,
            preferred_character=user.preferred_character
        )

        user_data = user_repo.get_user(user_id)

        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="사용자 생성 후 조회 실패"
            )

        return UserResponse(**user_data)

    except Exception as e:
        logger.error(f"User creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 생성 중 오류가 발생했습니다: {str(e)}"
        )


@user_router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="사용자 조회",
    description="사용자 ID로 정보 조회"
)
async def get_user(user_id: int):
    """사용자 조회"""
    user_data = user_repo.get_user(user_id)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )

    return UserResponse(**user_data)


@user_router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="사용자 정보 수정",
    description="사용자 정보 업데이트"
)
async def update_user(user_id: int, user_update: UserUpdate):
    """사용자 정보 수정"""
    try:
        # 사용자 존재 확인
        existing_user = user_repo.get_user(user_id)
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )

        # 업데이트
        update_data = user_update.model_dump(exclude_unset=True)
        user_repo.update_user(user_id, **update_data)

        # 업데이트된 정보 조회
        updated_user = user_repo.get_user(user_id)

        return UserResponse(**updated_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 정보 수정 중 오류가 발생했습니다: {str(e)}"
        )


@user_router.get(
    "/",
    response_model=List[UserResponse],
    summary="사용자 목록 조회",
    description="모든 활성 사용자 조회"
)
async def list_users(is_active: bool = True, limit: int = 100):
    """사용자 목록 조회"""
    try:
        query = """
        SELECT * FROM users
        WHERE is_active = ?
        ORDER BY last_active_at DESC
        LIMIT ?
        """
        users = db.execute_query(query, (is_active, limit))

        return [UserResponse(**user) for user in users]

    except Exception as e:
        logger.error(f"User list error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )
