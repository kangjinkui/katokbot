"""
Pydantic Models for KaTokBot API
카톡봇 데이터 모델 정의
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from datetime import datetime


# ====================================
# User Models (사용자 관련 모델)
# ====================================

class UserBase(BaseModel):
    """사용자 기본 정보"""
    room_name: str = Field(..., description="카톡방 이름", min_length=1, max_length=100)
    author_name: str = Field(..., description="사용자 이름", min_length=1, max_length=50)
    nickname: Optional[str] = Field(None, description="사용자 별명", max_length=50)
    preferred_character: str = Field(
        default="tsundere_cat",
        description="선호 캐릭터 (tsundere_cat, kind_teacher, etc.)"
    )


class UserCreate(UserBase):
    """사용자 생성 요청"""
    pass


class UserUpdate(BaseModel):
    """사용자 정보 수정 요청"""
    nickname: Optional[str] = Field(None, max_length=50)
    preferred_character: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """사용자 응답"""
    user_id: int
    is_active: bool
    created_at: datetime
    last_active_at: datetime
    total_messages: int

    class Config:
        from_attributes = True  # Pydantic v2 (orm_mode 대체)


# ====================================
# Chat Session Models (세션 관련 모델)
# ====================================

class ChatSessionBase(BaseModel):
    """세션 기본 정보"""
    session_key: str = Field(..., description="세션 키 (room_author)")


class ChatSessionCreate(ChatSessionBase):
    """세션 생성 요청"""
    user_id: int = Field(..., description="사용자 ID", gt=0)


class ChatSessionResponse(ChatSessionBase):
    """세션 응답"""
    session_id: int
    user_id: int
    started_at: datetime
    last_message_at: datetime
    message_count: int
    is_active: bool

    class Config:
        from_attributes = True


# ====================================
# Message Models (메시지 관련 모델)
# ====================================

class MessageType(str):
    """메시지 타입 상수"""
    USER = "user"
    AI = "ai"
    SYSTEM = "system"


class MessageBase(BaseModel):
    """메시지 기본 정보"""
    message_type: Literal["user", "ai", "system"] = Field(
        ...,
        description="메시지 타입 (user/ai/system)"
    )
    content: str = Field(..., description="메시지 내용", min_length=1, max_length=5000)
    tokens_used: int = Field(default=0, description="사용된 토큰 수", ge=0)


class MessageCreate(MessageBase):
    """메시지 생성 요청"""
    session_id: int = Field(..., description="세션 ID", gt=0)


class MessageResponse(MessageBase):
    """메시지 응답"""
    message_id: int
    session_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ====================================
# Chat Request/Response Models
# ====================================

class ChatRequest(BaseModel):
    """채팅 요청 (메신저봇에서 호출)"""
    room_name: str = Field(..., description="카톡방 이름")
    author_name: str = Field(..., description="사용자 이름")
    content: str = Field(..., description="사용자 메시지", min_length=1)
    preferred_character: Optional[str] = Field(
        default="tsundere_cat",
        description="선호 캐릭터"
    )

    @validator('content')
    def validate_content(cls, v):
        """메시지 내용 검증"""
        v = v.strip()
        if not v:
            raise ValueError("메시지 내용이 비어있습니다")
        return v


class ChatResponse(BaseModel):
    """채팅 응답"""
    success: bool = Field(..., description="성공 여부")
    response: str = Field(..., description="AI 응답 메시지")
    session_id: int = Field(..., description="세션 ID")
    message_count: int = Field(..., description="현재 세션의 메시지 수")
    tokens_used: int = Field(default=0, description="이번 응답에 사용된 토큰")


class ChatHistoryRequest(BaseModel):
    """대화 기록 조회 요청"""
    room_name: str = Field(..., description="카톡방 이름")
    author_name: str = Field(..., description="사용자 이름")
    limit: int = Field(default=20, description="가져올 메시지 수", ge=1, le=100)


class ChatHistoryResponse(BaseModel):
    """대화 기록 응답"""
    session_id: int
    messages: List[MessageResponse]
    total_count: int


# ====================================
# Statistics Models (통계 관련 모델)
# ====================================

class UserStatistics(BaseModel):
    """사용자 통계"""
    user_id: int
    author_name: str
    room_name: str
    total_messages: int
    total_tokens_used: int
    first_message_at: Optional[datetime]
    last_message_at: Optional[datetime]


class DailyStatistics(BaseModel):
    """일별 통계"""
    date: str
    total_messages: int
    total_tokens_used: int
    active_users: int
    active_sessions: int


# ====================================
# Error Response Model
# ====================================

class ErrorResponse(BaseModel):
    """에러 응답"""
    success: bool = False
    error: str = Field(..., description="에러 메시지")
    detail: Optional[str] = Field(None, description="상세 에러 내용")


# ====================================
# Health Check Model
# ====================================

class HealthResponse(BaseModel):
    """헬스체크 응답"""
    status: str = Field(default="healthy", description="서버 상태")
    timestamp: datetime = Field(default_factory=datetime.now)
    database_connected: bool = Field(..., description="DB 연결 상태")
    version: str = Field(default="1.0.0", description="API 버전")
