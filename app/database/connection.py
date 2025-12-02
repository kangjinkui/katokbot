"""
Database Connection Manager
SQLite 데이터베이스 연결 관리
"""
import sqlite3
from contextlib import contextmanager
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class Database:
    """SQLite 데이터베이스 관리 클래스"""

    def __init__(self, db_path: str = "katokbot.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """데이터베이스 초기화 및 테이블 생성"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA busy_timeout=5000")

                # users 테이블
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_name TEXT NOT NULL,
                    author_name TEXT NOT NULL,
                    nickname TEXT,
                    preferred_character TEXT DEFAULT 'tsundere_cat',
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_active_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    total_messages INTEGER DEFAULT 0,
                    UNIQUE(room_name, author_name)
                )
                """)

                # chat_sessions 테이블
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_key TEXT NOT NULL UNIQUE,
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_message_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
                """)

                # chat_messages 테이블
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    message_type TEXT NOT NULL CHECK(message_type IN ('user', 'ai', 'system')),
                    content TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    tokens_used INTEGER DEFAULT 0,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
                )
                """)

                # 인덱스 생성
                cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_room_author
                ON users(room_name, author_name)
                """)

                cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user
                ON chat_sessions(user_id)
                """)

                cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session_time
                ON chat_messages(session_id, created_at)
                """)

                conn.commit()
                logger.info(f"Database initialized at {self.db_path}")

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """데이터베이스 연결 컨텍스트 매니저"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """SELECT 쿼리 실행"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """INSERT/UPDATE/DELETE 쿼리 실행"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid if cursor.lastrowid else cursor.rowcount

    def check_health(self) -> bool:
        """데이터베이스 연결 상태 확인"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
