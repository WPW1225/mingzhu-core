#!/usr/bin/env python3
"""
明烛执行策略双轨制 v4.4
母框架核心：提供两种执行策略供子项目选择。

策略A（快速响应）：直线流水线，成本低时间确定。适合报告生成、数据查询。
策略B（探索研究）：ReAct循环(Think→Act→Observe)，LLM自主调工具。适合编程、调研。
"""
import logging
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)


class ExecutionStrategyType(str, Enum):
    PIPELINE = "pipeline"    # 策略A：直线流水线
    REACT = "react"          # 策略B：ReAct循环


class ExecutionStrategy(ABC):
    """执行策略抽象接口"""

    @abstractmethod
    def execute(self, user_input: str, context: str, router) -> Dict:
        pass

    @abstractmethod
    def get_type(self) -> ExecutionStrategyType:
        pass


class PipelineStrategy(ExecutionStrategy):
    """策略A：直线流水线（快速响应）"""

    def __init__(self, graph):
        self.graph = graph

    def get_type(self) -> ExecutionStrategyType:
        return ExecutionStrategyType.PIPELINE

    def execute(self, user_input: str, context: str, router) -> Dict:
        result = self.graph.invoke(user_input, thread_id="pipeline")
        return {
            "output": result.get("final_output", ""),
            "strategy": "pipeline",
            "personas": result.get("persona_results", []),
        }


class ReactStrategy(ExecutionStrategy):
    """策略B：ReAct循环（探索研究）"""

    def __init__(self, router, tools_registry=None, max_iterations: int = 5):
        self.router = router
        self.max_iterations = max_iterations
        if tools_registry is None:
            from .tools import get_registry
            tools_registry = get_registry()
        self.tools = tools_registry

    def get_type(self) -> ExecutionStrategyType:
        return ExecutionStrategyType.REACT

    def execute(self, user_input: str, context: str, router) -> Dict:
        from .llm_backends import Scene
        observations = []
        final_answer = ""

        for i in range(self.max_iterations):
            think_prompt = self._build_think_prompt(user_input, context, observations)
            resp = router.generate(think_prompt, scene=Scene.ANALYSIS, max_tokens=300)
            if not resp.ok:
                break
            decision = self._parse_decision(resp.content)

            if decision.get("action") == "final":
                final_answer = decision.get("answer", resp.content)
                break
            elif decision.get("action") == "tool":
                tool_name = decision.get("tool", "")
                tool_args = decision.get("args", {})
                result = self.tools.call(tool_name, **tool_args)
                observations.append({
                    "iteration": i + 1,
                    "tool": tool_name,
                    "result": result.output[:200] if result.success else result.error,
                })
            else:
                final_answer = resp.content
                break

        if not final_answer and observations:
            summary_prompt = f"基于以下观察，回答问题：{user_input}\n观察：{observations}"
            resp = router.generate(summary_prompt, scene=Scene.ANALYSIS)
            final_answer = resp.content if resp.ok else "探索未得出结论"

        return {
            "output": final_answer,
            "strategy": "react",
            "iterations": len(observations),
            "observations": observations,
        }

    def _build_think_prompt(self, user_input, context, observations):
        obs_text = "\n".join(f"  轮{o['iteration']}: {o['tool']}→{o['result']}"
                             for o in observations) if observations else "无"
        return f"""任务：{user_input}
上下文：{context or '无'}
已有观察：{obs_text}

决定下一步：
- 如果需要调工具，返回JSON：{{"action":"tool","tool":"web_search","args":{{"query":"xxx"}}}}
- 如果已有答案，返回JSON：{{"action":"final","answer":"最终答案"}}

可用工具：web_search, calculator, code_execute, file_read
只返回JSON："""

    def _parse_decision(self, text: str) -> Dict:
        import json, re
        text = re.sub(r'```(?:json)?\s*', '', text).replace('```', '')
        idx = text.find('{')
        end = text.find('}', idx)
        if idx >= 0 and end > idx:
            try:
                return json.loads(text[idx:end+1])
            except Exception:
                pass
        return {"action": "unknown"}


def select_strategy(task_type: str) -> ExecutionStrategyType:
    """根据任务类型自动选择策略"""
    pipeline_keywords = ["报告", "总结", "查询", "分析", "评估", "生成"]
    react_keywords = ["搜索", "调研", "实现", "调试", "解决", "探索", "研究"]

    for kw in react_keywords:
        if kw in task_type:
            return ExecutionStrategyType.REACT
    for kw in pipeline_keywords:
        if kw in task_type:
            return ExecutionStrategyType.PIPELINE
    return ExecutionStrategyType.PIPELINE


if __name__ == "__main__":
    for t in ["生成电商报告", "搜索LangGraph最新特性", "分析数据", "调试代码bug"]:
        print(f"  {t} → {select_strategy(t).value}")
