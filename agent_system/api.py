#!/usr/bin/env python3
"""
明烛统一入口 v3.2
解决"该用 MingZhu.run() 还是 MingZhuGraph.invoke()"的困惑。

推荐用法：
    from agent_system.api import chat, chat_with_details

    # 简单用法
    reply = chat("帮我分析这段代码")

    # 带会话记忆 + 详细结果
    result = chat_with_details("帮我分析", session_id="user-1")
    print(result["output"])        # 最终回复
    print(result["observer"])      # 坎观观察报告
    print(result["personas"])      # 各人格输出

v3.2 新增：
- 长期记忆持久化（memory_store/<session_id>.json，重启不丢失）
- 成本监控（cost_log.json，可查累计费用）
- 历史会话查询
"""
import time as _time
from typing import Dict, Any, Optional, List
from .langgraph_engine import MingZhuGraph

# 全局图实例（复用，避免重复构建）
_graph: Optional[MingZhuGraph] = None


def _get_graph() -> MingZhuGraph:
    global _graph
    if _graph is None:
        _graph = MingZhuGraph()
    return _graph


def chat(user_input: str, session_id: str = "default") -> str:
    """明烛统一对话接口（推荐）

    Args:
        user_input: 用户输入
        session_id: 会话ID，相同ID自动保持多轮记忆 + 持久化到文件

    Returns:
        明烛的最终回复字符串
    """
    result = chat_with_details(user_input, session_id)
    return result["output"]


def chat_with_details(user_input: str, session_id: str = "default") -> Dict[str, Any]:
    """明烛统一对话接口（带完整细节，自动持久化记忆）

    Returns:
        {
            "output": str,           # 最终回复
            "personas": list,        # 各人格的输出
            "routing": str,          # 路由说明
            "routing_method": str,   # keyword/llm
            "conflicts": list,       # 冲突
            "vetoed": bool,          # 是否否决
            "observer": str,         # 坎观观察报告
            "models": list,          # 使用的模型
            "session_id": str,       # 会话ID
            "latency_ms": float,     # 总耗时
        }
    """
    from .memory import get_memory, MemoryEntry

    graph = _get_graph()
    start = _time.time()
    result = graph.invoke(user_input, thread_id=session_id)
    latency = (_time.time() - start) * 1000

    personas = result.get("persona_results", [])
    output = {
        "output": result.get("final_output", ""),
        "personas": [
            {
                "name": p.get("name", ""),
                "icon": p.get("icon", ""),
                "content": p.get("content", ""),
                "confidence": p.get("confidence", ""),
                "vetoed": p.get("vetoed", False),
                "error": p.get("error"),
                "model": p.get("model", ""),
                "backend": p.get("backend", ""),
            }
            for p in personas
        ],
        "routing": result.get("routing_reason", ""),
        "routing_method": result.get("routing_method", ""),
        "conflicts": result.get("conflicts", []),
        "vetoed": result.get("vetoed", False),
        "observer": result.get("observer_report", ""),
        "models": list(set(p.get("model", "") for p in personas if p.get("model"))),
        "session_id": session_id,
        "latency_ms": round(latency, 1),
    }

    # v3.2: 持久化到长期记忆
    try:
        entry = MemoryEntry(
            timestamp=_time.strftime("%Y-%m-%d %H:%M:%S"),
            user_input=user_input,
            output=output["output"],
            personas=[{"name": p["name"], "model": p.get("model", "")} for p in output["personas"]],
            models=output["models"],
            observer=output["observer"],
            latency_ms=round(latency, 1),
        )
        get_memory().save_turn(session_id, entry)
    except Exception:
        pass  # 记忆失败不影响主流程

    return output


def get_history(session_id: str) -> List[Dict]:
    """获取某会话的历史对话（从持久化记忆读取）"""
    from .memory import get_memory
    return get_memory().load_session(session_id)


def list_sessions() -> List[Dict]:
    """列出所有历史会话"""
    from .memory import get_memory
    return get_memory().list_sessions()


def clear_session(session_id: str) -> bool:
    """清除某会话的记忆"""
    from .memory import get_memory
    return get_memory().clear_session(session_id)


def cost_summary() -> Dict:
    """获取成本统计（累计费用、按后端/场景分布）"""
    from .cost_monitor import get_monitor
    return get_monitor().summary()


def reset_session(session_id: str = "default"):
    """重置内存中的图状态（不影响已持久化的文件记忆）"""
    global _graph
    _graph = None


if __name__ == "__main__":
    print("=== 明烛统一入口测试 ===\n")

    # 简单对话
    print(">>> chat() 简单对话")
    reply = chat("用一句话介绍你自己")
    print(f"回复：{reply[:200]}\n")

    # 带细节
    print(">>> chat_with_details() 带细节")
    result = chat_with_details("帮我评估这个方案的利弊：用微服务架构做初创产品", session_id="detail-test")
    print(f"路由方法：{result['routing_method']}")
    print(f"调用人格：{[p['name'] for p in result['personas']]}")
    print(f"使用模型：{result['models']}")
    print(f"耗时：{result['latency_ms']}ms")
    print(f"观察报告：{result['observer'][:200]}")
    print(f"最终回复：{result['output'][:200]}")

    # 历史会话
    print(f"\n>>> 历史会话：{list_sessions()}")

    # 成本
    print(f"\n>>> 成本统计：{cost_summary()}")
