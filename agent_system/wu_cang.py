#!/usr/bin/env python3
"""
戊藏 · 记忆官（v4.3）

命名：时柱戊藏（伤官），阳土主储藏固化。
职责：被明烛(CEO)调用时才工作，不常驻。
  1. 检索：对话前检索相关历史记忆，注入context
  2. 遗忘：超过阈值时清理低价值记忆
  3. 去重：相似度高的记忆合并

设计原则：明烛判断"需要回忆吗"才调用戊藏，不需要就休息（不耗token）。
"""
import json
import time
import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class WuCang:
    """戊藏·记忆官"""

    def __init__(self):
        from .memory import get_memory
        from .vector_search import get_vector_search
        self.memory = get_memory()
        self.searcher = get_vector_search()
        self._max_per_session = 50  # 遗忘阈值

    def recall(self, query: str, limit: int = 3) -> str:
        """被明烛调用：检索相关记忆，返回注入文本"""
        results = self.searcher.search(query, limit=limit)
        if not results:
            return ""
        relevant = [r for r in results if r.get("similarity", 0) > 0.4]
        if not relevant:
            return ""
        parts = ["【戊藏·相关记忆】"]
        for r in relevant[:3]:
            parts.append(
                f"- [{r.get('session_id','')}] {r.get('user_input','')[:60]}\n"
                f"  答：{r.get('output','')[:100]}"
            )
        return "\n".join(parts)

    def forget(self) -> Dict:
        """遗忘机制：清理超过阈值的记忆（对话历史+进化经验）"""
        cleaned = 0
        # 1. 对话历史：每会话超过阈值保留最近N条
        for session_file in self.memory.memory_dir.glob("*.json"):
            try:
                history = json.loads(session_file.read_text(encoding="utf-8"))
                if len(history) <= self._max_per_session:
                    continue
                old_count = len(history)
                history = history[-self._max_per_session:]
                session_file.write_text(
                    json.dumps(history, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
                cleaned += old_count - len(history)
            except Exception:
                continue
        # 2. 进化经验：超过500条保留最近500条（与evolution.py一致）
        try:
            from .evolution import EVOLUTION_DIR
            exp_file = EVOLUTION_DIR / "experiences.json"
            if exp_file.exists():
                exps = json.loads(exp_file.read_text(encoding="utf-8"))
                if len(exps) > 500:
                    exps = exps[-500:]
                    exp_file.write_text(
                        json.dumps(exps, ensure_ascii=False, indent=2),
                        encoding="utf-8"
                    )
                    cleaned += len(exps) - 500
        except Exception:
            pass
        return {"cleaned": cleaned, "threshold": self._max_per_session}

    def get_status(self) -> Dict:
        sessions = self.memory.list_sessions()
        total = sum(s.get("turns", 0) for s in sessions)
        return {
            "total_sessions": len(sessions),
            "total_memories": total,
            "forget_threshold": self._max_per_session,
        }


_officer: Optional[WuCang] = None

def get_wu_cang() -> WuCang:
    global _officer
    if _officer is None:
        _officer = WuCang()
    return _officer


def reset_wu_cang() -> None:
    """重置单例（供测试使用，保证测试隔离）"""
    global _officer
    _officer = None
