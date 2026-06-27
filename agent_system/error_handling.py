#!/usr/bin/env python3
"""
明烛统一错误处理与结构化日志 v3.7

解决"错误处理与可观测性不足"问题：
- 统一错误处理：safe_run 装饰器，捕获异常+重试+降级
- 结构化日志：JSON格式，便于日志聚合和排查
- 链路追踪：每个请求带 request_id，串联调用链

不依赖外部库（structlog/OpenTelemetry），纯Python实现，部署友好。
"""
import os
import json
import time
import uuid
import logging
import functools
from typing import Callable, Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


class StructuredLogger:
    """结构化日志（JSON格式，便于聚合和排查）"""

    def __init__(self, name: str = "mingzhu"):
        self._logger = logging.getLogger(name)
        self._request_id: Optional[str] = None

    def set_request_id(self, request_id: str = None):
        self._request_id = request_id or str(uuid.uuid4())[:8]

    def _log(self, level: str, event: str, **kwargs):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "event": event,
            "request_id": self._request_id,
            **kwargs,
        }
        msg = json.dumps(entry, ensure_ascii=False)
        getattr(self._logger, level.lower(), self._logger.info)(msg)

    def info(self, event: str, **kwargs): self._log("info", event, **kwargs)
    def warning(self, event: str, **kwargs): self._log("warning", event, **kwargs)
    def error(self, event: str, **kwargs): self._log("error", event, **kwargs)
    def debug(self, event: str, **kwargs): self._log("debug", event, **kwargs)


logger = StructuredLogger("mingzhu")


@dataclass
class ErrorContext:
    function: str
    args_summary: str = ""
    retry_count: int = 0
    last_error: str = ""
    fallback_used: bool = False
    latency_ms: float = 0.0


def safe_run(retries: int = 2, delay: float = 0.5, fallback: Any = None, log_errors: bool = True):
    """统一错误处理装饰器：重试+降级+结构化日志"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            last_error = None
            for attempt in range(retries + 1):
                try:
                    result = func(*args, **kwargs)
                    latency = (time.time() - start) * 1000
                    if attempt > 0:
                        logger.info("retry_succeeded", function=func.__name__,
                                    attempts=attempt + 1, latency_ms=round(latency, 1))
                    return result
                except Exception as e:
                    last_error = e
                    if log_errors:
                        logger.warning("attempt_failed", function=func.__name__,
                                       attempt=attempt + 1, max_attempts=retries + 1, error=str(e))
                    if attempt < retries:
                        time.sleep(delay * (attempt + 1))
                    continue
            latency = (time.time() - start) * 1000
            if log_errors:
                logger.error("all_retries_failed", function=func.__name__,
                             retries=retries + 1, error=str(last_error),
                             latency_ms=round(latency, 1), fallback_used=fallback is not None)
            return fallback
        return wrapper
    return decorator


def get_request_id() -> str:
    return logger._request_id or "no-request-id"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.set_request_id("test-001")
    logger.info("test_start", module="error_handling")

    @safe_run(retries=2, fallback="降级结果")
    def flaky_function(fail: bool):
        if fail:
            raise ValueError("模拟失败")
        return "成功"

    print("=== 测试1：成功 ===")
    print(flaky_function(fail=False))
    print("\n=== 测试2：失败后降级 ===")
    print(f"结果: {flaky_function(fail=True)}")
