# 📋 Q&A 검색 시스템 개선 계획

## 🔴 현재 상황 분석 (2025-12-03 업데이트)

### 문제점
**핵심 이슈:** "식권정산" vs "식당의 정산 방법을 간단하게 설명해주세요"
- 사용자가 짧은 키워드로 질문 → DB의 긴 질문문과 매칭 실패
- FTS5 + 동의어 확장으로 시도했으나 **여전히 해결 안 됨**
- 유사도 임계값(0.15~0.2)로도 필터링되어 결과 없음

### 근본 원인
1. **키워드 기반 검색의 한계**
   - "식권정산" ≠ "식당의 정산 방법을 간단하게 설명해주세요"
   - 공통 단어: "정산" 하나뿐 → 유사도 매우 낮음

2. **동의어 사전의 한계**
   - 무한히 확장 불가능
   - "식권정산" = "식당 정산 방법"의 의미적 동치를 인식 못함

3. **LLM 직접 호출 불가**
   - 환각(hallucination) 위험: DB에 없는 내용 지어냄
   - 신뢰성 보장 불가

### 결론
**RAG(Retrieval Augmented Generation)로 전환 필요**

---

## 🎯 RAG 전환 전략

### RAG가 필요한 이유

| 문제 | FTS5 + 동의어 | RAG |
|------|-------------|-----|
| "식권정산" → "식당 정산 방법" | ❌ 매칭 실패 | ✅ 의미적 유사성 인식 |
| 동의어 관리 | ❌ 수동 추가 필요 | ✅ 자동 처리 |
| DB에 없는 질문 필터링 | ❌ 불완전 | ✅ 임계값으로 확실히 차단 |
| 환각 방지 | - | ✅ 검색 결과만 사용 |

### 아키텍처

```
사용자 질문: "식권정산"
    ↓
1. 임베딩 모델 (ko-sbert-sts)
    ↓ 벡터 변환: [0.12, -0.45, 0.78, ...]
    ↓
2. 벡터 검색 (ChromaDB)
    ↓ 코사인 유사도 계산
    ↓
3. Top-K 결과 반환 (K=3)
   - "식당의 정산 방법을 간단하게 설명해주세요" (유사도: 0.82)
   - "한방 식권 정산은 어떻게 하나요" (유사도: 0.78)
   - ...
    ↓
4. 임계값 필터 (0.65 이상만)
    ↓
5. 결과 반환 / "관련 질문 없음"
```

---

## 🛠️ 기술 스택 선정

### 임베딩 모델
**선택: `jhgan/ko-sbert-sts`** (로컬)

| 항목 | ko-sbert-sts | OpenAI text-embedding-3-small |
|------|-------------|------------------------------|
| 언어 지원 | 한국어 특화 | 다국어 |
| 차원 | 384 | 1536 |
| 크기 | ~150MB | API 호출 |
| 비용 | 무료 | $0.0001/1k tokens |
| 속도 | 50ms (로컬) | 200ms (네트워크) |
| 오프라인 | ✅ | ❌ |

**이유**:
- 45개 문서는 로컬 모델로 충분
- 외부 API 의존성 제거
- 비용 절감

### 벡터 스토어
**선택: ChromaDB** (파일 기반)

| 항목 | ChromaDB | Qdrant | FAISS |
|------|---------|--------|-------|
| 설치 | pip install | Docker | pip install |
| 관리 | 단일 폴더 | 서버 필요 | 코드 관리 |
| 쿼리 | 간편 | 강력 | 저수준 |
| 규모 | ~10k docs | ~1M docs | ~1M docs |

**이유**:
- SQLite처럼 파일 기반 (서버 불필요)
- 현재 45개 → 향후 수백 개 수준에 적합
- 코드 간결

---

## 📂 프로젝트 구조

```
fastapi/
├── app/
│   ├── routers/
│   │   └── qa.py                  # 기존 - RAG 로직으로 교체
│   ├── services/
│   │   ├── embedding.py           # 신규 - 임베딩 모델 래퍼
│   │   └── vector_store.py        # 신규 - ChromaDB 래퍼
│   └── database.py                # 기존 - SQLite (메타데이터용 유지)
├── data/
│   ├── hanbang_qa.md              # 기존 - 원본 데이터
│   ├── chroma_db/                 # 신규 - 벡터 DB (자동 생성)
│   └── models/                    # 신규 - 로컬 모델 캐시
├── requirements.txt               # 의존성 추가
└── qa_improvement_plan.md         # 이 문서
```

---

## 🚀 구현 계획

### Phase 1: 환경 설정 (30분)

**1.1 의존성 설치**
```bash
# requirements.txt에 추가
sentence-transformers==3.3.1
chromadb==0.5.23
```

**1.2 모델 다운로드**
- `jhgan/ko-sbert-sts` 자동 다운로드 (~150MB)
- 첫 실행 시 자동, 이후 캐시 사용

---

### Phase 2: 임베딩 서비스 구현 (1시간)

**파일: `app/services/embedding.py`**

```python
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self, model_name="jhgan/ko-sbert-sts"):
        logger.info(f"[Embedding] Loading model: {model_name}")
        self.model = SentenceTransformer(model_name)
        logger.info("[Embedding] Model loaded successfully")

    def encode(self, texts: list[str]) -> list[list[float]]:
        """텍스트 리스트를 벡터로 변환"""
        return self.model.encode(texts, show_progress_bar=False).tolist()

    def encode_single(self, text: str) -> list[float]:
        """단일 텍스트를 벡터로 변환"""
        return self.encode([text])[0]
```

---

### Phase 3: 벡터 스토어 구현 (1시간)

**파일: `app/services/vector_store.py`**

```python
import chromadb
from chromadb.config import Settings
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, persist_directory: str):
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="hanbang_qa",
            metadata={"hnsw:space": "cosine"}  # 코사인 유사도
        )
        logger.info(f"[VectorStore] Initialized at {persist_directory}")

    def add_documents(self, ids: List[str], embeddings: List[List[float]],
                      metadatas: List[Dict]):
        """문서 추가 (bulk insert)"""
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas
        )
        logger.info(f"[VectorStore] Added {len(ids)} documents")

    def search(self, query_embedding: List[float], top_k: int = 3):
        """벡터 검색"""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        return results

    def clear(self):
        """모든 문서 삭제"""
        self.client.delete_collection("hanbang_qa")
        self.collection = self.client.get_or_create_collection(
            name="hanbang_qa",
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("[VectorStore] Collection cleared")
```

---

### Phase 4: QA 로직 교체 (2시간)

**파일: `app/routers/qa.py` 수정**

#### 4.1 초기화
```python
from app.services.embedding import EmbeddingService
from app.services.vector_store import VectorStore

# 전역 인스턴스
embedding_service = EmbeddingService()
vector_store = VectorStore(persist_directory=os.path.join(BASE_DIR, "data", "chroma_db"))
```

#### 4.2 로더 수정
```python
def load_to_db(self, path: str) -> int:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Q&A markdown not found: {path}")

    logger.info(f"[QA Loader] Loading Q&A from: {path}")
    items = self.parse_markdown(path)
    logger.info(f"[QA Loader] Parsed {len(items)} Q&A items")

    # 1. SQLite에 저장 (메타데이터)
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM qa_documents")
        for qa in items:
            cur.execute(
                "INSERT INTO qa_documents (section, question, answer, source) VALUES (?, ?, ?, ?)",
                (qa["section"], qa["question"], qa["answer"], qa["source"]),
            )
        conn.commit()

    # 2. 벡터 DB에 저장
    vector_store.clear()

    # 임베딩 생성 (질문만)
    questions = [qa["question"] for qa in items]
    embeddings = embedding_service.encode(questions)

    # 메타데이터 준비
    ids = [str(i) for i in range(len(items))]
    metadatas = [
        {
            "question": qa["question"],
            "answer": qa["answer"],
            "section": qa["section"],
            "source": qa["source"] or ""
        }
        for qa in items
    ]

    vector_store.add_documents(ids, embeddings, metadatas)
    logger.info(f"[QA Loader] Loaded {len(items)} items into vector store")

    return len(items)
```

#### 4.3 검색 로직 교체
```python
def search(self, query: str, top_k: int) -> List[dict]:
    logger.info(f"[QA Search] Query: '{query}', Top K: {top_k}")

    # 1. 쿼리 임베딩
    query_embedding = embedding_service.encode_single(query)

    # 2. 벡터 검색
    results = vector_store.search(query_embedding, top_k=top_k * 2)

    # 3. 결과 파싱
    rows = []
    for i, metadata in enumerate(results['metadatas'][0]):
        distance = results['distances'][0][i]
        similarity = 1 - distance  # 코사인 유사도 (0~1)

        rows.append({
            "question": metadata["question"],
            "answer": metadata["answer"],
            "section": metadata["section"],
            "source": metadata.get("source", ""),
            "similarity": similarity
        })

    # 4. 임계값 필터링
    SIMILARITY_THRESHOLD = 0.65
    filtered_rows = [r for r in rows if r["similarity"] >= SIMILARITY_THRESHOLD]
    filtered_rows = filtered_rows[:top_k]

    if filtered_rows:
        logger.info(f"[QA Search] Top result similarity: {filtered_rows[0]['similarity']:.3f}")
    else:
        logger.warning(f"[QA Search] No results above threshold {SIMILARITY_THRESHOLD}")

    return filtered_rows
```

---

### Phase 5: 데이터 마이그레이션 (10분)

```bash
# 1. 서버 중지
# Ctrl+C

# 2. 의존성 설치
cd C:\Users\user\Documents\KaTokBot\19th_KatokBot_For_Student\fastapi
pip install sentence-transformers==3.3.1 chromadb==0.5.23

# 3. 데이터 재로드 (벡터 DB 생성)
curl -X POST http://localhost:9000/api/qa/reload \
  -H "X-API-Key: your-admin-key"

# 4. 테스트
curl -X POST http://localhost:9000/api/qa/search \
  -H "Content-Type: application/json" \
  -d '{"query": "식권정산", "top_k": 3}'
```

---

### Phase 6: 테스트 & 튜닝 (1시간)

**테스트 케이스**

| 입력 | 기대 결과 | 임계값 |
|------|----------|-------|
| "식권정산" | "식당의 정산 방법..." | 0.75+ |
| "한방 식당 정산" | "식당의 정산 방법..." | 0.80+ |
| "QR 발급" | "QR코드 재발급..." | 0.70+ |
| "블록체인" | (결과 없음) | < 0.65 |

**임계값 조정 가이드**
- 0.80+: 매우 유사 (거의 같은 질문)
- 0.65~0.80: 관련 질문
- 0.50~0.65: 약간 관련
- < 0.50: 무관

**추천 임계값**: 0.65 (필요시 0.6~0.7 조정)

---

## 📊 FTS vs RAG 비교

| 항목 | FTS5 + 동의어 (현재) | RAG (목표) |
|------|---------------------|-----------|
| **정확도** | ⭐⭐ (40%) | ⭐⭐⭐⭐⭐ (95%) |
| **유연성** | "식권정산" ❌ | "식권정산" ✅ |
| **DB 없는 질문 처리** | 부정확 | 임계값으로 확실히 차단 |
| **유지보수** | 동의어 수동 추가 | 자동 |
| **속도** | 10ms | 50ms |
| **메모리** | 50MB | 500MB |
| **구현 시간** | 2시간 (완료) | 5시간 |

---

## ✅ 체크리스트

### Phase 1: 환경 설정
- [ ] `sentence-transformers` 설치
- [ ] `chromadb` 설치
- [ ] 모델 다운로드 확인

### Phase 2-3: 서비스 구현
- [ ] `app/services/embedding.py` 작성
- [ ] `app/services/vector_store.py` 작성
- [ ] 유닛 테스트

### Phase 4: 로직 교체
- [ ] `QALoader.load_to_db()` 수정
- [ ] `QAService.search()` 수정
- [ ] 기존 FTS 코드 제거 (선택)

### Phase 5: 마이그레이션
- [ ] 데이터 재로드
- [ ] 벡터 DB 생성 확인

### Phase 6: 테스트
- [ ] "식권정산" → 정확한 답변
- [ ] "한방 식당 정산" → 정확한 답변
- [ ] "블록체인" → "관련 질문 없음"
- [ ] 임계값 튜닝 (0.6~0.7)

### Phase 7: 배포
- [ ] 로그 모니터링
- [ ] 카카오톡 봇 테스트
- [ ] 사용자 피드백 수집

---

## 🔧 트러블슈팅

### 문제 1: 모델 다운로드 실패
```bash
# 수동 다운로드
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('jhgan/ko-sbert-sts')"
```

### 문제 2: 메모리 부족
```python
# 배치 크기 줄이기
embeddings = embedding_service.encode(questions, batch_size=8)
```

### 문제 3: 검색 결과 없음
- 임계값 낮추기: 0.65 → 0.6 → 0.55
- 로그 확인: `logger.debug(f"Similarity: {similarity}")`

---

## 📈 예상 효과

| 지표 | 현재 (FTS) | 목표 (RAG) |
|------|----------|-----------|
| 검색 성공률 | 40% | 95% |
| 사용자 만족도 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 유지보수 시간 | 2시간/주 | 0.5시간/주 |
| 응답 속도 | 10ms | 50ms |

---

**작성일:** 2025-12-03
**현재 상태:** FTS5 + 동의어 확장 완료 (검색 실패율 높음)
**다음 단계:** RAG 전환 (Phase 1부터 순차 진행)
**예상 소요 시간:** 5시간
**담당자:** 개발팀
