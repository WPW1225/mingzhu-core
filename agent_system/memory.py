#!/usr/bin/env python3
"""
明烛长期记忆 v3.2
将对话记忆持久化到 JSON 文件，重启不丢失。

设计：
- 每个会话（thread_id）一个 JSON 文件
- 存储用户输入、明烛回复、人格调用、时间戳
- 自动限制每会话最多保留最近 50 轮（防止无限增长）
- 可查询历史会话列表

存储位置：agent_system/memory_store/<thread_id>.json
"""
import os
import json
import time
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

MEMORY_DIR = Path(__file__).parent.parent / "memory_store"
MAX_TURNS_PER_SESSION = 50  # 每会话最多保留轮数


@dataclass
class MemoryEntry:
    """单轮对话记忆"""
    timestamp: str
    user_input: str
    output: str
    personas: List[Dict] = field(default_factory=list)  # 调用了哪些人格
    models: List[str] = field(default_factory=list)     # 用了哪些模型
    observer: str = ""                                   # 坎观观察
    latency_ms: float = 0.0

    def to_dict(self) -> Dict:
        return asdict(self)


class LongTermMemory:
    """长期记忆管理器（文件持久化）"""

    def __init__(self, memory_dir: Path = None):
        self.memory_dir = memory_dir or MEMORY_DIR
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        # 按 thread_id 加锁：防止同一会话并发 save_turn 时的读-改-写竞态。
        # 不同会话用不同锁，互不阻塞。
        self._locks: Dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def _lock_for(self, thread_id: str) -> threading.Lock:
        """获取（或创建）某会话专属的锁"""
        with self._locks_guard:
            if thread_id not in self._locks:
                self._locks[thread_id] = threading.Lock()
            return self._locks[thread_id]

    def _session_file(self, thread_id: str) -> Path:
        # 防止路径注入：只允许字母数字下划线减号
        safe_id = "".join(c for c in thread_id if c.isalnum() or c in "_-")
        if not safe_id:
            safe_id = "default"
        return self.memory_dir / f"{safe_id}.json"

    def save_turn(self, thread_id: str, entry: MemoryEntry) -> None:
        """保存一轮对话到会话记忆文件（线程安全）"""
        # 同一会话串行化，避免并发覆写丢失数据
        with self._lock_for(thread_id):
            path = self._session_file(thread_id)
            history = self.load_session(thread_id)
            history.append(entry.to_dict())
            # 限制最大轮数，保留最近的
            if len(history) > MAX_TURNS_PER_SESSION:
                history = history[-MAX_TURNS_PER_SESSION:]
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(history, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"保存记忆失败: {e}")

    def load_session(self, thread_id: str) -> List[Dict]:
        """加载某会话的全部历史"""
        path = self._session_file(thread_id)
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def get_recent_context(self, thread_id: str, max_entries: int = 3) -> str:
        """获取最近几轮对话作为上下文（供 LLM 使用）"""
        history = self.load_session(thread_id)
        if not history:
            return ""
        recent = history[-max_entries:]
        parts = []
        for h in recent:
            parts.append(f"[{h['timestamp']}] 用户：{h['user_input'][:100]}")
            parts.append(f"明烛：{h['output'][:200]}")
        return "\n".join(parts)

    def list_sessions(self) -> List[Dict]:
        """列出所有会话及其摘要"""
        sessions = []
        for path in sorted(self.memory_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    history = json.load(f)
                if not history:
                    continue
                sessions.append({
                    "session_id": path.stem,
                    "turns": len(history),
                    "last_time": history[-1]["timestamp"],
                    "last_input": history[-1]["user_input"][:50],
                    "file_size": path.stat().st_size,
                })
            except Exception:
                continue
        return sessions

    def clear_session(self, thread_id: str) -> bool:
        """清除某会话记忆"""
        path = self._session_file(thread_id)
        if path.exists():
            path.unlink()
            return True
        return False


# 全局实例
_memory: Optional[LongTermMemory] = None

def get_memory() -> LongTermMemory:
    global _memory
    if _memory is None:
        _memory = LongTermMemory()
    return _memory


def reset_memory() -> None:
    """重置单例（供测试使用，保证测试隔离）"""
    global _memory
    _memory = None


if __name__ == "__main__":
    mem = get_memory()
    # 测试写入
    entry = MemoryEntry(
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        user_input="测试输入",
        output="测试输出",
        personas=[{"name": "乾断"}],
        models=["glm-4-plus"],
    )
    mem.save_turn("test-session", entry)
    print("=== 保存后 ===")
    print(json.dumps(mem.load_session("test-session"), ensure_ascii=False, indent=2))
    print("\n=== 会话列表 ===")
    print(json.dumps(mem.list_sessions(), ensure_ascii=False, indent=2))
    # 清理测试
    mem.clear_session("test-session")
    print("\n=== 清理后 ===")
    print(mem.list_sessions())
