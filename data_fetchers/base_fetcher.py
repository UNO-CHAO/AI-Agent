"""
数据抓取基类
定义统一的数据获取接口，包含重试机制和错误处理
"""

import time
import logging
import random
from abc import ABC, abstractmethod
from typing import Any, Optional, Callable
from functools import wraps

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    重试装饰器

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 退避系数，每次重试延迟乘以此系数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} 第 {attempt + 1} 次尝试失败: {e}, "
                            f"{current_delay:.1f}秒后重试..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"{func.__name__} 重试 {max_retries} 次后仍然失败: {e}"
                        )

            raise last_exception
        return wrapper
    return decorator


class FetchResult:
    """
    标准化的数据获取结果类
    """

    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: Optional[str] = None,
        source: Optional[str] = None,
        count: int = 0
    ):
        self.success = success
        self.data = data
        self.error = error
        self.source = source
        self.count = count
        self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'source': self.source,
            'count': self.count,
            'timestamp': self.timestamp
        }

    def __repr__(self) -> str:
        status = "成功" if self.success else "失败"
        return f"<FetchResult [{status}] source={self.source}, count={self.count}>"


class BaseFetcher(ABC):
    """
    数据抓取基类
    所有数据源抓取器都应继承此类
    """

    def __init__(self, source_name: str = "unknown"):
        """
        初始化抓取器

        Args:
            source_name: 数据源名称，用于日志和结果标识
        """
        self.source_name = source_name
        self.logger = logging.getLogger(f"{__name__}.{source_name}")

    def _retry_call(
        self,
        func: Callable,
        max_retries: int = 3,
        min_delay: float = 2.0,
        max_delay: float = 5.0,
        backoff: float = 2.0,
        func_name: Optional[str] = None
    ) -> Any:
        """
        带随机延迟的重试调用方法
        用于 akshare API 调用的重试机制

        Args:
            func: 要调用的函数（无参数）
            max_retries: 最大重试次数
            min_delay: 最小延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            backoff: 退避系数，每次重试延迟范围乘以此系数
            func_name: 函数名称（用于日志），默认从函数对象获取

        Returns:
            函数调用的结果

        Raises:
            Exception: 重试次数耗尽后抛出最后一次异常
        """
        if func_name is None:
            func_name = func.__name__ if hasattr(func, '__name__') else 'unknown'

        last_exception = None
        current_min_delay = min_delay
        current_max_delay = max_delay

        for attempt in range(max_retries + 1):
            try:
                return func()
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    # 随机延迟
                    delay = random.uniform(current_min_delay, current_max_delay)
                    self.logger.warning(
                        f"[{self.source_name}] {func_name} 第 {attempt + 1} 次调用失败: {type(e).__name__}: {e}, "
                        f"{delay:.1f}秒后重试 (剩余重试次数: {max_retries - attempt})"
                    )
                    time.sleep(delay)
                    # 退避：增加延迟范围
                    current_min_delay *= backoff
                    current_max_delay *= backoff
                else:
                    self.logger.error(
                        f"[{self.source_name}] {func_name} 重试 {max_retries} 次后仍然失败: {type(e).__name__}: {e}"
                    )

        # 重试耗尽，抛出最后一次异常
        raise last_exception

    def _safe_call(
        self,
        func: Callable,
        default_value: Any = None,
        func_name: Optional[str] = None,
        log_warning: bool = True
    ) -> Any:
        """
        安全调用：执行函数，失败时返回默认值而不抛出异常
        内部使用 _retry_call 进行重试

        Args:
            func: 要调用的函数
            default_value: 失败时返回的默认值
            func_name: 函数名称（用于日志）
            log_warning: 是否在失败时记录警告日志

        Returns:
            函数调用结果或默认值
        """
        try:
            return self._retry_call(func, func_name=func_name)
        except Exception as e:
            if log_warning:
                self.logger.warning(
                    f"[{self.source_name}] {func_name or 'unknown'} 最终失败，返回默认值: {e}"
                )
            return default_value

    @abstractmethod
    def fetch(self, *args, **kwargs) -> FetchResult:
        """
        抽象方法：获取数据
        子类必须实现此方法

        Returns:
            FetchResult: 标准化的获取结果
        """
        pass

    @abstractmethod
    def normalize(self, raw_data: Any) -> list[dict]:
        """
        抽象方法：标准化数据格式
        子类必须实现此方法

        Args:
            raw_data: 原始数据

        Returns:
            list[dict]: 标准化的字典列表
        """
        pass

    def fetch_with_retry(
        self,
        max_retries: int = 3,
        delay: float = 1.0,
        *args,
        **kwargs
    ) -> FetchResult:
        """
        带重试机制的数据获取

        Args:
            max_retries: 最大重试次数
            delay: 重试延迟
            *args, **kwargs: 传递给 fetch 方法的参数

        Returns:
            FetchResult: 标准化的获取结果
        """
        current_delay = delay

        for attempt in range(max_retries + 1):
            try:
                result = self.fetch(*args, **kwargs)
                if result.success:
                    return result

                # 如果返回了失败结果但没有抛出异常，也进行重试
                if attempt < max_retries:
                    self.logger.warning(
                        f"[{self.source_name}] 第 {attempt + 1} 次获取失败: {result.error}, "
                        f"{current_delay:.1f}秒后重试..."
                    )
                    time.sleep(current_delay)
                    current_delay *= 2
                else:
                    return result

            except Exception as e:
                if attempt < max_retries:
                    self.logger.warning(
                        f"[{self.source_name}] 第 {attempt + 1} 次尝试异常: {e}, "
                        f"{current_delay:.1f}秒后重试..."
                    )
                    time.sleep(current_delay)
                    current_delay *= 2
                else:
                    self.logger.error(f"[{self.source_name}] 重试 {max_retries} 次后仍然失败: {e}")
                    return FetchResult(
                        success=False,
                        error=str(e),
                        source=self.source_name
                    )

        return FetchResult(
            success=False,
            error="未知错误",
            source=self.source_name
        )

    def safe_fetch(self, *args, **kwargs) -> FetchResult:
        """
        安全获取：捕获所有异常，确保不抛出错误

        Returns:
            FetchResult: 始终返回结果对象，不会抛出异常
        """
        try:
            return self.fetch_with_retry(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"[{self.source_name}] 安全获取失败: {e}")
            return FetchResult(
                success=False,
                error=str(e),
                source=self.source_name
            )