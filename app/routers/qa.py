"""
QA Router - RAG 기반 Q&A 검색
"""
import logging
import os
import shutil
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.database import db
from app.services.embedding import EmbeddingService
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)

load_dotenv()

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, "data", "hanbang_qa.md")
CHROMA_DIR = os.path.join(BASE_DIR, "data", "chroma_db")
MODEL_CACHE_DIR = os.path.join(BASE_DIR, "data", "models")

os.makedirs(CHROMA_DIR, exist_ok=True)
os.makedirs(MODEL_CACHE_DIR, exist_ok=True)


# =========================
# Schema init
# =========================
def init_qa_schema() -> None:
    """Create QA table if missing (metadata only, retrieval uses Chroma)."""
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
        "예산담당": "예산담당",
        "담당": "담당",
        "기술": "기술",
        "도입": "도입/참여",
        "최종": "최종정리",
    }

    ENCODING_FIXES = {
        # UTF-8 깨짐 패턴 보정
        "�??": "",
        "��": "",
    }

    def __init__(self, embedding_service: EmbeddingService, vector_store: VectorStore):
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def clean_text(self, text: str) -> str:
        cleaned = text.replace("**", "").strip()
        for bad, good in self.ENCODING_FIXES.items():
            cleaned = cleaned.replace(bad, good)
        cleaned = cleaned.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
        return cleaned.strip()

    def normalize_section(self, section_line: str) -> str:
        for key, val in self.SECTION_MAP.items():
            if key in section_line:
                return val
        return section_line.strip()

    def parse_markdown(self, path: str) -> List[dict]:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except UnicodeDecodeError:
            logger.warning("[QA Loader] UTF-8 decoding failed, trying cp949")
            try:
                with open(path, "r", encoding="cp949", errors="ignore") as f:
                    content = f.read()
            except Exception:
                with open(path, "r", encoding="latin-1", errors="ignore") as f:
                    content = f.read()

        lines = content.splitlines()
        current_section = None
        items: List[dict] = []

        for line in lines:
            if line.startswith("###"):
                current_section = self.normalize_section(line)
                continue

            if not line.startswith("|") or line.startswith("|:"):
                continue

            cols = [c.strip() for c in line.split("|")[1:-1]]
            if len(cols) < 3:
                continue
            if "질문" in cols[0] and "답변" in cols[1]:
                continue

            question = self.clean_text(cols[0])
            answer = self.clean_text(cols[1])
            source = self.clean_text(cols[2]) if len(cols) > 2 and cols[2] else None
            section = current_section or "기본"

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

        # Build vector store from questions
        self.vector_store.clear()
        questions = [qa["question"] for qa in items]
        embeddings = self.embedding_service.encode(questions)
        ids = [str(i) for i in range(len(items))]
        metadatas = [
            {
                "question": qa["question"],
                "answer": qa["answer"],
                "section": qa["section"],
                "source": qa["source"] or "",
            }
            for qa in items
        ]
        self.vector_store.add_documents(ids, embeddings, metadatas)
        logger.info(f"[QA Loader] Loaded {len(items)} items into vector store")

        return len(items)


# =========================
# Service
# =========================
class QAService:
    SIMILARITY_THRESHOLD = 0.7

    def __init__(self, embedding_service: EmbeddingService, vector_store: VectorStore):
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def search(self, query: str, top_k: int) -> List[dict]:
        logger.info(f"[QA Search] Query: '{query}', Top K: {top_k}")

        query_embedding = self.embedding_service.encode_single(query)
        results = self.vector_store.search(query_embedding, top_k=top_k * 2)

        metadatas = results.get("metadatas", [[]])
        distances = results.get("distances", [[]])
        if not metadatas or not metadatas[0]:
            logger.warning("[QA Search] No vector search results returned")
            return []

        rows = []
        for i, metadata in enumerate(metadatas[0]):
            distance = distances[0][i] if distances and distances[0] else None
            similarity = 1 - distance if distance is not None else 0
            rows.append(
                {
                    "question": metadata.get("question"),
                    "answer": metadata.get("answer"),
                    "section": metadata.get("section"),
                    "source": metadata.get("source", ""),
                    "similarity": similarity,
                }
            )

        filtered_rows = [r for r in rows if r["similarity"] >= self.SIMILARITY_THRESHOLD]
        filtered_rows = filtered_rows[:top_k]

        if filtered_rows:
            logger.info(
                f"[QA Search] Top result similarity: {filtered_rows[0]['similarity']:.3f}, "
                f"question: {filtered_rows[0]['question'][:50]}..."
            )
        else:
            logger.warning(
                f"[QA Search] No results above threshold {self.SIMILARITY_THRESHOLD} for query: '{query}'"
            )

        return filtered_rows


# =========================
# Router
# =========================
embedding_service = EmbeddingService(cache_dir=MODEL_CACHE_DIR)
vector_store = VectorStore(persist_directory=CHROMA_DIR)
qa_service = QAService(embedding_service, vector_store)
qa_loader = QALoader(embedding_service, vector_store)
qa_router = APIRouter(prefix="/api/qa", tags=["QA"])
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

    backup_dir = os.path.join(BASE_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(
        backup_dir, f"katokbot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    )
    shutil.copy2(db.db_path, backup_path)

    count = qa_loader.load_to_db(DATA_PATH)
    return {"success": True, "loaded": count, "backup": backup_path}
