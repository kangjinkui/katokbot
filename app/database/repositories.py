"""
Repository Pattern - 데이터 접근 계층
"""
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class UserRepository:
    """사용자 데이터 접근 계층"""

    def __init__(self, db):
        self.db = db

    def create_or_get_user(
        self,
        room_name: str,
        author_name: str,
        nickname: Optional[str] = None,
        preferred_character: str = "tsundere_cat"
    ) -> int:
        """사용자 생성 또는 조회 (upsert)"""
        # 기존 사용자 확인
        query = "SELECT user_id FROM users WHERE room_name = ? AND author_name = ?"
        result = self.db.execute_query(query, (room_name, author_name))

        if result:
            # 마지막 활동 시간 업데이트
            user_id = result[0]['user_id']
            update_query = """
            UPDATE users
            SET last_active_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """
            self.db.execute_update(update_query, (user_id,))
            return user_id
        else:
            # 새 사용자 생성
            insert_query = """
            INSERT INTO users (room_name, author_name, nickname, preferred_character)
            VALUES (?, ?, ?, ?)
            """
            return self.db.execute_update(
                insert_query,
                (room_name, author_name, nickname, preferred_character)
            )

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """사용자 조회"""
        query = "SELECT * FROM users WHERE user_id = ?"
        result = self.db.execute_query(query, (user_id,))
        return result[0] if result else None

    def update_user(self, user_id: int, **kwargs) -> bool:
        """사용자 정보 수정"""
        fields = []
        values = []

        for key, value in kwargs.items():
            if value is not None:
                fields.append(f"{key} = ?")
                values.append(value)

        if not fields:
            return False

        values.append(user_id)
        query = f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?"
        self.db.execute_update(query, tuple(values))
        return True

    def increment_message_count(self, user_id: int):
        """메시지 카운트 증가"""
        query = """
        UPDATE users
        SET total_messages = total_messages + 1,
            last_active_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
        """
        self.db.execute_update(query, (user_id,))


class SessionRepository:
    """세션 데이터 접근 계층"""

    def __init__(self, db):
        self.db = db

    def create_or_get_session(self, user_id: int, session_key: str) -> int:
        """세션 생성 또는 조회"""
        # 기존 활성 세션 확인
        query = """
        SELECT session_id FROM chat_sessions
        WHERE session_key = ? AND is_active = 1
        """
        result = self.db.execute_query(query, (session_key,))

        if result:
            session_id = result[0]['session_id']
            # 마지막 메시지 시간 업데이트
            update_query = """
            UPDATE chat_sessions
            SET last_message_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
            """
            self.db.execute_update(update_query, (session_id,))
            return session_id
        else:
            # 새 세션 생성
            insert_query = """
            INSERT INTO chat_sessions (user_id, session_key)
            VALUES (?, ?)
            """
            return self.db.execute_update(insert_query, (user_id, session_key))

    def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """세션 조회"""
        query = "SELECT * FROM chat_sessions WHERE session_id = ?"
        result = self.db.execute_query(query, (session_id,))
        return result[0] if result else None

    def increment_message_count(self, session_id: int):
        """세션 메시지 카운트 증가"""
        query = """
        UPDATE chat_sessions
        SET message_count = message_count + 1,
            last_message_at = CURRENT_TIMESTAMP
        WHERE session_id = ?
        """
        self.db.execute_update(query, (session_id,))

    def clear_session(self, session_key: str):
        """세션 비활성화"""
        query = """
        UPDATE chat_sessions
        SET is_active = 0
        WHERE session_key = ?
        """
        self.db.execute_update(query, (session_key,))

    def cleanup_old_sessions(self, timeout_minutes: int = 30) -> int:
        """오래된 세션 정리"""
        query = """
        UPDATE chat_sessions
        SET is_active = 0
        WHERE datetime(last_message_at, '+' || ? || ' minutes') < datetime('now')
        AND is_active = 1
        """
        return self.db.execute_update(query, (timeout_minutes,))


class MessageRepository:
    """메시지 데이터 접근 계층"""

    def __init__(self, db):
        self.db = db

    def create_message(
        self,
        session_id: int,
        message_type: str,
        content: str,
        tokens_used: int = 0
    ) -> int:
        """메시지 생성"""
        query = """
        INSERT INTO chat_messages (session_id, message_type, content, tokens_used)
        VALUES (?, ?, ?, ?)
        """
        return self.db.execute_update(
            query,
            (session_id, message_type, content, tokens_used)
        )

    def get_session_messages(
        self,
        session_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """세션의 최근 메시지 조회"""
        query = """
        SELECT * FROM chat_messages
        WHERE session_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """
        messages = self.db.execute_query(query, (session_id, limit))
        return list(reversed(messages))  # 오래된 것부터 정렬

    def delete_old_messages(self, days: int = 30) -> int:
        """오래된 메시지 삭제"""
        query = """
        DELETE FROM chat_messages
        WHERE datetime(created_at, '+' || ? || ' days') < datetime('now')
        """
        return self.db.execute_update(query, (days,))
