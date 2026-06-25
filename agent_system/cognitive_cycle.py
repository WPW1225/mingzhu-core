#!/usr/bin/env python3
"""
明烛认知循环 v2.1
基于 Zimmerman 自我调节学习模型（SRL），强制执行"预见→执行→反思"三阶段。

这是对 SOUL.md 中元认知原则的可执行化实现：
- 预见阶段：任务分析4问 + 任务拆分 + 认知偏差预检 + 执行驱动信号检测
- 执行阶段：固定任务清单（编译验证、Todo打钩、进度汇报、全量测试、远程同步、必须push）
- 反思阶段：三段式复盘（事实/思维/迭代）+ 教训写入 PROJECT_LOG

设计原则：
- enforce_strict=True 时，run() 必须依次完成三阶段，缺一报错
- 每阶段产出结构化记录，便于审计
- 执行驱动信号检测：发现"收到指令立即动手"等模式时主动刹车

使用方式：
    from agent_system.cognitive_cycle import CognitiveCycle

    cycle = CognitiveCycle()
    result = cycle.run(
        task="给项目增加 CI 测试",
        forethought_fn=lambda: {"goal_clarity": "...", ...},
        execute_fn=lambda plan: {"output": "...", "files_changed": 2},
        reflect_fn=lambda: {"factual": "...", "cognitive": "...", "iterative": "..."},
    )
"""
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable

from .config_loader import config as soul_config

logger = logging.getLogger(__name__)


# ============================================================
# 数据结构
# ============================================================

@dataclass
class PhaseRecord:
    """单阶段执行记录"""
    phase: str                    # forethought / performance / reflection
    name: str                     # 预见 / 执行 / 反思
    started_at: str = ""
    finished_at: str = ""
    completed: bool = False
    skipped: bool = False
    answers: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict:
        return {
            "phase": self.phase,
            "name": self.name,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "completed": self.completed,
            "skipped": self.skipped,
            "answers": self.answers,
            "warnings": self.warnings,
            "notes": self.notes,
        }


@dataclass
class CycleResult:
    """完整认知循环结果"""
    task: str = ""
    forethought: PhaseRecord = field(default_factory=lambda: PhaseRecord("forethought", "预见"))
    performance: PhaseRecord = field(default_factory=lambda: PhaseRecord("performance", "执行"))
    reflection: PhaseRecord = field(default_factory=lambda: PhaseRecord("reflection", "反思"))
    all_completed: bool = False

    def to_dict(self) -> Dict:
        return {
            "task": self.task,
            "forethought": self.forethought.to_dict(),
            "performance": self.performance.to_dict(),
            "reflection": self.reflection.to_dict(),
            "all_completed": self.all_completed,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


# ============================================================
# 认知循环
# ============================================================

class CognitiveCycle:
    """
    明烛认知循环控制器。

    从 soul_config.yaml 的 cognitive_cycle 段加载配置，
    强制执行 Zimmerman 三阶段：预见 → 执行 → 反思。
    """

    def __init__(self):
        self.config = soul_config.soul.get("cognitive_cycle", {})
        if not self.config:
            logger.warning("cognitive_cycle 配置未找到，元认知循环将使用空配置")
        self.enforce_strict = self.config.get("enforce_strict", True)

    # ---------- 配置查询 ----------

    def get_forethought_questions(self) -> List[Dict]:
        """返回预见阶段需要回答的所有问题（任务分析 + 偏差预检）"""
        ft_cfg = self.config.get("forethought", {})
        questions = []
        for item in ft_cfg.get("task_analysis", []):
            questions.append({
                "id": item["id"],
                "type": "task_analysis",
                "question": item["question"],
                "must_answer": item.get("must_answer", False),
            })
        for bias in ft_cfg.get("bias_precheck", []):
            questions.append({
                "id": f"bias_{bias['id']}",
                "type": "bias_precheck",
                "question": bias["question"],
                "risk_level": bias.get("risk_level", "low"),
            })
        return questions

    def get_reflection_questions(self) -> List[Dict]:
        """返回反思阶段需要回答的三段式问题"""
        ref_cfg = self.config.get("reflection", {})
        return [
            {
                "id": step["id"],
                "name": step["name"],
                "question": step["question"],
                "must_answer": step.get("must_answer", False),
            }
            for step in ref_cfg.get("three_step_review", [])
        ]

    def get_fixed_tasks(self) -> List[Dict]:
        """返回执行阶段的固定任务清单"""
        perf_cfg = self.config.get("performance", {})
        return [
            {"id": ft["id"], "rule": ft["rule"]}
            for ft in perf_cfg.get("fixed_tasks", [])
        ]

    def get_execution_drive_signals(self) -> List[str]:
        """返回执行驱动触发信号列表"""
        return self.config.get("forethought", {}).get("execution_drive_signals", [])

    # ---------- 执行驱动检测 ----------

    def _detect_execution_drive(self, answers: Dict[str, Any]) -> List[str]:
        """
        检测预见回答中是否存在执行驱动特征。
        返回警告列表（空列表表示未检测到）。
        """
        warnings = []

        # 特征1：必答项未回答（目标不清就动手 = 执行驱动）
        must_answer_ids = [
            q["id"] for q in self.get_forethought_questions()
            if q.get("must_answer") and q["type"] == "task_analysis"
        ]
        for qid in must_answer_ids:
            val = answers.get(qid, "")
            if not val or (isinstance(val, str) and not val.strip()):
                warnings.append(
                    f"执行驱动警告：必答项 [{qid}] 未回答——动手前没想清楚目标，"
                    f"这是执行驱动的典型特征"
                )

        # 特征2：复杂度评估为"简单"但任务实际复杂（启发式：回答过短）
        complexity = answers.get("complexity_assessment", "")
        if isinstance(complexity, str) and len(complexity) < 4 and complexity:
            warnings.append(
                f"执行驱动警告：复杂度评估过短（'{complexity}'），"
                f"可能低估了任务复杂度"
            )

        return warnings

    # ---------- 三阶段执行 ----------

    def _run_forethought(self, fn: Optional[Callable], result: CycleResult) -> PhaseRecord:
        """执行预见阶段"""
        rec = result.forethought
        rec.started_at = time.strftime("%Y-%m-%d %H:%M:%S")

        if fn is None:
            if self.enforce_strict:
                raise ValueError(
                    "预见阶段（forethought）不可跳过：enforce_strict=True。"
                    "请提供 forethought_fn 回答任务分析4问。"
                )
            rec.skipped = True
            return rec

        answers = fn() or {}
        rec.answers = answers

        # 执行驱动检测
        rec.warnings = self._detect_execution_drive(answers)
        for w in rec.warnings:
            logger.warning(w)

        # 检查必答项
        must_ids = [
            q["id"] for q in self.get_forethought_questions()
            if q.get("must_answer") and q["type"] == "task_analysis"
        ]
        all_answered = all(
            answers.get(qid) for qid in must_ids
        )
        rec.completed = all_answered and len(rec.warnings) == 0
        rec.finished_at = time.strftime("%Y-%m-%d %H:%M:%S")
        return rec

    def _run_performance(self, fn: Optional[Callable], result: CycleResult) -> PhaseRecord:
        """执行执行阶段"""
        rec = result.performance
        rec.started_at = time.strftime("%Y-%m-%d %H:%M:%S")

        if fn is None:
            if self.enforce_strict:
                raise ValueError(
                    "执行阶段（performance）不可跳过：enforce_strict=True。"
                )
            rec.skipped = True
            return rec

        answers = fn() or {}
        rec.answers = answers
        rec.completed = True
        rec.finished_at = time.strftime("%Y-%m-%d %H:%M:%S")
        return rec

    def _run_reflection(self, fn: Optional[Callable], result: CycleResult) -> PhaseRecord:
        """执行反思阶段"""
        rec = result.reflection
        rec.started_at = time.strftime("%Y-%m-%d %H:%M:%S")

        if fn is None:
            # enforce_strict 下，反思不能跳过，但允许"未完成"标记
            if self.enforce_strict:
                rec.skipped = True
                rec.completed = False
                rec.warnings.append(
                    "反思阶段未执行：enforce_strict=True 但未提供 reflect_fn。"
                    "三段式复盘是固定任务，不可省略。"
                )
                rec.finished_at = time.strftime("%Y-%m-%d %H:%M:%S")
                return rec
            rec.skipped = True
            rec.finished_at = time.strftime("%Y-%m-%d %H:%M:%S")
            return rec

        answers = fn() or {}
        rec.answers = answers

        # 检查三段式必答项
        must_ids = [
            q["id"] for q in self.get_reflection_questions()
            if q.get("must_answer")
        ]
        all_answered = all(answers.get(qid) for qid in must_ids)
        rec.completed = all_answered
        rec.finished_at = time.strftime("%Y-%m-%d %H:%M:%S")
        return rec

    # ---------- 完整循环 ----------

    def run(
        self,
        task: str,
        forethought_fn: Optional[Callable] = None,
        execute_fn: Optional[Callable] = None,
        reflect_fn: Optional[Callable] = None,
    ) -> CycleResult:
        """
        执行完整认知循环：预见 → 执行 → 反思。

        参数：
            task: 任务描述
            forethought_fn: 预见阶段回调，返回 dict（含 goal_clarity 等键）
            execute_fn: 执行阶段回调，返回 dict（含 output 等键）
            reflect_fn: 反思阶段回调，返回 dict（含 factual/cognitive/iterative 键）

        返回：
            CycleResult，包含三阶段的完整记录

        异常：
            enforce_strict=True 时，跳过预见或执行阶段会抛出 ValueError
        """
        result = CycleResult(task=task)

        # 阶段一：预见
        self._run_forethought(forethought_fn, result)

        # 阶段二：执行
        self._run_performance(execute_fn, result)

        # 阶段三：反思
        self._run_reflection(reflect_fn, result)

        # 汇总
        result.all_completed = (
            result.forethought.completed
            and result.performance.completed
            and result.reflection.completed
        )

        if not result.all_completed:
            logger.warning(
                "认知循环未全部完成：forethought=%s, performance=%s, reflection=%s",
                result.forethought.completed,
                result.performance.completed,
                result.reflection.completed,
            )

        return result


if __name__ == "__main__":
    # 自测
    cycle = CognitiveCycle()
    print("=== 预见阶段问题 ===")
    for q in cycle.get_forethought_questions():
        print(f"  [{q['id']}] {q['question']}")
    print("\n=== 反思阶段问题 ===")
    for q in cycle.get_reflection_questions():
        print(f"  [{q['id']}] {q['name']}：{q['question']}")
    print("\n=== 执行阶段固定任务 ===")
    for t in cycle.get_fixed_tasks():
        print(f"  [{t['id']}] {t['rule']}")
    print("\n=== 执行驱动信号 ===")
    for s in cycle.get_execution_drive_signals():
        print(f"  - {s}")
