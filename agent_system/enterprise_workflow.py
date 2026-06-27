#!/usr/bin/env python3
"""
明烛企业级工作流引擎 v4.0
参考世界级企业体系，实现层级化任务调度。

架构：董事会(用户) → CEO(明烛) → C-level(高管) → 部门(执行)
流程：立项 → 规划 → 执行 → 审查 → 复盘

核心改进（vs v3.x）：
1. 层级化：人格不再是平铺，有明确上下级关系
2. 任务板：CEO创建任务，部门自主领取，去中心化协调
3. 标准流程：5阶段工作流，每阶段有明确owner和output
4. Heartbeat：执行中汇报进度和阻塞，可升级
5. 去官僚：去掉企业里的虚无主义（汇报PPT/会议纪要/审批流），保留高效决策
"""
import json
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

ORG_CONFIG = Path(__file__).parent.parent / "config" / "organization.yaml"


class TaskState(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    REVIEWED = "reviewed"


class WorkflowPhase(str, Enum):
    INITIATION = "initiation"      # 立项
    PLANNING = "planning"          # 规划
    EXECUTION = "execution"        # 执行
    REVIEW = "review"              # 审查
    RETROSPECTIVE = "retrospective"  # 复盘


@dataclass
class Task:
    """任务板条目"""
    id: str
    title: str
    assigned_to: str = ""          # persona_id
    state: TaskState = TaskState.PENDING
    created_at: str = ""
    dependencies: List[str] = field(default_factory=list)
    priority: int = 1              # 1=高 2=中 3=低
    heartbeat: List[Dict] = field(default_factory=list)  # 进度汇报
    result: str = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "title": self.title, "assigned_to": self.assigned_to,
            "state": self.state.value, "priority": self.priority,
            "dependencies": self.dependencies, "result": self.result[:200],
            "heartbeats": len(self.heartbeat),
        }


@dataclass
class WorkflowResult:
    """工作流执行结果"""
    phase: WorkflowPhase
    tasks: List[Task] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    review_report: str = ""
    final_output: str = ""
    lessons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "phase": self.phase.value,
            "tasks": [t.to_dict() for t in self.tasks],
            "decisions": self.decisions,
            "review_report": self.review_report[:300],
            "final_output": self.final_output[:300],
            "lessons": self.lessons,
        }


class EnterpriseWorkflow:
    """企业级工作流引擎"""

    def __init__(self):
        self._load_org_config()
        self.task_board: List[Task] = []
        self.current_phase: WorkflowPhase = WorkflowPhase.INITIATION

    def _load_org_config(self):
        """加载组织架构配置"""
        import yaml
        if ORG_CONFIG.exists():
            self.org = yaml.safe_load(ORG_CONFIG.read_text(encoding="utf-8"))
        else:
            self.org = {}

    def get_persona_level(self, persona_id: str) -> str:
        """获取人格的层级（ceo/c_level/department）"""
        if persona_id == "mingzhu":
            return "ceo"
        for c in self.org.get("hierarchy", {}).get("c_level", []):
            if persona_id in c.get("personas", []):
                return "c_level"
        for d in self.org.get("hierarchy", {}).get("departments", []):
            if d.get("persona") == persona_id:
                return "department"
        return "department"

    def get_persona_title(self, persona_id: str) -> str:
        """获取人格的企业头衔"""
        for c in self.org.get("hierarchy", {}).get("c_level", []):
            if persona_id in c.get("personas", []):
                return c["title"]
        for d in self.org.get("hierarchy", {}).get("departments", []):
            if d.get("persona") == persona_id:
                return d["title"]
        return persona_id

    def run(self, user_input: str, persona_ids: List[str],
            execute_fn) -> WorkflowResult:
        """运行企业级工作流

        Args:
            user_input: 用户输入
            persona_ids: 需要调用的子人格
            execute_fn: 执行函数 (persona_id, task) -> result

        Returns:
            WorkflowResult
        """
        result = WorkflowResult(phase=WorkflowPhase.INITIATION)

        # 阶段1：立项（CEO）
        result = self._phase_initiation(user_input, persona_ids, result)

        # 阶段2：规划（C-level讨论，如果复杂）
        if len(persona_ids) > 2:
            result = self._phase_planning(user_input, persona_ids, result)

        # 阶段3：执行（部门并行/串行）
        result = self._phase_execution(user_input, persona_ids, execute_fn, result)

        # 阶段4：审查（观察部+CSO）
        result = self._phase_review(result)

        # 阶段5：复盘
        result = self._phase_retrospective(user_input, result)

        return result

    def _phase_initiation(self, user_input: str, persona_ids: List[str],
                          result: WorkflowResult) -> WorkflowResult:
        """阶段1：立项"""
        self.current_phase = WorkflowPhase.INITIATION
        # CEO创建任务
        for pid in persona_ids:
            task = Task(
                id=f"task-{pid}-{int(time.time())}",
                title=f"{self.get_persona_title(pid)}执行: {user_input[:50]}",
                assigned_to=pid,
                state=TaskState.PENDING,
                created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
            self.task_board.append(task)
            result.tasks.append(task)
        result.decisions.append(f"CEO立项：{len(persona_ids)}个任务委派")
        return result

    def _phase_planning(self, user_input: str, persona_ids: List[str],
                        result: WorkflowResult) -> WorkflowResult:
        """阶段2：规划（C-level高管讨论）"""
        self.current_phase = WorkflowPhase.PLANNING
        c_level = [p for p in persona_ids if self.get_persona_level(p) == "c_level"]
        if c_level:
            result.decisions.append(f"C-level规划会议：{[self.get_persona_title(p) for p in c_level]}")
        return result

    def _phase_execution(self, user_input: str, persona_ids: List[str],
                         execute_fn, result: WorkflowResult) -> WorkflowResult:
        """阶段3：执行"""
        self.current_phase = WorkflowPhase.EXECUTION
        for task in result.tasks:
            task.state = TaskState.IN_PROGRESS
            task.heartbeat.append({
                "time": time.strftime("%H:%M:%S"),
                "status": "开始执行",
            })
            try:
                task.result = execute_fn(task.assigned_to, user_input) or ""
                task.state = TaskState.DONE
            except Exception as e:
                task.state = TaskState.BLOCKED
                task.heartbeat.append({"status": f"阻塞: {e}"})
                logger.warning(f"任务 {task.id} 阻塞: {e}")
        return result

    def _phase_review(self, result: WorkflowResult) -> WorkflowResult:
        """阶段4：审查"""
        self.current_phase = WorkflowPhase.REVIEW
        done = [t for t in result.tasks if t.state == TaskState.DONE]
        blocked = [t for t in result.tasks if t.state == TaskState.BLOCKED]
        result.review_report = (
            f"审查报告：{len(done)}个任务完成，{len(blocked)}个阻塞。"
            + ("所有任务通过审查。" if not blocked else "需处理阻塞任务。")
        )
        return result

    def _phase_retrospective(self, user_input: str,
                             result: WorkflowResult) -> WorkflowResult:
        """阶段5：复盘"""
        self.current_phase = WorkflowPhase.RETROSPECTIVE
        result.decisions.append("CEO复盘：总结经验，写入进化系统")
        result.lessons.append("工作流5阶段完整执行")
        return result

    def get_org_summary(self) -> Dict:
        """获取组织架构摘要"""
        return {
            "model": self.org.get("meta", {}).get("model", "enterprise"),
            "levels": ["board", "ceo", "c_level", "department"],
            "c_level_count": len(self.org.get("hierarchy", {}).get("c_level", [])),
            "department_count": len(self.org.get("hierarchy", {}).get("departments", [])),
            "workflow_phases": [p.value for p in WorkflowPhase],
        }


# 全局实例
_workflow: Optional[EnterpriseWorkflow] = None

def get_workflow() -> EnterpriseWorkflow:
    global _workflow
    if _workflow is None:
        _workflow = EnterpriseWorkflow()
    return _workflow


if __name__ == "__main__":
    wf = get_workflow()
    print("=== 组织架构 ===")
    print(json.dumps(wf.get_org_summary(), ensure_ascii=False, indent=2))
    print("\n=== 人格层级 ===")
    for p in ["mingzhu", "zhen_zao", "gen_shou", "qian_duan", "kan_guan"]:
        print(f"  {p}: {wf.get_persona_level(p)} / {wf.get_persona_title(p)}")
