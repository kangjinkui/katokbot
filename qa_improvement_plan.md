# 📋 유연한 Q&A 검색 시스템 개선 계획

## 현재 상황 분석

**현재 방식:** SQLite FTS5 (키워드 기반)

**문제점:**
- "정산 업무가 얼마나 줄어드나요?" ≠ "정산 시간 절약돼요?"
- 단어가 정확히 일치해야만 검색됨

**원인:** FTS5는 정확한 키워드 매칭만 수행

---

## 🎯 개선 방안 (3가지 옵션)

### 옵션 1: 동의어 사전 추가 (간단, 빠름 ⭐ 추천)

**장점:**
- 구현 간단 (1시간 내)
- 추가 패키지 불필요
- 빠른 속도 유지 (~10ms)

**단점:**
- 수동으로 동의어 관리 필요
- 완벽한 커버리지 불가능

**구현 방법:**

```python
class QAService:
    SYNONYM_MAP = {
        "정산": ["정산", "계산", "처리", "집계"],
        "업무": ["업무", "일", "작업", "처리"],
        "줄어들다": ["줄어들다", "절약", "단축", "감소"],
        "QR코드": ["QR코드", "QR", "큐알", "큐알코드"],
        "식권": ["식권", "쿠폰", "한방식권"],
    }

    def expand_query(self, query):
        # "정산 업무" → "정산 OR 계산 OR 집계 업무 OR 일 OR 작업"
        expanded_terms = []
        for word in query.split():
            if word in self.SYNONYM_MAP:
                expanded_terms.append(" OR ".join(self.SYNONYM_MAP[word]))
            else:
                expanded_terms.append(word)
        return " ".join(expanded_terms)
```

---

### 옵션 2: 임베딩 기반 검색 (정확도 최고, 무겁지만 가능)

**장점:**
- 의미 기반 검색 (가장 정확)
- 자연어 질문 이해
- 동의어 자동 처리

**단점:**
- 모델 다운로드 필요 (~500MB)
- 메모리 사용량 증가 (~1GB)
- 검색 속도 느림 (50~100ms)

**구현 방법:**

```python
# requirements.txt
sentence-transformers==2.2.2

# qa.py
from sentence_transformers import SentenceTransformer
import numpy as np

class QAService:
    def __init__(self):
        # 한국어 경량 모델
        self.model = SentenceTransformer('jhgan/ko-sroberta-multitask')
        self.load_embeddings()

    def load_embeddings(self):
        # DB에서 모든 Q&A 로드
        rows = db.execute_query("SELECT id, question, answer FROM qa_documents")
        self.docs = rows

        # 질문 임베딩 생성 (서버 시작 시 1회)
        questions = [r['question'] for r in rows]
        self.embeddings = self.model.encode(questions)

    def search(self, query, top_k):
        # 쿼리 임베딩
        query_emb = self.model.encode([query])[0]

        # 코사인 유사도 계산
        scores = np.dot(self.embeddings, query_emb)
        top_indices = np.argsort(scores)[-top_k:][::-1]

        return [self.docs[i] for i in top_indices]
```

---

### 옵션 3: 하이브리드 (FTS5 + 간단한 유사도) (균형잡힌 선택)

**장점:**
- 빠른 속도 유지 (~30ms)
- 의미 유사도도 고려
- 가벼움 (~100MB)

**단점:**
- 임베딩보다 정확도 낮음

**구현 방법:**

```python
from difflib import SequenceMatcher

class QAService:
    def search(self, query, top_k):
        # 1단계: FTS5로 후보 추출 (top_k * 3)
        candidates = self._fts_search(query, top_k * 3)

        # 2단계: 문자열 유사도로 재정렬
        for candidate in candidates:
            similarity = SequenceMatcher(
                None,
                query.lower(),
                candidate['question'].lower()
            ).ratio()
            candidate['similarity'] = similarity

        # 유사도 순 정렬
        candidates.sort(key=lambda x: x['similarity'], reverse=True)
        return candidates[:top_k]
```

---

## 🚀 추천 구현 순서

### Phase 1: 동의어 사전 (즉시 적용) ⭐

```python
# app/routers/qa.py에 추가
class QAService:
    SYNONYMS = {
        "정산": ["정산", "계산", "집계", "처리"],
        "업무": ["업무", "일", "작업"],
        "절약": ["절약", "줄어들다", "단축", "감소"],
        "QR": ["QR", "큐알", "QR코드"],
        "식권": ["식권", "쿠폰", "한방식권", "한방쿠폰"],
        "사용": ["사용", "쓰다", "이용"],
        "등록": ["등록", "가입", "신청"],
        "분실": ["분실", "잃어버리다", "없어지다"],
    }
```

### Phase 2: 쿼리 확장 로직

```python
def expand_query(self, query):
    words = self.sanitize_fts_query(query).split()
    expanded = []

    for word in words:
        # 동의어 찾기
        synonyms = None
        for key, syns in self.SYNONYMS.items():
            if word in syns or word == key:
                synonyms = syns
                break

        if synonyms:
            # OR 연산으로 확장
            expanded.append("(" + " OR ".join(synonyms) + ")")
        else:
            expanded.append(word)

    return " ".join(expanded)
```

### Phase 3: 테스트

```bash
# "정산 시간 절약돼요?" → "(정산 OR 계산 OR 집계) 시간 (절약 OR 줄어들다 OR 단축)"
curl -X POST http://localhost:9000/api/qa/search \
  -H "Content-Type: application/json" \
  -d '{"query": "정산 시간 절약돼요", "top_k": 2}'
```

---

## 📊 옵션 비교표

| 항목 | 옵션1: 동의어 | 옵션2: 임베딩 | 옵션3: 하이브리드 |
|------|--------------|--------------|------------------|
| **구현 시간** | 1시간 | 3시간 | 2시간 |
| **정확도** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **속도** | 10ms | 100ms | 30ms |
| **메모리** | 50MB | 1GB | 100MB |
| **유지보수** | 동의어 수동 추가 | 자동 | 중간 |
| **추가 패키지** | 불필요 | sentence-transformers | 불필요 |
| **모델 다운로드** | 불필요 | ~500MB | 불필요 |

---

## ✅ 최종 추천

### 단계별 접근:

1. **지금 당장 (Week 1)**: 옵션1 (동의어 사전) 구현
   - 빠른 개선 효과
   - 위험도 낮음
   - 즉시 배포 가능

2. **2주 후 (Week 3)**: 사용자 피드백 수집
   - 검색 로그 분석
   - 검색 실패 케이스 파악
   - 동의어 사전 확장

3. **필요시 (Month 2+)**: 옵션2 (임베딩) 도입
   - 사용자 수 증가 시
   - 정확도 요구사항 상승 시
   - 서버 리소스 충분할 때

---

## 📝 구현 체크리스트

### Phase 1: 동의어 사전
- [ ] `SYNONYMS` 딕셔너리 추가
- [ ] `expand_query()` 메서드 구현
- [ ] `search()` 메서드에 통합
- [ ] 로컬 테스트
- [ ] VM 배포
- [ ] 카카오톡 봇 테스트

### Phase 2: 모니터링
- [ ] 검색 로그 수집 로직 추가
- [ ] 검색 실패율 측정
- [ ] 동의어 효과 분석

### Phase 3: 고도화 (선택)
- [ ] 임베딩 모델 선택
- [ ] 성능 테스트
- [ ] 메모리 최적화
- [ ] 점진적 배포

---

**작성일:** 2025-12-02
**현재 구현 상태:** FTS5 기본 검색 완료 (45개 Q&A 로드됨)
**다음 단계:** 동의어 사전 추가
