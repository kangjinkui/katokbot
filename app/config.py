"""
Configuration Management
환경 변수 및 설정 관리
"""
import os
from typing import Optional
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class Settings:
    """애플리케이션 설정"""

    # 기본 설정
    APP_NAME: str = "KaTokBot API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # 데이터베이스 설정
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "katokbot.db")

    # API 보안
    ADMIN_API_KEY: Optional[str] = os.getenv("ADMIN_API_KEY")

    # CORS 설정
    ALLOWED_ORIGINS: list = os.getenv(
        "ALLOWED_ORIGINS",
        "*"
    ).split(",")

    # 로깅 레벨
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # 세션 타임아웃 (분)
    SESSION_TIMEOUT_MINUTES: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))

    # 메시지 보관 기간 (일)
    MESSAGE_RETENTION_DAYS: int = int(os.getenv("MESSAGE_RETENTION_DAYS", "90"))

    # Q&A 데이터 경로
    QA_DATA_PATH: Optional[str] = os.getenv("QA_DATA_PATH")

    # API Rate Limiting (향후 확장용)
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "False").lower() == "true"
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))


# 전역 설정 인스턴스
settings = Settings()


def get_settings() -> Settings:
    """설정 인스턴스 반환"""
    return settings
