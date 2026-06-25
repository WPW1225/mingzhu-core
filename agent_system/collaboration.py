#!/usr/bin/env python3
"""
明烛多人格协作协议
定义多Agent协作的通信协议、冲突解决机制、观察者机制。
解决风险：协作流程未定义、缺少观察者角色。
"""
import time
import json
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

from .config_loader import config


class CollaborationPhase(Enum):
    """协作阶段"""
    RESEARCH = "research"       # 调研（巽风）
    CREATIVE = "creative"       # 创意（兑泽）
    DECISION = "decision"       # 决断（乾断）
    BUILD = "build"             # 构建（震造）
    REVIEW = "review"           # 审查（艮守）
    OBSERVE = "observe"         # 观察（坎观）—— 贯穿全程
    COMMUNICATE = "communicate" # 沟通（离明）—— 最终输出
    MANAGE = "manage"           # 管理（坤载）—— 协调全程


@dataclass
class CollaborationMessage:
    """协作消息"""
    from_persona: str
    to_persona: str
    phase: CollaborationPhase
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)


@dataclass
class CollaborationResult:
    """协作结果"""
    task: str
    phases: List[Dict] = field(default_factory=list)        # 各阶段结果
    messages: List[Dict] = field(default_factory=list)      # 消息记录
    final_output: str = ""                                   # 最终输出
    observer_report: str = ""                                # 观察者报告
    quality_score: float = 0.0                               # 质量评分
    success: bool = True
    error: str = ""
    duration: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "task": self.task,
            "phases": self.phases,
            "message_count": len(self.messages),
            "final_output": self.final_output,
            "observer_report": self.observer_report,
            "quality_score": round(self.quality_score, 1),
            "success": self.success,
            "error": self.error,
            "duration": round(self.duration, 2),
        }


class CollaborationProtocol:
    """
    多人格协作协议

    核心原则：
    1. 坎观（观察者）必须贯穿全程，独立审查
    2. 最多3个人格并行，控制Token消耗
    3. 冲突由坤载协调，无法解决由坎观仲裁
    4. 每阶段输出结构化结果，传递给下一阶段
    """

    # 标准协作流程
    STANDARD_PIPELINE = [
        (CollaborationPhase.MANAGE, "kun_zai", "任务分解和计划"),
        (CollaborationPhase.RESEARCH, "xun_feng", "调研和信息收集"),
        (CollaborationPhase.CREATIVE, "dui_ze", "创意发散"),
        (CollaborationPhase.DECISION, "qian_duan", "方案决断"),
        (CollaborationPhase.BUILD, "zhen_zao", "代码实现"),
        (CollaborationPhase.REVIEW, "gen_shou", "安全审查"),
        (CollaborationPhase.COMMUNICATE, "li_ming", "表达输出"),
        (CollaborationPhase.OBSERVE, "kan_guan", "最终审查"),
    ]

    # 并行限制
    MAX_PARALLEL = 3
    # Token预算
    TOKEN_BUDGET = {
        "kun_zai": 1500,
        "xun_feng": 2000,
        "dui_ze": 1500,
        "qian_duan": 1500,
        "zhen_zao": 3000,
        "gen_shou": 1000,
        "li_ming": 1500,
        "kan_guan": 2000,
    }

    def __init__(self, llm_caller: Optional[Callable] = None):
        """
        Args:
            llm_caller: LLM调用函数 (prompt: str, system: str) -> str
        """
        self.llm_caller = llm_caller
        self.messages: List[CollaborationMessage] = []

    def execute(self, task: str, pipeline: Optional[List] = None) -> CollaborationResult:
        """执行多人格协作任务"""
        start_time = time.time()
        result = CollaborationResult(task=task)
        pipeline = pipeline or self.STANDARD_PIPELINE

        try:
            context = {"task": task, "previous_outputs": {}}

            for phase, persona_id, description in pipeline:
                # 跳过不可用的阶段
                if not self.llm_caller:
                    result.phases.append({
                        "phase": phase.value,
                        "persona": persona_id,
                        "description": description,
                        "output": f"[模拟] {description}（需接入LLM）",
                        "skipped": True,
                    })
                    continue

                # 执行阶段
                phase_output = self._execute_phase(
                    phase, persona_id, description, context
                )

                result.phases.append({
                    "phase": phase.value,
                    "persona": persona_id,
                    "description": description,
                    "output": phase_output,
                    "skipped": False,
                })

                # 记录消息
                self.messages.append(CollaborationMessage(
                    from_persona=persona_id,
                    to_persona="next" if phase != CollaborationPhase.OBSERVE else "final",
                    phase=phase,
                    content=phase_output,
                ))

                # 更新上下文
                context["previous_outputs"][phase.value] = phase_output

            # 最终输出（取沟通阶段或观察阶段的输出）
            if result.phases:
                for p in reversed(result.phases):
                    if not p.get("skipped", False) and p["output"]:
                        result.final_output = p["output"]
                        break

            # 观察者报告
            if self.llm_caller:
                result.observer_report = self._generate_observer_report(result)
            else:
                result.observer_report = "[模拟] 观察者报告（需接入LLM）"

        except Exception as e:
            result.success = False
            result.error = str(e)

        result.duration = time.time() - start_time
        result.messages = [m.__dict__ for m in self.messages]
        return result

    def _execute_phase(self, phase: CollaborationPhase, persona_id: str,
                       description: str, context: Dict) -> str:
        """执行单个协作阶段"""
        persona_config = config.get_persona(persona_id)
        if not persona_config:
            return f"[错误] 人格配置 {persona_id} 未找到"

        # 构建提示词
        system_prompt = config.get_persona_prompt(persona_id)
        task_context = self._build_context(context, phase)

        user_prompt = f"""任务：{context['task']}
当前阶段：{description}
前置上下文：
{task_context}

请以{persona_config['meta']['name']}人格执行此阶段任务。"""

        # 调用LLM
        response = self.llm_caller(user_prompt, system_prompt)
        return response

    def _build_context(self, context: Dict, current_phase: CollaborationPhase) -> str:
        """构建上下文（只传递相关部分，控制Token）"""
        parts = []
        for phase, output in context["previous_outputs"].items():
            # 截断过长的输出
            truncated = output[:500] + "..." if len(output) > 500 else output
            parts.append(f"[{phase}] {truncated}")
        return "\n\n".join(parts) if parts else "（无前置上下文）"

    def _generate_observer_report(self, result: CollaborationResult) -> str:
        """生成观察者报告"""
        phases_summary = "\n".join(
            f"  - {p['phase']}({p['persona']}): {p['description']}"
            for p in result.phases
        )

        observer_prompt = f"""你是坎观（观察者），请审查以下多人格协作过程：

任务：{result.task}
协作阶段：
{phases_summary}

请从观察者角度提供：
1. 调度决策质量评估
2. 各阶段衔接是否顺畅
3. 潜在盲点或偏差
4. 改进建议

观察报告："""

        observer_system = config.get_persona_prompt("kan_guan")
        return self.llm_caller(observer_prompt, observer_system)

    def resolve_conflict(self, persona_a: str, persona_b: str,
                         conflict: str) -> str:
        """解决人格间冲突"""
        # 第一步：坤载协调
        if self.llm_caller:
            manage_prompt = f"""人格 {persona_a} 和 {persona_b} 产生冲突：
{conflict}

作为坤载（管理者），请协调此冲突，给出解决方案。"""
            manage_system = config.get_persona_prompt("kun_zai")
            resolution = self.llm_caller(manage_prompt, manage_system)

            # 第二步：如果坤载无法解决，坎观仲裁
            if "无法解决" in resolution or "需要仲裁" in resolution:
                observe_prompt = f"""坤载无法解决以下冲突，请作为坎观（观察者）仲裁：
{conflict}

坤载的协调建议：{resolution}

请给出最终仲裁。"""
                observe_system = config.get_persona_prompt("kan_guan")
                resolution = self.llm_caller(observe_prompt, observe_system)

            return resolution
        return "[模拟] 冲突解决（需接入LLM）"


if __name__ == "__main__":
    # 测试（无LLM模式）
    protocol = CollaborationProtocol()
    result = protocol.execute("设计一个用户认证系统")
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
