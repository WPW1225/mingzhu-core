#!/usr/bin/env python3
"""
明烛成本监控 v3.2
记录每次 LLM 调用的 token 用量和费用，按后端/场景统计。

定价（2026 估算，单位：元/千token）：
- 智谱 glm-4-plus: 输入 0.05, 输出 0.05
- DeepSeek deepseek-chat: 输入 0.001, 输出 0.002
- DeepSeek deepseek-v4-flash: 输入 0.0005, 输出 0.001

存储：agent_system/cost_log.json
"""
import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

COST_LOG_FILE = Path(__file__).parent.parent / "cost_log.json"

# 定价表（元/千token）
PRICING = {
    "glm-4-plus": {"input": 0.05, "output": 0.05},
    "glm-4": {"input": 0.1, "output": 0.1},
    "glm-4-flash": {"input": 0.01, "output": 0.01},
    "deepseek-chat": {"input": 0.001, "output": 0.002},
    "deepseek-v4-flash": {"input": 0.0005, "output": 0.001},
    "deepseek-reasoner": {"input": 0.004, "output": 0.016},
}


def estimate_cost(model: str, usage: Dict) -> float:
    """根据模型和 usage 估算费用（元）"""
    if not usage or model not in PRICING:
        return 0.0
    price = PRICING[model]
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)
    cost = (input_tokens / 1000) * price["input"] + (output_tokens / 1000) * price["output"]
    return round(cost, 6)


@dataclass
class CostEntry:
    """单次调用成本记录"""
    timestamp: str
    backend: str
    model: str
    scene: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_yuan: float = 0.0
    latency_ms: float = 0.0
    ok: bool = True

    def to_dict(self) -> Dict:
        return asdict(self)


class CostMonitor:
    """成本监控器"""

    def __init__(self, log_file: Path = None):
        self.log_file = log_file or COST_LOG_FILE

    def record(self, backend: str, model: str, scene: str,
               usage: Dict, latency_ms: float, ok: bool = True) -> CostEntry:
        """记录一次调用"""
        entry = CostEntry(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            backend=backend, model=model, scene=scene,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            cost_yuan=estimate_cost(model, usage),
            latency_ms=round(latency_ms, 1),
            ok=ok,
        )
        self._append_log(entry)
        return entry

    def _append_log(self, entry: CostEntry):
        """追加到日志文件"""
        try:
            logs = []
            if self.log_file.exists():
                with open(self.log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            logs.append(entry.to_dict())
            # 限制日志大小，保留最近 1000 条
            if len(logs) > 1000:
                logs = logs[-1000:]
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"成本日志写入失败: {e}")

    def summary(self) -> Dict:
        """获取成本摘要"""
        logs = self._load_all()
        if not logs:
            return {"total_calls": 0, "total_cost": 0, "total_tokens": 0}

        total_cost = sum(l["cost_yuan"] for l in logs)
        total_tokens = sum(l["total_tokens"] for l in logs)

        # 按后端统计
        by_backend = {}
        for l in logs:
            b = l["backend"]
            if b not in by_backend:
                by_backend[b] = {"calls": 0, "cost": 0, "tokens": 0}
            by_backend[b]["calls"] += 1
            by_backend[b]["cost"] += l["cost_yuan"]
            by_backend[b]["tokens"] += l["total_tokens"]

        # 按场景统计
        by_scene = {}
        for l in logs:
            s = l["scene"]
            if s not in by_scene:
                by_scene[s] = {"calls": 0, "cost": 0}
            by_scene[s]["calls"] += 1
            by_scene[s]["cost"] += l["cost_yuan"]

        return {
            "total_calls": len(logs),
            "total_cost": round(total_cost, 4),
            "total_tokens": total_tokens,
            "by_backend": {k: {**v, "cost": round(v["cost"], 4)} for k, v in by_backend.items()},
            "by_scene": {k: {**v, "cost": round(v["cost"], 4)} for k, v in by_scene.items()},
            "pricing": PRICING,
        }

    def _load_all(self) -> List[Dict]:
        if not self.log_file.exists():
            return []
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def clear(self):
        """清空日志"""
        if self.log_file.exists():
            self.log_file.unlink()


# 全局实例
_monitor: Optional[CostMonitor] = None

def get_monitor() -> CostMonitor:
    global _monitor
    if _monitor is None:
        _monitor = CostMonitor()
    return _monitor


if __name__ == "__main__":
    mon = get_monitor()
    # 测试记录
    mon.record("zhipu", "glm-4-plus", "analysis",
               {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}, 652.0)
    mon.record("deepseek", "deepseek-chat", "simple",
               {"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80}, 1800.0)
    print("=== 成本摘要 ===")
    print(json.dumps(mon.summary(), ensure_ascii=False, indent=2))
    mon.clear()
