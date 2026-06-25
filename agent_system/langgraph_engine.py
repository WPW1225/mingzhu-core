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
        """路由节点：决定调用哪些子人格（P1-5 语义路由增强）"""
        user_input = state.get("user_input", "")

        # 第一层：关键词快速路由（低成本）
        persona_ids = self.mz.route(user_input)

        # 第二层：LLM 语义路由（当关键词路由不确定时启用）
        # 触发条件：①只路由到默认乾断 ②输入较短无明确关键词 ③用户明确要求多视角
        needs_llm_route = (
            len(persona_ids) == 1 and persona_ids[0] == "qian_duan"
        ) or len(user_input) < 8

        if needs_llm_route:
            resp = self.router.generate(
                prompt=f"""用户输入：{user_input}

判断这句话需要哪些能力（可多选，用逗号分隔，只回答能力名）：
搜索调研/代码工程/逻辑决策/安全审查/管理协调/创意灵感/表达沟通/观察分析""",
                scene=Scene.ROUTING, max_tokens=40,
            )
            if resp.ok:
                keyword_map = {
                    "搜索调研": "xun_feng", "代码工程": "zhen_zao",
                    "逻辑决策": "qian_duan", "安全审查": "gen_shou",
                    "管理协调": "kun_zai", "创意灵感": "dui_ze",
                    "表达沟通": "li_ming", "观察分析": "kan_guan",
                }
                llm_personas = []
                for kw, pid in keyword_map.items():
                    if kw in resp.content and pid not in llm_personas:
                        llm_personas.append(pid)
                # 如果 LLM 给出了明确判断，用 LLM 的结果（更准）
                if llm_personas:
                    persona_ids = llm_personas

        # 确保至少有一个人格
        if not persona_ids:
            persona_ids = ["qian_duan"]

        # 限制最多3个人格（避免 token 爆炸）
        if len(persona_ids) > 3:
            persona_ids = persona_ids[:3]

        return {
            "persona_ids": persona_ids,
            "routing_reason": self.mz.explain_routing(user_input),
            "routing_method": "llm" if needs_llm_route else "keyword",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _node_execute_personas(self, state: MingZhuState) -> Dict:
        """执行节点：调用各子人格（v3.3 顺序协作，后执行者能看到先执行者的输出）

        改进：从纯并行改为顺序协作——每个人格执行时，能看到之前人格的输出摘要，
        可以引用、补充或质疑。这是"人格间消息传递"的轻量实现。
        """
        persona_ids = state.get("persona_ids", [])
        user_input = state.get("user_input", "")
        context = state.get("context", "")

        # 工具集成：某些人格在执行前先调用工具获取信息
        tool_context = self._maybe_call_tools(persona_ids, user_input)
        if tool_context:
            context = (context + "\n\n" + tool_context).strip()

        results = []
        prior_outputs = []  # 已执行人格的输出摘要（供后续人格参考）

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

            # 构造系统提示词（含之前人格的输出，实现协作）
            prior_context = ""
            if prior_outputs:
                prior_context = "\n\n【其他人格已给出的分析（你可引用/补充/质疑）】\n" + \
                                "\n---\n".join(prior_outputs)

            system_prompt = f"""你是「{persona_name}」，明烛数字分身的子人格。

{persona_content}
{prior_context}

请以「{persona_name}」的视角回答用户问题。输出格式：
1. 分析/建议内容
2. 置信度：高/中/低
3. 如果是艮守且发现安全问题，标注「否决」
4. 如果是坎观，提供观察报告
"""

            # 真正调用 LLM
            scene = Scene.SAFETY if pid == "gen_shou" else Scene.ANALYSIS
            full_prompt = user_input if not context else f"{context}\n\n当前问题：{user_input}"
            resp = self.router.generate(
                full_prompt, system_prompt=system_prompt, scene=scene,
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

            # 收集输出摘要供后续人格参考（限制长度防 token 爆炸）
            prior_outputs.append(f"{persona_name}: {content[:300]}")

        return {"persona_results": results}

    def _maybe_call_tools(self, persona_ids: List[str], user_input: str) -> str:
        """工具集成：根据人格配置的 tools 字段，自动调用合适的工具。

        v3.3 改进：从 persona yaml 读取 tools 绑定，不再硬编码。
        支持的工具：web_search / calculator / code_execute / file_read
        """
        tool_context_parts = []

        try:
            from .tools import get_registry
            from .config_loader import config as soul_config
            registry = get_registry()

            for pid in persona_ids:
                # 从配置读取该人格绑定的工具
                persona_cfg = soul_config.personas.get(pid, {})
                bound_tools = persona_cfg.get("tools", []) if persona_cfg else []

                for tool_name in bound_tools:
                    result = None
                    if tool_name == "web_search" and len(user_input) > 10:
                        # 巽风：LLM 提取关键词
                        kw_resp = self.router.generate(
                            prompt=f"从以下用户输入提取1个最核心搜索关键词(只返回关键词):\n{user_input}",
                            scene=Scene.ROUTING, max_tokens=20,
                        )
                        if kw_resp.ok:
                            keyword = kw_resp.content.strip().strip('"\'""')
                            if 2 <= len(keyword) <= 30:
                                result = registry.call("web_search", query=keyword, num=3)
                                if result.success:
                                    tool_context_parts.append(f"[巽风搜索·{keyword}]:\n{result.output[:800]}")

                    elif tool_name == "calculator":
                        import re
                        calc_match = re.search(r'(\d+(?:\.\d+)?\s*[*+\-/^]+\s*\d+(?:\.\d+)?(?:\s*[*+\-/^]+\s*\d+(?:\.\d+)?)*)', user_input)
                        if calc_match:
                            expr = calc_match.group(1).replace('^', '**')
                            result = registry.call("calculator", expression=expr)
                            if result.success:
                                tool_context_parts.append(f"[乾断计算·{expr}]: {result.output}")

                    elif tool_name == "code_execute":
                        # 震造/艮守：检测代码块时执行验证
                        import re
                        code_match = re.search(r'\`\`\`(?:python)?\n(.*?)\n\`\`\`', user_input, re.DOTALL)
                        if code_match:
                            code = code_match.group(1)[:2000]  # 限制长度
                            result = registry.call("code_execute", code=code)
                            if result.success:
                                tool_context_parts.append(f"[代码执行结果]:\n{result.output[:500]}")
                            elif result.error:
                                tool_context_parts.append(f"[代码执行失败·{pid}]: {result.error[:200]}")

                    elif tool_name == "file_read":
                        # 坤载/震造：检测文件路径时读取
                        import re
                        path_match = re.search(r'(?:文件|读取|查看|分析)\s*[「「]?(?:\./)?([\w/]+\.\w+)', user_input)
                        if path_match:
                            fpath = path_match.group(1)
                            result = registry.call("file_read", path=fpath)
                            if result.success:
                                tool_context_parts.append(f"[文件内容·{fpath}]:\n{result.output[:800]}")

        except Exception as e:
            logger.debug(f"工具调用失败（不影响主流程）: {e}")

        return "\n\n".join(tool_context_parts)

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
        """观察节点：坎观独立审查（v3.1 用 LLM 做深度质量审查）"""
        results = state.get("persona_results", [])
        final_output = state.get("final_output", "")
        conflicts = state.get("conflicts", [])
        user_input = state.get("user_input", "")

        # 基础统计（规则层，永远执行）
        stats = []
        stats.append(f"调用 {len(results)} 个人格")
        if conflicts:
            stats.append(f"{len(conflicts)} 个冲突")
        if state.get("vetoed"):
            stats.append("触发安全否决")
        errors = [r for r in results if r.get("error")]
        if errors:
            stats.append(f"{len(errors)} 个人格降级")
        stats_report = "；".join(stats) + "。"

        # LLM 深度审查（坎观视角：发现盲点和质量问题）
        llm_report = ""
        try:
            persona_summary = "\n".join(
                f"- {r.get('name','')}: {r.get('content','')[:200]}"
                for r in results if r.get("content")
            )

            system_prompt = """你是「坎观」，明烛的观察者人格（坎 ☵ 水）。
你的职责是独立审查整个调度的质量，发现盲点，不参与执行只做批判性观察。

审查维度：
1. 目标达成度：最终输出是否真正回答了用户问题
2. 盲点：有没有被忽略的重要角度
3. 质量：分析深度够不够，是否停留在表面
4. 一致性：各人格输出是否自洽
5. 改进建议：下次怎么做得更好

输出格式：2-4句话的观察报告，直接指出问题，不客套。"""

            resp = self.router.generate(
                prompt=f"""用户问题：{user_input}

各人格输出摘要：
{persona_summary}

最终汇总输出：
{final_output[:800]}

冲突：{conflicts if conflicts else '无'}

请给出观察报告。""",
                system_prompt=system_prompt, scene=Scene.ANALYSIS, max_tokens=300,
            )
            if resp.ok:
                llm_report = resp.content.strip()
        except Exception as e:
            llm_report = f"（坎观LLM审查失败：{e}）"

        # 合并报告
        full_report = stats_report
        if llm_report:
            full_report += "\n\n" + llm_report

        return {"observer_report": full_report}

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
