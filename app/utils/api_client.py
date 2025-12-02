"""
API Client Wrapper with Retry Logic and Error Handling
재시도 로직과 오류 처리가 적용된 API 클라이언트
"""
import requests
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from retry_utils import (
    retry,
    async_retry,
    CircuitBreaker,
    ExponentialBackoffStrategy,
    APIConnectionError,
    APITimeoutError,
    APIRateLimitError,
    APIServerError,
    NetworkError,
)

logger = logging.getLogger(__name__)


# ====================================
# HTTP Client with Retry Logic
# ====================================

class ResilientHTTPClient:
    """
    재시도 로직이 적용된 HTTP 클라이언트

    Features:
    - 자동 재시도 (지수 백오프)
    - Circuit Breaker 패턴
    - 타임아웃 처리
    - Rate Limit 핸들링
    - 상세 에러 로깅
    """

    def __init__(
        self,
        base_url: str = "",
        timeout: int = 30,
        max_retries: int = 3,
        enable_circuit_breaker: bool = True,
        circuit_breaker_threshold: int = 5,
        default_headers: Optional[Dict[str, str]] = None
    ):
        """
        Args:
            base_url: 기본 URL
            timeout: 요청 타임아웃 (초)
            max_retries: 최대 재시도 횟수
            enable_circuit_breaker: Circuit Breaker 활성화 여부
            circuit_breaker_threshold: Circuit Breaker 임계값
            default_headers: 기본 헤더
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.default_headers = default_headers or {}

        # Circuit Breaker 설정
        self.circuit_breaker = None
        if enable_circuit_breaker:
            self.circuit_breaker = CircuitBreaker(
                failure_threshold=circuit_breaker_threshold,
                recovery_timeout=60.0
            )

        # 세션 생성 (연결 풀링)
        self.session = requests.Session()
        self.session.headers.update(self.default_headers)

        # 통계
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retry_count": 0,
        }

    def _build_url(self, endpoint: str) -> str:
        """전체 URL 생성"""
        endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{endpoint}" if self.base_url else endpoint

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """응답 처리 및 에러 핸들링"""

        # 성공 응답 (2xx)
        if 200 <= response.status_code < 300:
            try:
                return response.json()
            except ValueError:
                return {"text": response.text}

        # Rate Limit (429)
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            raise APIRateLimitError(
                f"Rate limit exceeded. Retry after {retry_after}s",
                retry_after=retry_after
            )

        # Server Error (5xx)
        if response.status_code >= 500:
            raise APIServerError(
                f"Server error: {response.status_code} - {response.text}",
                status_code=response.status_code
            )

        # Client Error (4xx)
        raise NetworkError(
            f"Client error: {response.status_code} - {response.text}"
        )

    @retry(
        max_attempts=3,
        strategy=ExponentialBackoffStrategy(base_delay=1.0, max_delay=30.0),
        exceptions=(APIConnectionError, APITimeoutError, APIServerError),
    )
    def _request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        HTTP 요청 실행 (재시도 로직 포함)

        Args:
            method: HTTP 메서드 (GET, POST, etc.)
            endpoint: API 엔드포인트
            headers: 추가 헤더
            params: URL 파라미터
            json: JSON 바디
            data: 일반 바디
        """
        url = self._build_url(endpoint)

        # 헤더 병합
        merged_headers = {**self.default_headers}
        if headers:
            merged_headers.update(headers)

        try:
            # Circuit Breaker 적용
            if self.circuit_breaker:
                response = self.circuit_breaker.call(
                    self.session.request,
                    method=method,
                    url=url,
                    headers=merged_headers,
                    params=params,
                    json=json,
                    data=data,
                    timeout=self.timeout
                )
            else:
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=merged_headers,
                    params=params,
                    json=json,
                    data=data,
                    timeout=self.timeout
                )

            # 통계 업데이트
            self.stats["total_requests"] += 1
            self.stats["successful_requests"] += 1

            return self._handle_response(response)

        except requests.exceptions.Timeout as e:
            self.stats["failed_requests"] += 1
            raise APITimeoutError(
                f"Request timeout after {self.timeout}s: {url}",
                timeout=self.timeout
            ) from e

        except requests.exceptions.ConnectionError as e:
            self.stats["failed_requests"] += 1
            raise APIConnectionError(
                f"Connection failed: {url}",
                url=url
            ) from e

        except requests.exceptions.RequestException as e:
            self.stats["failed_requests"] += 1
            raise NetworkError(f"Request failed: {e}") from e

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """GET 요청"""
        return self._request("GET", endpoint, headers=headers, params=params)

    def post(
        self,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """POST 요청"""
        return self._request("POST", endpoint, headers=headers, json=json, data=data)

    def put(
        self,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """PUT 요청"""
        return self._request("PUT", endpoint, headers=headers, json=json)

    def delete(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """DELETE 요청"""
        return self._request("DELETE", endpoint, headers=headers)

    def get_stats(self) -> Dict[str, Any]:
        """통계 조회"""
        stats = self.stats.copy()
        if self.circuit_breaker:
            stats["circuit_breaker"] = self.circuit_breaker.get_state()
        return stats

    def reset_stats(self):
        """통계 초기화"""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retry_count": 0,
        }

    def close(self):
        """세션 종료"""
        self.session.close()


# ====================================
# LLM API Client (Perplexity/OpenAI 등)
# ====================================

class LLMAPIClient(ResilientHTTPClient):
    """
    LLM API 전용 클라이언트

    Perplexity, OpenAI, Claude 등 LLM API 호출에 최적화
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str = "sonar-pro",
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Args:
            api_key: API 키
            base_url: API 기본 URL
            model: 모델 이름
            timeout: 타임아웃 (초)
            max_retries: 최대 재시도 횟수
        """
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        super().__init__(
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=headers,
            enable_circuit_breaker=True,
            circuit_breaker_threshold=5
        )

        self.model = model
        self.api_key = api_key

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500,
        **kwargs
    ) -> Dict[str, Any]:
        """
        채팅 완성 API 호출

        Args:
            messages: 메시지 배열 [{"role": "user", "content": "..."}]
            temperature: 창의성 수준 (0~1)
            max_tokens: 최대 토큰 수
        """
        request_body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        try:
            logger.info(f"LLM API request: {len(messages)} messages, model={self.model}")

            response = self.post("/chat/completions", json=request_body)

            # 응답 파싱
            if "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0]["message"]["content"]
                usage = response.get("usage", {})

                logger.info(
                    f"LLM API response: {usage.get('total_tokens', 0)} tokens used"
                )

                return {
                    "content": content,
                    "usage": usage,
                    "model": response.get("model", self.model),
                    "raw_response": response
                }

            raise NetworkError("Invalid LLM API response format")

        except APIRateLimitError as e:
            logger.error(f"LLM API rate limit: {e}")
            # Rate Limit 시 기본 응답 반환
            return {
                "content": "API 사용량이 초과되었습니다. 잠시 후 다시 시도해주세요.",
                "error": "rate_limit",
                "retry_after": e.retry_after
            }

        except APITimeoutError as e:
            logger.error(f"LLM API timeout: {e}")
            return {
                "content": "응답 시간이 초과되었습니다. 다시 시도해주세요.",
                "error": "timeout"
            }

        except NetworkError as e:
            logger.error(f"LLM API error: {e}")
            return {
                "content": "API 호출 중 오류가 발생했습니다.",
                "error": str(e)
            }


# ====================================
# FastAPI용 Async HTTP Client
# ====================================

class AsyncResilientHTTPClient:
    """
    비동기 HTTP 클라이언트 (FastAPI용)

    httpx 라이브러리 사용
    """

    def __init__(
        self,
        base_url: str = "",
        timeout: int = 30,
        max_retries: int = 3,
        default_headers: Optional[Dict[str, str]] = None
    ):
        try:
            import httpx
            self.httpx = httpx
        except ImportError:
            raise ImportError("httpx is required for async client. Install: pip install httpx")

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.default_headers = default_headers or {}

        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager 진입"""
        self.client = self.httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self.default_headers
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager 종료"""
        if self.client:
            await self.client.aclose()

    @async_retry(
        max_attempts=3,
        strategy=ExponentialBackoffStrategy(),
        exceptions=(APIConnectionError, APITimeoutError, APIServerError)
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """비동기 HTTP 요청"""
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            response = await self.client.request(method, endpoint, **kwargs)

            if 200 <= response.status_code < 300:
                return response.json()

            if response.status_code >= 500:
                raise APIServerError(
                    f"Server error: {response.status_code}",
                    status_code=response.status_code
                )

            raise NetworkError(f"HTTP {response.status_code}: {response.text}")

        except self.httpx.TimeoutException as e:
            raise APITimeoutError(f"Request timeout: {endpoint}") from e

        except self.httpx.ConnectError as e:
            raise APIConnectionError(f"Connection failed: {endpoint}") from e

    async def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """비동기 GET 요청"""
        return await self._request("GET", endpoint, **kwargs)

    async def post(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """비동기 POST 요청"""
        return await self._request("POST", endpoint, **kwargs)


# ====================================
# Example Usage
# ====================================

if __name__ == "__main__":
    # 예제 1: 일반 HTTP 클라이언트
    client = ResilientHTTPClient(
        base_url="https://api.example.com",
        timeout=10,
        max_retries=3
    )

    try:
        response = client.get("/users", params={"limit": 10})
        print(f"Response: {response}")
    except NetworkError as e:
        print(f"Error: {e}")
    finally:
        print(f"Stats: {client.get_stats()}")
        client.close()

    # 예제 2: LLM API 클라이언트
    llm_client = LLMAPIClient(
        api_key="your-api-key",
        base_url="https://api.perplexity.ai",
        model="sonar-pro"
    )

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ]

    try:
        result = llm_client.chat_completion(messages)
        print(f"AI Response: {result['content']}")
        print(f"Tokens used: {result['usage']}")
    except NetworkError as e:
        print(f"Error: {e}")
    finally:
        llm_client.close()
