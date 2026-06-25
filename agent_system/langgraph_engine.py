#!/usr/bin/env python3
"""
明烛 LangGraph 引擎 v3.0
将明烛的"路由→执行→审查→汇总"流程映射为 LangGraph 状态图。

架构原则：
- 框架服从明烛：LangGraph 只做执行层，灵魂层（SOUL/八卦/命理/认知循环）保留为明烛配置
- 状态图模型：每个节点是一个处理步骤，边是条件路由
- 原生能力：状态管理、checkpoint（多轮记忆）、失败恢复

状态图结构：
    [route] → [execute_personas] → [safety_check] → [conflict_check] → [synthesize] → [observe] → END
                  ↑                    |
                  └── veto ────────────┘  (艮守否决则回到执行调整)

使用方式：
    from agent_system.langgraph_engine import MingZhuGraph
    graph = MingZhuGraph()
    result = graph.invoke("帮我分析这段代码", thread_id="session-1")
"""
import json
import logging
from typing import Dict, List, Any, Optional, Annotated
from dataclasses import dataclass, field
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from typing_extensions import TypedDict

from . import PERSONAS, TRIGRAM_ELEMENT, MingZhu
from .llm_backends import get_router, Scene, LLMResponse

logger = logging.getLogger(__name__)


# ============================================================
# 状态定义
# ============================================================

class MingZhuState(TypedDict, total=False):
    """明烛状态图的状态结构

    LangGraph 的 State 在每个节点间传递，实现多轮记忆。
    thread_id 区分不同会话，配合 MemorySaver 实现跨调用状态保持。
    """
    # 输入
    user_input: str                          # 用户原始输入
    context: str                             # 额外上下文（多轮历史摘要）

    # 路由结果
    persona_ids: List[str]                   # 需要调用的子人格ID列表
    routing_reason: str                      # 路由理由

    # 执行结果
    persona_results: List[Dict]              # 各人格执行结果
    vetoed: bool                             # 是否被艮守否决
    veto_reason: str                         # 否决理由

    # 冲突检测
    conflicts: List[str]                     # 检测到的冲突

    # 最终输出
    final_output: str                        # 离明汇总后的最终输出
    observer_report: str                     # 坎观观察报告

    # 元数据
    thread_id: str                           # 会话ID（多轮记忆用）
    timestamp: str                           # 调用时间
    error: Optional[str]                     # 错误信息


# ============================================================
# 图节点
# ============================================================

class MingZhuGraph:
    """明烛 LangGraph 状态图引擎"""

    def __init__(self, llm_router=None):
        self.mz = MingZhu(llm_client=None)  # 复用明烛的路由和人格加载逻辑
        self.router = llm_router or get_router()
        self.checkpointer = MemorySaver()  # 必须在 _build_graph 之前初始化
        self.graph = self._build_graph()

    def _build_graph(self):
        """构建状态图"""
        workflow = StateGraph(MingZhuState)

        # 添加节点
        workflow.add_node("route", self._node_route)
        workflow.add_node("execute", self._node_execute_personas)
        workflow.add_node("safety_check", self._node_safety_check)
        workflow.add_node("conflict_check", self._node_conflict_check)
        workflow.add_node("synthesize", self._node_synthesize)
        workflow.add_node("observe", self._node_observe)

        # 设置入口
        workflow.set_entry_point("route")

        # 添加边
        workflow.add_edge("route", "execute")
        workflow.add_conditional_edges(
            "safety_check",
            self._after_safety_check,
            {"pass": "conflict_check", "veto": "synthesize"},  # 否决也进汇总（标注否决）
        )
        workflow.add_edge("execute", "safety_check")
        workflow.add_edge("conflict_check", "synthesize")
        workflow.add_edge("synthesize", "observe")
        workflow.add_edge("observe", END)

        return workflow.compile(checkpointer=self.checkpointer)

    # ---------- 节点实现 ----------

    def _node_route(self, state: MingZhuState) -> Dict:
        """路由节点：决定调用哪些子人格"""
        user_input = state.get("user_input", "")
        persona_ids = self.mz.route(user_input)

        # 语义路由增强：用 LLM 判断是否需要补充人格（P1-5）
        if len(persona_ids) == 1 and persona_ids[0] == "qian_duan":
            # 默认路由到乾断时，用 LLM 复核是否需要补充
            resp = self.router.generate(
                prompt=f"用户输入：{user_input}\n\n判断这句话最需要哪种能力？只回答一个词：搜索调研/代码工程/逻辑决策/安全审查/管理协调/创意灵感/表达沟通/观察分析",
                scene=Scene.ROUTING, max_tokens=20,
            )
            if resp.ok:
                keyword_map = {
                    "搜索调研": "xun_feng", "代码工程": "zhen_zao",
                    "逻辑决策": "qian_duan", "安全审查": "gen_shou",
                    "管理协调": "kun_zai", "创意灵感": "dui_ze",
                    "表达沟通": "li_ming", "观察分析": "kan_guan",
                }
                for kw, pid in keyword_map.items():
                    if kw in resp.content and pid not in persona_ids:
                        persona_ids.append(pid)
                        break

        return {
            "persona_ids": persona_ids,
            "routing_reason": self.mz.explain_routing(user_input),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _node_execute_personas(self, state: MingZhuState) -> Dict:
        """执行节点：并行调用各子人格（真正调用 LLM）"""
        persona_ids = state.get("persona_ids", [])
        user_input = state.get("user_input", "")
        context = state.get("context", "")

        results = []
        for pid in persona_ids:
            persona_cfg = PERSONAS.get(pid, {})
            persona_name = persona_cfg.get("name", pid)
            persona_icon = persona_cfg.get("icon", "")

            # 加载人格 prompt
            try:
                persona_content = self.mz._load_persona(pid)
            except Exception as e:
                results.append({
                    "persona": pid, "name": persona_name, "icon": persona_icon,
                    "content": "", "confidence": "低", "vetoed": False,
                    "error": f"加载人格失败: {e}",
                })
                continue

            # 构造系统提示词
            system_prompt = f"""你是「{persona_name}」，明烛数字分身的子人格。

{persona_content}

请以「{persona_name}」的视角回答用户问题。输出格式：
1. 分析/建议内容
2. 置信度：高/中/低
3. 如果是艮守且发现安全问题，标注「否决」
4. 如果是坎观，提供观察报告
"""

            # 真正调用 LLM
            scene = Scene.SAFETY if pid == "gen_shou" else Scene.ANALYSIS
            resp = self.router.generate(
                user_input if not context else f"{context}\n\n当前问题：{user_input}",
                system_prompt=system_prompt,
                scene=scene,
            )

            content = resp.content if resp.ok else f"（{persona_name} 调用失败：{resp.error}）"
            vetoed = "否决" in content and pid == "gen_shou"
            confidence = "中"
            if "置信度：高" in content or "置信度: 高" in content:
                confidence = "高"
            elif "置信度：低" in content or "置信度: 低" in content:
                confidence = "低"

            results.append({
                "persona": pid, "name": persona_name, "icon": persona_icon,
                "content": content, "confidence": confidence,
                "vetoed": vetoed, "error": resp.error,
                "model": resp.model, "backend": resp.backend,
            })

        return {"persona_results": results}

    def _node_safety_check(self, state: MingZhuState) -> Dict:
        """安全检查节点：艮守审查，一票否决"""
        results = state.get("persona_results", [])
        vetoed = any(r.get("vetoed") for r in results)
        veto_reason = ""
        if vetoed:
            for r in results:
                if r.get("vetoed"):
                    veto_reason = f"{r['name']} 否决：{r['content'][:200]}"
                    break
        return {"vetoed": vetoed, "veto_reason": veto_reason}

    def _node_conflict_check(self, state: MingZhuState) -> Dict:
        """冲突检测节点：扫描人格间对立信号"""
        from . import AgentResult
        results = state.get("persona_results", [])
        agent_results = [
            AgentResult(
                persona=r["persona"], name=r["name"], icon=r["icon"],
                content=r.get("content", ""), confidence=r.get("confidence", "中"),
                vetoed=r.get("vetoed", False), error=r.get("error"),
            ) for r in results
        ]
        conflicts = self.mz._detect_conflicts(agent_results)
        return {"conflicts": conflicts}

    def _node_synthesize(self, state: MingZhuState) -> Dict:
        """汇总节点：离明封装最终输出"""
        results = state.get("persona_results", [])
        conflicts = state.get("conflicts", [])
        vetoed = state.get("vetoed", False)
        user_input = state.get("user_input", "")

        # 拼接各人格输出
        parts = []
        for r in results:
            if r.get("content") and not r.get("error"):
                parts.append(f"{r['icon']} {r['name']}（置信度：{r['confidence']}）：\n{r['content']}")

        other_outputs = "\n\n---\n\n".join(parts)

        # 冲突提示
        conflict_hint = ""
        if conflicts:
            conflict_hint = "\n\n⚠️ 检测到人格间冲突，请在汇总时优先解决：\n" + \
                           "\n".join(f"- {c}" for c in conflicts)

        # 否决提示
        veto_hint = ""
        if vetoed:
            veto_hint = f"\n\n🛑 安全否决：{state.get('veto_reason', '')}"

        # 用 LLM 做离明汇总
        system_prompt = """你是「离明」，明烛数字分身的表达封装人格。
你的任务是把多个子人格的分析结果汇总成一份清晰、结构化的最终回复。

要求：
1. 先结论后展开
2. 如有冲突，明确指出分歧点和各方立场
3. 如有安全否决，把否决理由放在最前面
4. 保持平和、清晰、不谄媚的语气
5. 用中文"""

        full_context = f"其他人格的输出：\n{other_outputs}{conflict_hint}{veto_hint}"
        resp = self.router.generate(
            prompt=f"用户问题：{user_input}\n\n请汇总以下各人格的分析：\n{full_context}",
            system_prompt=system_prompt, scene=Scene.DEFAULT, max_tokens=1500,
        )

        final_output = resp.content if resp.ok else (
            f"（离明汇总失败：{resp.error}）\n\n原始各人格输出：\n{other_outputs}"
        )

        return {"final_output": final_output}

    def _node_observe(self, state: MingZhuState) -> Dict:
        """观察节点：坎观独立审查"""
        results = state.get("persona_results", [])
        final_output = state.get("final_output", "")
        conflicts = state.get("conflicts", [])

        # 简化版观察报告（无 LLM 时用规则）
        report_parts = []
        report_parts.append(f"本次调用 {len(results)} 个人格")
        if conflicts:
            report_parts.append(f"检测到 {len(conflicts)} 个冲突")
        if state.get("vetoed"):
            report_parts.append("触发安全否决")
        errors = [r for r in results if r.get("error")]
        if errors:
            report_parts.append(f"{len(errors)} 个人格执行失败（已降级）")

        return {"observer_report": "；".join(report_parts) + "。"}

    def _after_safety_check(self, state: MingZhuState) -> str:
        """安全检查后的条件路由"""
        return "veto" if state.get("vetoed") else "pass"

    # ---------- 对外接口 ----------

    def invoke(self, user_input: str, context: str = "",
               thread_id: str = "default") -> Dict[str, Any]:
        """调用明烛状态图

        参数：
            user_input: 用户输入
            context: 额外上下文（多轮历史）
            thread_id: 会话ID，相同 thread_id 共享状态（多轮记忆）

        返回：
            完整状态字典，含 final_output / observer_report / persona_results 等
        """
        config = {"configurable": {"thread_id": thread_id}}
        initial_state = MingZhuState(
            user_input=user_input,
            context=context,
            thread_id=thread_id,
        )
        return self.graph.invoke(initial_state, config=config)

    def get_history(self, thread_id: str) -> List[Dict]:
        """获取某个会话的历史状态（多轮记忆）"""
        config = {"configurable": {"thread_id": thread_id}}
        try:
            return list(self.graph.get_state_history(config))
        except Exception:
            return []


# 便捷函数
def quick_graph_run(user_input: str, thread_id: str = "default") -> str:
    """快速调用，只返回最终输出"""
    graph = MingZhuGraph()
    result = graph.invoke(user_input, thread_id=thread_id)
    return result.get("final_output", "")


if __name__ == "__main__":
    print("=== 明烛 LangGraph 引擎测试 ===\n")
    graph = MingZhuGraph()

    # 测试1：代码相关
    print(">>> 测试1：代码相关输入")
    result = graph.invoke("帮我写一个文件上传功能", thread_id="test-1")
    print(f"路由：{result.get('routing_reason', '')[:100]}")
    print(f"人格数：{len(result.get('persona_results', []))}")
    print(f"冲突：{result.get('conflicts', [])}")
    print(f"观察：{result.get('observer_report', '')}")
    print(f"最终输出（前200字）：{result.get('final_output', '')[:200]}")
    print()

    # 测试2：多轮记忆（相同 thread_id）
    print(">>> 测试2：多轮记忆（相同 thread_id）")
    result2 = graph.invoke("刚才说的文件上传，再补充一下安全检查", thread_id="test-1")
    print(f"路由：{result2.get('routing_reason', '')[:100]}")
    print(f"最终输出（前200字）：{result2.get('final_output', '')[:200]}")
