#!/usr/bin/env python3
"""
明烛智能调度策略 v3.4
参考顶尖企业工作流系统，动态决定并行/顺序/混合调度。

调度策略：
- PARALLEL（并行）：独立任务同时执行。如：多角度分析同一问题（乾断+巽风+兑泽各独立分析）
- SEQUENTIAL（顺序）：有依赖关系的任务接力。如：巽风调研→震造实现→艮守审查
- MIXED（混合）：先并行收集，再顺序加工。如：巽风+兑泽并行调研→乾断综合决策→艮守审查
- ITERATIVE（迭代）：需要反复打磨。如：震造实现→坎观审查→震造修正（循环直到满意）

决策依据（明烛主人格用LLM判断）：
1. 任务是否有依赖关系（有→顺序）
2. 各人格输出是否独立（独立→并行）
3. 是否需要多轮修正（需要→迭代）
4. 是否部分独立部分依赖（→混合）
"""
import json
import logging
from typing import Dict, List, Any
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class ScheduleStrategy(str, Enum):
    """调度策略"""
    PARALLEL = "parallel"      # 全并行
    SEQUENTIAL = "sequential"  # 全顺序
    MIXED = "mixed"            # 混合（先并行后顺序）
    ITERATIVE = "iterative"    # 迭代（循环修正）
    DISCUSS = "discuss"        # v3.9: 并行执行+内部讨论轮+汇总


@dataclass
class SchedulePlan:
    """调度计划"""
    strategy: ScheduleStrategy
    # 执行分组：每组内并行，组间顺序
    # 例：[["xun_feng","dui_ze"], ["qian_duan"], ["gen_shou","kan_guan"]]
    # 表示巽风兑泽并行→乾断→艮守坎观并行
    groups: List[List[str]] = field(default_factory=list)
    # 是否需要迭代修正
    needs_iteration: bool = False
    max_iterations: int = 1
    reason: str = ""           # 决策理由

    def to_dict(self) -> Dict:
        return {
            "strategy": self.strategy.value,
            "groups": self.groups,
            "needs_iteration": self.needs_iteration,
            "max_iterations": self.max_iterations,
            "reason": self.reason,
        }


def plan_schedule(persona_ids: List[str], user_input: str, router) -> SchedulePlan:
    """让明烛主人格用LLM决定调度策略

    Args:
        persona_ids: 需要调用的人格ID列表
        user_input: 用户输入
        router: LLM路由器

    Returns:
        SchedulePlan: 调度计划
    """
    from .llm_backends import Scene

    # 只有1个人格时无需复杂调度
    if len(persona_ids) <= 1:
        return SchedulePlan(
            strategy=ScheduleStrategy.SEQUENTIAL,
            groups=[[persona_ids[0]] if persona_ids else []],
            reason="单人格，直接执行",
        )

    # 用LLM判断调度策略
    persona_names = {
        "qian_duan": "乾断(决策)", "xun_feng": "巽风(调研)", "zhen_zao": "震造(实现)",
        "gen_shou": "艮守(安全)", "kun_zai": "坤载(管理)", "kan_guan": "坎观(观察)",
        "li_ming": "离明(表达)", "dui_ze": "兑泽(创意)",
    }
    personas_str = ", ".join(persona_names.get(p, p) for p in persona_ids)

    prompt = f"""你是明烛CEO，负责调度子人格。根据任务特征决定最佳协作模式。

【需调用的人格】{personas_str}
【用户任务】{user_input}

【协作模式】（选一个，参考世界级企业的工作方式）
- parallel: 各人格独立分析同一问题，互不依赖。像企业里多个部门各自出具报告。适合：多角度评估、对比分析
- sequential: 有依赖关系，需接力。像企业流水线。适合：调研→实现→审查、需求→设计→开发
- mixed: 部分独立部分依赖。像企业项目里先并行收集信息再顺序决策。适合：先调研+创意并行，再决策+审查顺序
- iterative: 需要反复修正。像企业的PDCA循环。适合：实现→审查→修正、写→审→改
- discuss: 各人格先并行独立分析，然后互相讨论质疑，最后汇总。像企业的高管会议。适合：复杂决策、争议性问题、需要多视角深度探讨

【示例】
任务"对比Redis和Memcached" → parallel（多角度独立评估）
任务"调研JWT然后实现认证" → sequential（有依赖）
任务"从技术安全商业角度讨论微服务" → discuss（需要多视角讨论）
任务"写代码然后审查修复" → iterative（需要循环修正）

【输出格式】严格JSON：
{{"strategy":"discuss","groups":[["qian_duan","gen_shou","zhen_zao"]],"needs_iteration":false,"reason":"需要多视角讨论"}}"""

    try:
        resp = router.generate(prompt, scene=Scene.ROUTING, max_tokens=200)
        if resp.ok:
            # 解析JSON
            text = resp.content
            idx = text.find('{')
            end = text.rfind('}')
            if idx >= 0 and end > idx:
                data = json.loads(text[idx:end+1])
                strategy = ScheduleStrategy(data.get("strategy", "sequential"))
                groups = data.get("groups", [])
                # 验证groups里的人格都在persona_ids里
                valid_groups = []
                for g in groups:
                    valid_g = [p for p in g if p in persona_ids]
                    if valid_g:
                        valid_groups.append(valid_g)
                # 确保所有人格都被调度到
                scheduled = set(p for g in valid_groups for p in g)
                missing = set(persona_ids) - scheduled
                for m in missing:
                    valid_groups.append([m])

                return SchedulePlan(
                    strategy=strategy,
                    groups=valid_groups,
                    needs_iteration=data.get("needs_iteration", False),
                    max_iterations=data.get("max_iterations", 1) if data.get("needs_iteration") else 1,
                    reason=data.get("reason", ""),
                )
    except Exception as e:
        logger.debug(f"LLM调度决策失败，降级为顺序: {e}")

    # 降级：顺序执行
    return SchedulePlan(
        strategy=ScheduleStrategy.SEQUENTIAL,
        groups=[[p] for p in persona_ids],
        reason="LLM调度决策失败，降级顺序执行",
    )


if __name__ == "__main__":
    # 测试（无LLM时降级）
    class MockRouter:
        def generate(self, prompt, scene=None, max_tokens=100):
            class R:
                ok = False
                content = ""
            return R()

    plan = plan_schedule(["xun_feng", "zhen_zao", "gen_shou"], "调研JWT然后实现然后审查", MockRouter())
    print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
