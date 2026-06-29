#!/usr/bin/env python3
"""
明烛认知状态层 v6.0
统一LangGraph state和cognitive_cycle的状态，解决分裂问题。

之前的问题：
- LangGraph有MingZhuState（TypedDict）
- cognitive_cycle有CycleResult/PhaseRecord
- evaluator有QualityScore
- 三者分裂，状态不统一

v6.0：CognitiveState作为唯一状态模型，贯穿全流程。
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class Verdict(str, Enum):
    """裁决类型——evaluator从打分升级为裁决，触发行动"""
    ACCEPT = "accept"    # 通过，输出最终结果
    REVISE = "revise"    # 需修正，退回执行
    REJECT = "reject"    # 彻底拒绝，重新规划


@dataclass
class CognitiveState:
    """统一认知状态——贯穿预见→执行→反思全流程"""

    # 输入
    user_input: str = ""
    intent: str = ""                    # CEO判断的意图

    # 执行
    persona_ids: List[str] = field(default_factory=list)
    persona_results: List[Dict] = field(default_factory=list)
    schedule: Dict = field(default_factory=dict)

    # 对抗（v6.0新增）
    critic_attacks: List[Dict] = field(default_factory=list)   # Critic的攻击点
    generator_defenses: List[Dict] = field(default_factory=list)  # Generator的防御

    # 记忆
    memory_context: str = ""            # 戊藏检索的相关记忆
    knowledge_context: str = ""         # 甲觉学到的外部知识

    # 裁决（v6.0升级：从score到verdict）
    score: float = 0.0
    verdict: Verdict = Verdict.ACCEPT
    critique: str = ""                  # 裁决理由

    # 反思
    reflection: Dict = field(default_factory=dict)  # 三段式复盘
    meta_cognition: Dict = field(default_factory=dict)  # 元元认知评分

    # 元数据
    iteration: int = 0
    final_output: str = ""
    trace: List[Dict] = field(default_factory=list)  # 认知路径追踪

    def add_trace(self, node: str, action: str, detail: str = ""):
        """记录认知路径（可追踪）"""
        self.trace.append({"node": node, "action": action, "detail": detail[:200]})

    def to_dict(self) -> Dict:
        return {
            "user_input": self.user_input[:100],
            "intent": self.intent,
            "persona_ids": self.persona_ids,
            "schedule": self.schedule,
            "score": self.score,
            "verdict": self.verdict.value,
            "critique": self.critique[:200],
            "iteration": self.iteration,
            "trace_count": len(self.trace),
            "final_output_length": len(self.final_output),
        }


def determine_verdict(score: float, has_red_line_violation: bool = False,
                      has_critic_fatal: bool = False) -> Verdict:
    """根据分数和违规情况决定裁决

    - REJECT: 红线违规或Critic发现致命问题
    - REVISE: 分数<60，需修正
    - ACCEPT: 分数>=60，通过
    """
    if has_red_line_violation or has_critic_fatal:
        return Verdict.REJECT
    if score < 60:
        return Verdict.REVISE
    return Verdict.ACCEPT
