# KaTokBot FastAPI Backend

표준 FastAPI 프로젝트 구조로 재구성된 카톡봇 백엔드 서버입니다.

## 프로젝트 구조

```
fastapi/
├── app/                      # 메인 애플리케이션 패키지
│   ├── __init__.py
│   ├── main.py              # FastAPI 앱 엔트리포인트
│   ├── config.py            # 설정 관리
│   ├── models/              # Pydantic 모델
│   │   ├── __init__.py
│   │   └── chat_models.py
│   ├── routers/             # API 라우터
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   ├── users.py
│   │   ├── stats.py
│   │   ├── admin.py
│   │   ├── qa.py
│   │   └── dashboard.py
│   ├── database/            # 데이터베이스 레이어
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   └── repositories.py
│   └── utils/               # 유틸리티 함수
│       ├── __init__.py
│       ├── api_client.py
│       └── retry_utils.py
├── static/                  # 정적 파일
├── templates/               # HTML 템플릿
├── data/                    # 데이터 파일
├── backup/                  # 백업 파일
├── venv/                    # 가상환경
├── requirements.txt         # 의존성 목록
├── .env                     # 환경 변수
├── run.py                   # 서버 실행 스크립트
└── README.md
```

## 설치 및 실행

### 1. 가상환경 생성 및 활성화

```bash
# Windows
python -m venv venv
.\\venv\\Scripts\\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env` 파일을 생성하고 필요한 환경 변수를 설정합니다:

```env
DEBUG=True
DATABASE_PATH=katokbot.db
ADMIN_API_KEY=your-secret-key
LOG_LEVEL=INFO
SESSION_TIMEOUT_MINUTES=30
MESSAGE_RETENTION_DAYS=90
```

### 4. 서버 실행

```bash
# 방법 1: run.py 스크립트 사용
python run.py

# 방법 2: uvicorn 직접 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. API 문서 확인

서버 실행 후 아래 URL에서 API 문서를 확인할 수 있습니다:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 엔드포인트

### Chat (채팅)
- `POST /api/chat/message` - 메시지 전송
- `POST /api/chat/history` - 대화 기록 조회
- `DELETE /api/chat/session/{room_name}/{author_name}` - 세션 초기화

### Users (사용자)
- `POST /api/users/` - 사용자 생성
- `GET /api/users/{user_id}` - 사용자 조회
- `PATCH /api/users/{user_id}` - 사용자 수정
- `GET /api/users/` - 사용자 목록

### Stats (통계)
- `GET /api/stats/users/{user_id}` - 사용자 통계
- `GET /api/stats/top-users` - TOP 사용자

### Admin (관리)
- `POST /api/admin/cleanup/sessions` - 세션 정리
- `POST /api/admin/cleanup/messages` - 메시지 정리
- `POST /api/admin/db/vacuum` - DB 최적화

### QA (검색)
- `POST /api/qa/search` - Q&A 검색
- `POST /api/qa/reload` - Q&A 데이터 리로드

### Dashboard (대시보드)
- `GET /api/dashboard/rooms` - 방 목록
- `GET /api/dashboard/rooms/{room_name}/users` - 방별 사용자
- `GET /api/dashboard/users/{user_id}/messages` - 사용자 메시지
- `GET /api/dashboard/stats/overview` - 전체 통계
- `GET /api/dashboard/search` - 통합 검색
- `GET /api/dashboard/timeline` - 활동 타임라인

## 주요 개선 사항

1. **모듈화된 구조**: 관심사 분리 원칙에 따라 코드 구조화
2. **명확한 계층 분리**: Models, Routers, Database, Utils로 계층 분리
3. **중복 제거**: 중복된 파일 및 폴더 제거
4. **설정 관리**: config.py를 통한 중앙화된 설정 관리
5. **표준 규칙**: FastAPI 베스트 프랙티스 준수

## 개발 가이드

### 새로운 라우터 추가

1. `app/routers/` 디렉토리에 새 파일 생성
2. `app/routers/__init__.py`에 라우터 import 추가
3. `app/main.py`에 라우터 등록

### 새로운 모델 추가

1. `app/models/chat_models.py`에 Pydantic 모델 추가
2. `app/models/__init__.py`에 export 추가

### 데이터베이스 작업

- Repository 패턴 사용
- `app/database/repositories.py`에 새로운 repository 메서드 추가

## 라이선스

MIT
