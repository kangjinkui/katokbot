# 프로젝트 구조 개선 마이그레이션 가이드

## 변경 사항 요약

기존의 중복되고 비효율적인 구조를 표준 FastAPI 프로젝트 구조로 개선했습니다.

## 이전 구조 vs 개선된 구조

### 이전 구조 (문제점)
```
fastapi/
├── fastapi/          ❌ 중복된 폴더
│   └── main.py      ❌ 의미없는 테스트 코드
├── main.py          # 실제 메인 앱
├── models.py        # 모든 모델이 한 파일에
├── routers.py       # 모든 라우터가 한 파일에
├── database.py
├── database_improved.py  ❌ 중복
├── qa.py
├── dashboard_routes.py
├── api_client.py
├── retry_utils.py
└── venv/            ❌ 중복된 가상환경
```

### 개선된 구조 (표준 구조)
```
fastapi/
├── app/                      ✅ 메인 애플리케이션 패키지
│   ├── __init__.py
│   ├── main.py              # FastAPI 앱 엔트리포인트
│   ├── config.py            # 설정 중앙 관리
│   ├── models/              # Pydantic 모델 분리
│   │   ├── __init__.py
│   │   └── chat_models.py
│   ├── routers/             # 라우터별 파일 분리
│   │   ├── __init__.py
│   │   ├── chat.py         # 채팅 관련
│   │   ├── users.py        # 사용자 관리
│   │   ├── stats.py        # 통계
│   │   ├── admin.py        # 관리
│   │   ├── qa.py           # Q&A 검색
│   │   └── dashboard.py    # 대시보드
│   ├── database/            # 데이터베이스 레이어 분리
│   │   ├── __init__.py
│   │   ├── connection.py   # DB 연결 관리
│   │   └── repositories.py # Repository 패턴
│   └── utils/               # 유틸리티 함수
│       ├── __init__.py
│       ├── api_client.py
│       └── retry_utils.py
├── static/                  # 정적 파일
├── templates/               # HTML 템플릿
├── data/                    # 데이터 파일
├── backup/                  # 백업 파일
├── venv/                    # 가상환경 (하나만)
├── requirements.txt
├── .env
├── .gitignore
├── run.py                   # 서버 실행 스크립트
└── README.md
```

## 주요 개선 사항

### 1. 중복 제거
- ❌ 삭제: `fastapi/fastapi/` 중첩 폴더
- ❌ 삭제: `database_improved.py` 중복 파일
- ❌ 삭제: 루트의 개별 파일들 (`models.py`, `routers.py` 등)

### 2. 모듈화 및 관심사 분리
- **Models**: `app/models/` - 모든 Pydantic 모델
- **Routers**: `app/routers/` - 기능별로 분리된 라우터
- **Database**: `app/database/` - DB 연결 및 Repository 패턴
- **Utils**: `app/utils/` - 공통 유틸리티

### 3. 설정 중앙화
- `app/config.py`: 모든 환경 변수와 설정을 한 곳에서 관리

### 4. 명확한 진입점
- `run.py`: 서버 실행을 위한 명확한 진입점
- `app/main.py`: FastAPI 앱 정의

## Import 경로 변경

### 이전
```python
from models import ChatRequest, ChatResponse
from database import db, user_repo
from routers import chat_router
```

### 현재
```python
from app.models import ChatRequest, ChatResponse
from app.database import db, user_repo
from app.routers import chat_router
```

## 서버 실행 방법 변경

### 이전
```bash
# uvicorn으로 직접 실행
uvicorn main:app --reload
```

### 현재
```bash
# 방법 1: run.py 스크립트 사용 (권장)
python run.py

# 방법 2: uvicorn 직접 실행
uvicorn app.main:app --reload
```

## 새로운 기능 추가 방법

### 새 라우터 추가
1. `app/routers/` 에 새 파일 생성 (예: `notifications.py`)
2. `app/routers/__init__.py` 에 import 추가:
   ```python
   from .notifications import notification_router
   ```
3. `app/main.py` 에 라우터 등록:
   ```python
   app.include_router(notification_router)
   ```

### 새 모델 추가
1. `app/models/chat_models.py` 에 Pydantic 모델 추가
2. `app/models/__init__.py` 에 export 추가

### 새 Repository 메서드 추가
1. `app/database/repositories.py` 의 해당 Repository 클래스에 메서드 추가

## 백업 파일

혹시 모를 문제를 대비해 다음 파일들이 백업되었습니다:
- `backup/old_main.py` - 이전 중첩 폴더의 main.py
- `backup/database_improved.py` - 이전 개선 버전

## 테스트 체크리스트

리팩토링 후 다음 사항들을 테스트했습니다:

- ✅ Models import 정상 동작
- ✅ Database import 정상 동작
- ✅ Routers import 정상 동작
- ✅ Main app import 정상 동작
- ✅ 28개의 라우트 정상 등록

## 문제 발생 시

만약 문제가 발생하면:

1. **Import 에러**: Python 경로에 프로젝트 루트가 포함되어 있는지 확인
   ```bash
   export PYTHONPATH="${PYTHONPATH}:/path/to/fastapi"
   ```

2. **모듈을 찾을 수 없음**: 가상환경이 활성화되어 있는지 확인
   ```bash
   source venv/bin/activate  # Linux/Mac
   .\\venv\\Scripts\\activate  # Windows
   ```

3. **DB 연결 실패**: `katokbot.db` 파일이 프로젝트 루트에 있는지 확인

## 추가 권장 사항

1. **타입 힌팅**: 모든 함수에 타입 힌팅 추가 권장
2. **로깅**: 각 모듈별로 로거 사용 (이미 적용됨)
3. **테스트**: `tests/` 디렉토리 생성 및 단위 테스트 추가
4. **API 문서화**: Docstring 작성 (이미 대부분 적용됨)

## 다음 단계

1. 테스트 코드 작성
2. CI/CD 파이프라인 구축
3. Docker 컨테이너화
4. API 버저닝 고려
5. 로깅 및 모니터링 강화
