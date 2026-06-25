#!/usr/bin/env python3
"""
明烛统一入口 v3.1
解决"该用 MingZhu.run() 还是 MingZhuGraph.invoke()"的困惑。

推荐用法（v3.1+）：
    from agent_system.api import chat, chat_with_details

    # 简单用法
    reply = chat("帮我分析这段代码")

    # 带会话记忆 + 详细结果
    result = chat_with_details("帮我分析", session_id="user-1")
    print(result["output"])        # 最终回复
    print(result["observer"])      # 坎观观察报告
    print(result["personas"])      # 各人格输出

兼容旧用法：
    from agent_system import MingZhu      # v1/v2 接口（无LLM）
    from agent_system.langgraph_engine import MingZhuGraph  # v3.0 接口
"""
from typing import Dict, Any, Optional
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
        session_id: 会话ID，相同ID自动保持多轮记忆

    Returns:
        明烛的最终回复字符串

    示例：
        >>> chat("你好")
        '你好！我是明烛...'
        >>> chat("刚才说的再展开", session_id="s1")  # 记忆上一轮
    """
    graph = _get_graph()
    result = graph.invoke(user_input, thread_id=session_id)
    return result.get("final_output", "")


def chat_with_details(user_input: str, session_id: str = "default") -> Dict[str, Any]:
    """明烛统一对话接口（带完整细节，用于审计和调试）

    Returns:
        {
            "output": str,           # 最终回复
            "personas": list,        # 各人格的输出
            "routing": str,          # 路由说明
            "routing_method": str,   # 路由方法（keyword/llm）
            "conflicts": list,       # 冲突列表
            "vetoed": bool,          # 是否被否决
            "observer": str,         # 坎观观察报告
            "models": list,          # 使用的模型列表
        }
    """
    graph = _get_graph()
    result = graph.invoke(user_input, thread_id=session_id)

    personas = result.get("persona_results", [])
    return {
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
    }


def reset_session(session_id: str = "default"):
    """重置某个会话的记忆"""
    # MemorySaver 是内存态，重置全局图即可清空所有会话
    # 未来落盘后改为按 session_id 精准清除
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
    print(f"冲突：{result['conflicts']}")
    print(f"观察报告：{result['observer'][:200]}")
    print(f"最终回复：{result['output'][:200]}")
