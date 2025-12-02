"""
Retry Logic and Network Error Handling Utilities
재시도 로직 및 네트워크 오류 처리 유틸리티
"""
import time
import logging
from typing import Callable, TypeVar, Optional, Type, Tuple
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ====================================
# Custom Exception Classes
# ====================================

class NetworkError(Exception):
    """네트워크 관련 에러 기본 클래스"""
    pass


class APIConnectionError(NetworkError):
    """API 연결 실패"""
    def __init__(self, message: str, url: Optional[str] = None):
        self.url = url
        super().__init__(message)


class APITimeoutError(NetworkError):
    """API 타임아웃"""
    def __init__(self, message: str, timeout: Optional[int] = None):
        self.timeout = timeout
        super().__init__(message)


class APIRateLimitError(NetworkError):
    """API Rate Limit 초과"""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(message)


class APIServerError(NetworkError):
    """API 서버 에러 (5xx)"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)


class MaxRetriesExceededError(NetworkError):
    """최대 재시도 횟수 초과"""
    def __init__(self, message: str, attempts: int):
        self.attempts = attempts
        super().__init__(message)


# ====================================
# Retry Strategy Classes
# ====================================

class RetryStrategy:
    """재시도 전략 기본 클래스"""

    def get_wait_time(self, attempt: int) -> float:
        """재시도 전 대기 시간 계산 (초)"""
        raise NotImplementedError


class FixedDelayStrategy(RetryStrategy):
    """고정 지연 전략 (매번 같은 시간 대기)"""

    def __init__(self, delay: float = 1.0):
        """
        Args:
            delay: 대기 시간 (초)
        """
        self.delay = delay

    def get_wait_time(self, attempt: int) -> float:
        return self.delay


class ExponentialBackoffStrategy(RetryStrategy):
    """지수 백오프 전략 (대기 시간이 지수적으로 증가)"""

    def __init__(
        self,
        base_delay: float = 1.0,
        multiplier: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = True
    ):
        """
        Args:
            base_delay: 기본 대기 시간 (초)
            multiplier: 증가 배수
            max_delay: 최대 대기 시간 (초)
            jitter: 랜덤 지터 추가 여부 (동시 요청 분산)
        """
        self.base_delay = base_delay
        self.multiplier = multiplier
        self.max_delay = max_delay
        self.jitter = jitter

    def get_wait_time(self, attempt: int) -> float:
        import random

        # 지수 백오프 계산
        delay = min(
            self.base_delay * (self.multiplier ** (attempt - 1)),
            self.max_delay
        )

        # 지터 추가 (0.5 ~ 1.5배 랜덤)
        if self.jitter:
            delay = delay * (0.5 + random.random())

        return delay


class LinearBackoffStrategy(RetryStrategy):
    """선형 백오프 전략 (대기 시간이 선형적으로 증가)"""

    def __init__(self, base_delay: float = 1.0, increment: float = 1.0):
        """
        Args:
            base_delay: 기본 대기 시간 (초)
            increment: 증가량 (초)
        """
        self.base_delay = base_delay
        self.increment = increment

    def get_wait_time(self, attempt: int) -> float:
        return self.base_delay + (self.increment * (attempt - 1))


# ====================================
# Retry Decorator
# ====================================

def retry(
    max_attempts: int = 3,
    strategy: Optional[RetryStrategy] = None,
    exceptions: Tuple[Type[Exception], ...] = (NetworkError,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
    raise_on_max_retries: bool = True
):
    """
    재시도 데코레이터

    Args:
        max_attempts: 최대 시도 횟수
        strategy: 재시도 전략 (기본: ExponentialBackoff)
        exceptions: 재시도할 예외 타입들
        on_retry: 재시도 시 호출할 콜백 함수
        raise_on_max_retries: 최대 재시도 초과 시 예외 발생 여부

    Example:
        @retry(max_attempts=3, strategy=ExponentialBackoffStrategy())
        def call_api():
            response = requests.get("https://api.example.com")
            return response.json()
    """
    if strategy is None:
        strategy = ExponentialBackoffStrategy()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    # 함수 실행
                    result = func(*args, **kwargs)

                    # 성공 시 재시도 횟수 로그
                    if attempt > 1:
                        logger.info(
                            f"{func.__name__} succeeded on attempt {attempt}/{max_attempts}"
                        )

                    return result

                except exceptions as e:
                    last_exception = e

                    # 마지막 시도면 재시도 안함
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        break

                    # 대기 시간 계산
                    wait_time = strategy.get_wait_time(attempt)

                    # 재시도 로그
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                        f"Retrying in {wait_time:.2f}s..."
                    )

                    # 재시도 콜백 호출
                    if on_retry:
                        on_retry(e, attempt)

                    # 대기
                    time.sleep(wait_time)

            # 최대 재시도 초과
            if raise_on_max_retries:
                raise MaxRetriesExceededError(
                    f"Max retries ({max_attempts}) exceeded for {func.__name__}",
                    attempts=max_attempts
                ) from last_exception

            return None

        return wrapper
    return decorator


# ====================================
# Async Retry Decorator
# ====================================

def async_retry(
    max_attempts: int = 3,
    strategy: Optional[RetryStrategy] = None,
    exceptions: Tuple[Type[Exception], ...] = (NetworkError,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
    raise_on_max_retries: bool = True
):
    """
    비동기 재시도 데코레이터

    FastAPI의 async 함수에 사용
    """
    import asyncio

    if strategy is None:
        strategy = ExponentialBackoffStrategy()

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    result = await func(*args, **kwargs)

                    if attempt > 1:
                        logger.info(
                            f"{func.__name__} succeeded on attempt {attempt}/{max_attempts}"
                        )

                    return result

                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        break

                    wait_time = strategy.get_wait_time(attempt)

                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                        f"Retrying in {wait_time:.2f}s..."
                    )

                    if on_retry:
                        on_retry(e, attempt)

                    await asyncio.sleep(wait_time)

            if raise_on_max_retries:
                raise MaxRetriesExceededError(
                    f"Max retries ({max_attempts}) exceeded for {func.__name__}",
                    attempts=max_attempts
                ) from last_exception

            return None

        return wrapper
    return decorator


# ====================================
# Circuit Breaker Pattern
# ====================================

class CircuitBreakerState:
    """Circuit Breaker 상태"""
    CLOSED = "closed"      # 정상 동작
    OPEN = "open"          # 차단 (즉시 실패)
    HALF_OPEN = "half_open"  # 테스트 중


class CircuitBreaker:
    """
    Circuit Breaker 패턴 구현

    연속된 실패가 임계값을 초과하면 일정 시간 동안 요청을 차단
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exceptions: Tuple[Type[Exception], ...] = (NetworkError,)
    ):
        """
        Args:
            failure_threshold: 차단 임계값 (연속 실패 횟수)
            recovery_timeout: 복구 대기 시간 (초)
            expected_exceptions: 실패로 간주할 예외 타입들
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions

        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitBreakerState.CLOSED

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """함수 호출 (Circuit Breaker 적용)"""

        # OPEN 상태: 복구 시간 확인
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                logger.info("Circuit Breaker: Attempting reset (HALF_OPEN)")
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. Retry after "
                    f"{self.recovery_timeout - self._time_since_last_failure():.1f}s"
                )

        # 함수 실행
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exceptions as e:
            self._on_failure()
            raise

    def _on_success(self):
        """성공 시 처리"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            logger.info("Circuit Breaker: Recovery successful (CLOSED)")

        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED

    def _on_failure(self):
        """실패 시 처리"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            logger.error(
                f"Circuit Breaker: Threshold reached ({self.failure_count}). "
                f"State changed to OPEN"
            )
            self.state = CircuitBreakerState.OPEN

    def _should_attempt_reset(self) -> bool:
        """복구 시도 가능 여부"""
        return self._time_since_last_failure() >= self.recovery_timeout

    def _time_since_last_failure(self) -> float:
        """마지막 실패 이후 경과 시간 (초)"""
        if self.last_failure_time is None:
            return float('inf')
        return (datetime.now() - self.last_failure_time).total_seconds()

    def reset(self):
        """Circuit Breaker 수동 리셋"""
        logger.info("Circuit Breaker: Manual reset")
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
        self.last_failure_time = None

    def get_state(self) -> dict:
        """현재 상태 조회"""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time.isoformat()
                if self.last_failure_time else None,
            "time_since_last_failure": self._time_since_last_failure()
        }


class CircuitBreakerOpenError(NetworkError):
    """Circuit Breaker가 OPEN 상태일 때 발생"""
    pass


# ====================================
# Timeout Handler
# ====================================

class TimeoutHandler:
    """타임아웃 핸들러"""

    @staticmethod
    def with_timeout(timeout: float, func: Callable[..., T], *args, **kwargs) -> T:
        """
        타임아웃이 있는 함수 실행

        Args:
            timeout: 타임아웃 시간 (초)
            func: 실행할 함수
        """
        import signal

        def timeout_handler(signum, frame):
            raise APITimeoutError(f"Function timed out after {timeout}s", timeout=timeout)

        # 타임아웃 설정 (Unix 시스템만 지원)
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))

        try:
            result = func(*args, **kwargs)
            signal.alarm(0)  # 타임아웃 해제
            return result
        finally:
            signal.signal(signal.SIGALRM, old_handler)


# ====================================
# Utility Functions
# ====================================

def is_retryable_error(exception: Exception) -> bool:
    """재시도 가능한 에러인지 판단"""
    retryable_types = (
        APIConnectionError,
        APITimeoutError,
        APIServerError,
    )
    return isinstance(exception, retryable_types)


def get_retry_strategy(strategy_name: str = "exponential") -> RetryStrategy:
    """재시도 전략 팩토리"""
    strategies = {
        "fixed": FixedDelayStrategy(delay=2.0),
        "exponential": ExponentialBackoffStrategy(base_delay=1.0, max_delay=60.0),
        "linear": LinearBackoffStrategy(base_delay=1.0, increment=2.0),
    }
    return strategies.get(strategy_name, ExponentialBackoffStrategy())


# ====================================
# Example Usage
# ====================================

if __name__ == "__main__":
    # 예제 1: 재시도 데코레이터
    @retry(
        max_attempts=3,
        strategy=ExponentialBackoffStrategy(),
        exceptions=(NetworkError, ConnectionError)
    )
    def fetch_data():
        import random
        if random.random() < 0.7:  # 70% 실패
            raise APIConnectionError("Connection failed")
        return {"data": "success"}

    # 예제 2: Circuit Breaker
    circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=10.0)

    def unreliable_api():
        import random
        if random.random() < 0.8:
            raise APIServerError("Server error", status_code=500)
        return "OK"

    # 사용
    try:
        result = circuit_breaker.call(unreliable_api)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Circuit Breaker State: {circuit_breaker.get_state()}")
