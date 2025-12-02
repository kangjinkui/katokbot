"""
QA Router - Q&A 검색 엔드포인트 (SQLite FTS5)
"""
import os
import re
import shutil
import sqlite3
import logging
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.database import db

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, "data", "hanbang_qa.md")


# =========================
# Schema init
# =========================
def init_qa_schema():
    """Create QA tables/triggers if missing."""
    with db.get_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS qa_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                source TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS qa_fts USING fts5(
                question,
                answer,
                section,
                content='qa_documents',
                content_rowid='id',
                tokenize='unicode61'
            )
            """
        )

        triggers = [
            """
            CREATE TRIGGER IF NOT EXISTS qa_fts_sync_insert
            AFTER INSERT ON qa_documents BEGIN
                INSERT INTO qa_fts(rowid, question, answer, section)
                VALUES (new.id, new.question, new.answer, new.section);
            END;
            """,
            """
            CREATE TRIGGER IF NOT EXISTS qa_fts_sync_delete
            AFTER DELETE ON qa_documents BEGIN
                DELETE FROM qa_fts WHERE rowid = old.id;
            END;
            """,
        ]

        for sql in triggers:
            try:
                cur.execute(sql)
            except sqlite3.OperationalError as e:
                if "already exists" not in str(e):
                    raise

        conn.commit()


# =========================
# Models
# =========================
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    top_k: int = Field(default=3, ge=1, le=10)


class SearchResponse(BaseModel):
    success: bool
    query: str
    results: List[dict]
    total: int


# =========================
# Loader
# =========================
class QALoader:
    SECTION_MAP = {
        "직원": "직원",
        "정산담당": "정산담당",
        "식당": "식당",
        "기술": "기술",
        "도입": "도입/참여",
        "최종": "최종정리",
    }

    ENCODING_FIXES = {
        # UTF-8 깨짐 패턴들
        "?�": "",  # 깨진 문자 제거
        "��": "",  # 깨진 문자 제거
    }

    def __init__(self):
        pass

    def clean_text(self, text: str) -> str:
        # 볼드 마크다운 제거
        cleaned = text.replace("**", "").strip()

        # 인코딩 깨짐 수정
        for bad, good in self.ENCODING_FIXES.items():
            cleaned = cleaned.replace(bad, good)

        # 추가 정제: 유효하지 않은 유니코드 제거
        cleaned = cleaned.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')

        return cleaned.strip()

    def normalize_section(self, section_line: str) -> str:
        for key, val in self.SECTION_MAP.items():
            if key in section_line:
                return val
        return section_line.strip()

    def parse_markdown(self, path: str) -> List[dict]:
        # UTF-8로 파일 읽기, 에러 무시
        try:
            with open(path, "r", encoding="utf-8", errors='ignore') as f:
                content = f.read()
        except UnicodeDecodeError:
            # UTF-8 실패 시 다른 인코딩 시도
            logger.warning(f"[QA Loader] UTF-8 decoding failed, trying cp949")
            try:
                with open(path, "r", encoding="cp949", errors='ignore') as f:
                    content = f.read()
            except:
                with open(path, "r", encoding="latin-1", errors='ignore') as f:
                    content = f.read()

        lines = content.splitlines()
        current_section = None
        items: List[dict] = []

        for line in lines:
            if line.startswith("###"):
                current_section = self.normalize_section(line)
                continue

            if not line.startswith("|"):
                continue
            if line.startswith("|:"):
                continue

            cols = [c.strip() for c in line.split("|")[1:-1]]
            if len(cols) < 3:
                continue
            if "질문" in cols[0] and "답변" in cols[1]:
                continue

            question = self.clean_text(cols[0])
            answer = self.clean_text(cols[1])
            source = self.clean_text(cols[2]) if len(cols) > 2 and cols[2] else None
            section = current_section or "기타"

            # 빈 질문이나 답변 스킵
            if not question or not answer:
                continue

            items.append(
                {
                    "section": section,
                    "question": question,
                    "answer": answer,
                    "source": source,
                }
            )

        return items

    def load_to_db(self, path: str) -> int:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Q&A markdown not found: {path}")

        logger.info(f"[QA Loader] Loading Q&A from: {path}")
        items = self.parse_markdown(path)
        logger.info(f"[QA Loader] Parsed {len(items)} Q&A items")

        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM qa_documents")
            cur.execute("DELETE FROM qa_fts")
            logger.info("[QA Loader] Cleared existing data")

            for qa in items:
                cur.execute(
                    """
                    INSERT INTO qa_documents (section, question, answer, source)
                    VALUES (?, ?, ?, ?)
                    """,
                    (qa["section"], qa["question"], qa["answer"], qa["source"]),
                )
            conn.commit()
            logger.info(f"[QA Loader] Loaded {len(items)} items into database")

        return len(items)


# =========================
# Service
# =========================



class QAService:
    # ?? ??? ?? (RAG ??? ?? ?? ??)
    SYNONYMS = {
        "정산": ["정산", "계산", "집계", "처리"],
        "업무": ["업무", "작업", "일", "처리"],
        "시간": ["시간", "소요", "기간"],
        "절약": ["절약", "단축", "감소"],
        "식권": ["식권", "쿠폰", "한방쿠폰"],
        "qr": ["qr", "qr코드", "큐알", "큐알c크론"],
        "발급": ["발급", "출력", "배포", "재발급"],
        "보고": ["보고", "보고서", "리포트", "정산보고"],
        "결재": ["결재", "결제"],
        "분실": ["분실", "유실", "잃어버림"],
        "말일": ["말일", "월말", "마감"],
    }

    def normalize(self, text: str) -> str:
        """??? ?? + ??/??? ??."""
        lowered = text.lower()
        cleaned = re.sub(r"[^\w\s\uac00-\ud7a3]", " ", lowered)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def sanitize_fts_query(self, query: str) -> str:
        """
        FTS5 ???? ?? ? ?? ??
        FTS5? ?? ????? ???? ????? ?? ??
        """
        sanitized = re.sub(r"[^\w\s\uac00-\ud7a3]", " ", query)
        sanitized = re.sub(r"\s+", " ", sanitized).strip()
        logger.debug(f"[QA Search] Sanitized query: '{query}' -> '{sanitized}'")
        return sanitized

    def expand_with_synonyms(self, query: str) -> str:
        """
        FTS5 ??? ???? ?? (OR ??).
        ?: '?? ??' -> '(?? OR ?? OR ?? OR ??) (?? OR ?? OR ? OR ??)'
        """
        tokens = self.normalize(query).split()
        expanded_tokens = []
        for token in tokens:
            syns = None
            for key, values in self.SYNONYMS.items():
                if token == key or token in values:
                    syns = values
                    break
            if syns:
                expanded_tokens.append("(" + " OR ".join(syns) + ")")
            else:
                expanded_tokens.append(token)
        return " ".join(expanded_tokens)

    def similarity(self, query: str, candidate: str) -> float:
        """?? ??? ?? ??? ?? ??? ??."""
        q_tokens = set(self.normalize(query).split())
        c_tokens = set(self.normalize(candidate).split())
        if not q_tokens or not c_tokens:
            return 0.0
        overlap = len(q_tokens & c_tokens) / len(q_tokens | c_tokens)
        coverage = len(q_tokens & c_tokens) / len(q_tokens)
        return 0.6 * overlap + 0.4 * coverage

    def search(self, query: str, top_k: int) -> List[dict]:
        logger.info(f"[QA Search] Query: '{query}', Top K: {top_k}")

        sanitized_query = self.sanitize_fts_query(query)

        if not sanitized_query:
            logger.warning("[QA Search] Query is empty after sanitization")
            return []

        sql = """
        SELECT
            d.id,
            d.section,
            d.question,
            d.answer,
            d.source,
            fts.rank AS score
        FROM qa_fts fts
        JOIN qa_documents d ON fts.rowid = d.id
        WHERE qa_fts MATCH ?
        ORDER BY fts.rank
        LIMIT ?
        """

        expanded_query = self.expand_with_synonyms(sanitized_query)
        limit = top_k * 3  # ??? ??? ??? ???

        logger.debug(f"[QA Search] Executing SQL with params: query={expanded_query}, limit={limit}")
        rows = db.execute_query(sql, (expanded_query, limit))

        logger.info(f"[QA Search] Found {len(rows)} results")

        for r in rows:
            if "score" in r and r["score"] is not None:
                r["score"] = abs(r["score"])

        # ???: ?? ???? ?? ?? ??
        for r in rows:
            r["similarity"] = self.similarity(query, r["question"])

        rows.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        rows = rows[:top_k]

        if rows:
            logger.debug(f"[QA Search] Top result: {rows[0]['question'][:50]}...")
        else:
            logger.warning(f"[QA Search] No results found for query: '{query}'")

        return rows

# =========================
# Router
# =========================
qa_router = APIRouter(prefix="/api/qa", tags=["QA"])
qa_service = QAService()
qa_loader = QALoader()
init_qa_schema()


@qa_router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    logger.info(f"[QA API] Received search request: query='{request.query}', top_k={request.top_k}")

    results = qa_service.search(request.query, request.top_k)

    logger.info(f"[QA API] Returning {len(results)} results")

    return {
        "success": True,
        "query": request.query,
        "results": results,
        "total": len(results),
    }


@qa_router.post("/reload")
async def reload(x_api_key: Optional[str] = Header(None)):
    if ADMIN_API_KEY and x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

    if not os.path.exists(DATA_PATH):
        raise HTTPException(status_code=404, detail=f"Markdown not found: {DATA_PATH}")

    # Backup before reload
    backup_dir = os.path.join(BASE_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(
        backup_dir, f"katokbot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    )
    shutil.copy2(db.db_path, backup_path)

    count = qa_loader.load_to_db(DATA_PATH)
    return {"success": True, "loaded": count, "backup": backup_path}
