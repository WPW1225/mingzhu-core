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
    from .execution_strategy import select_strategy, ExecutionStrategyType, ReactStrategy

    graph = _get_graph()
    start = _time.time()

    # v4.8: 双轨制真正接入——根据策略选Pipeline或ReAct
    strategy_type = select_strategy(user_input)
    if strategy_type == ExecutionStrategyType.REACT:
        # ReAct策略：LLM自主调工具循环
        react = ReactStrategy(graph.router)
        react_result = react.execute(user_input, "", graph.router)
        result = {
            "final_output": react_result.get("output", ""),
            "persona_results": [],
            "schedule": {"strategy": "react"},
        }
    else:
        # Pipeline策略：走5阶段图
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

    # v3.4: 自我进化——提取经验、检测纠正、学习偏好
    try:
        from .evolution import get_engine, Experience, Preference
        engine = get_engine()
        graph = _get_graph()

        # 检测用户是否在纠正明烛
        correction = engine.detect_correction(user_input, graph.router)
        if correction:
            engine.record_preference(Preference(
                timestamp=_time.strftime("%Y-%m-%d %H:%M:%S"),
                trigger=user_input[:100], preference=correction,
            ))

        # 提取可复用经验
        lesson = engine.extract_lesson(
            user_input, output["output"], output["observer"], graph.router
        )

        # v3.6: 明烛自评——每次对话后给自己打分
        self_score = _self_evaluate(
            user_input, output["output"], output["observer"],
            output["personas"], graph.router,
        )
        output["self_score"] = self_score

        engine.record_experience(Experience(
            timestamp=_time.strftime("%Y-%m-%d %H:%M:%S"),
            user_input=user_input, output=output["output"],
            personas=[p["name"] for p in output["personas"]],
            schedule=result.get("schedule", {}).get("strategy", "unknown"),
            observer_report=output["observer"],
            outcome="corrected" if correction else "success",
            lesson=lesson, reusable=bool(lesson),
        ))

        # v4.9: 甲觉·学习官——学习外部知识到知识库
        try:
            from .jia_jue import get_jia_jue
            jia_jue = get_jia_jue()
            # 甲觉向外学习，不是归纳内部经验
            learned = jia_jue.learn(user_input, graph.router) if any(
                kw in user_input for kw in ["搜索", "查询", "了解", "学习", "最新", "什么是"]
            ) else {"learned": 0}
            output["learned"] = learned
        except Exception:
            pass
    except Exception:
        pass  # 进化失败不影响主流程

    return output


def _self_evaluate(user_input: str, output: str, observer: str,
                   personas: list, router) -> Dict:
    """v3.6: 明烛自评——每次对话后给自己打分

    维度：
    - 目标达成度：是否真正回答了用户问题
    - 质量：分析深度、结构清晰度
    - 诚实性：是否承认不确定性
    - 协作效果：多人格是否有效协作
    - 综合分：0-100

    结合元元认知：如果坎观指出了问题，自评分应降低。
    """
    try:
        from .llm_backends import Scene
        persona_summary = ", ".join(p.get("name", "") for p in personas[:3])
        prompt = f"""你是明烛，请对刚才这次回答做自我评价。

用户问题：{user_input[:200]}
你的回答：{output[:500]}
坎观观察：{observer[:300] if observer else '无'}
调用人格：{persona_summary}

请从4个维度打分（0-100），返回JSON：
{{"goal_completion":85,"quality":75,"honesty":90,"collaboration":70,"overall":80,"one_line":"一句话自我评价"}}"""

        resp = router.generate(prompt, scene=Scene.JUDGE, max_tokens=200)
        if not resp.ok:
            return {"overall": 0, "one_line": "自评失败"}

        import json as _json
        text = resp.content
        idx = text.find('{')
        end = text.find('}', idx)
        if idx < 0 or end < 0:
            return {"overall": 0, "one_line": "自评解析失败"}
        data = _json.loads(text[idx:end + 1])
        return {
            "goal_completion": data.get("goal_completion", 0),
            "quality": data.get("quality", 0),
            "honesty": data.get("honesty", 0),
            "collaboration": data.get("collaboration", 0),
            "overall": data.get("overall", 0),
            "one_line": data.get("one_line", ""),
        }
    except Exception as e:
        return {"overall": 0, "one_line": f"自评异常: {e}"}


def get_history(session_id: str) -> List[Dict]:
    """获取某会话的历史对话（从持久化记忆读取）"""
    from .memory import get_memory
    return get_memory().load_session(session_id)


def estimate_cost(user_input: str) -> Dict:
    """v4.5: 成本预估——执行前预估token和费用

    根据输入长度和预估人格数，估算本次对话成本。
    企业客户不怕花钱，怕月底账单吓一跳——透明化是卖点。
    """
    from .execution_strategy import select_strategy, ExecutionStrategyType
    from .cost_monitor import PRICING

    strategy = select_strategy(user_input)
    # 预估人格数：简单任务2-3个，复杂4-5个
    input_len = len(user_input)
    if input_len < 20:
        persona_count = 2
    elif input_len < 50:
        persona_count = 3
    else:
        persona_count = 4

    # 预估token：每人格 system_prompt(800) + 输入(200) + 输出(800) ≈ 1800
    # ReAct策略多3-5轮工具调用，每轮+500
    tokens_per_persona = 1800
    if strategy == ExecutionStrategyType.REACT:
        tokens_per_persona = 3500  # ReAct多轮

    total_tokens = persona_count * tokens_per_persona
    # 按智谱glm-4-plus定价估算
    cost = (total_tokens / 1000) * PRICING.get("glm-4-plus", {}).get("input", 0.05)

    return {
        "strategy": strategy.value,
        "estimated_personas": persona_count,
        "estimated_tokens": total_tokens,
        "estimated_cost_yuan": round(cost, 4),
        "model": "glm-4-plus",
        "warning": "ReAct策略成本较高" if strategy == ExecutionStrategyType.REACT else None,
    }


def get_agents_status() -> Dict:
    """v4.7: 获取所有agent状态（全状态面板）"""
    status = {}
    # 戊藏·记忆官
    try:
        from .wu_cang import get_wu_cang
        status["wu_cang"] = get_wu_cang().get_status()
    except Exception:
        status["wu_cang"] = {"error": "unavailable"}
    # 甲觉·学习官
    try:
        from .jia_jue import get_jia_jue
        status["jia_jue"] = get_jia_jue().get_status()
    except Exception:
        status["jia_jue"] = {"error": "unavailable"}
    # 进化系统
    try:
        status["evolution"] = evolution_metrics()
    except Exception:
        status["evolution"] = {"error": "unavailable"}
    # 成本
    try:
        status["cost"] = cost_summary()
    except Exception:
        status["cost"] = {"error": "unavailable"}
    # v4.7: 8个执行人格清单
    try:
        from . import PERSONAS
        status["personas"] = [
            {"id": pid, "name": p["name"], "icon": p["icon"],
             "element": {"wood": "木·用神", "fire": "火·用神", "earth": "土·喜神",
                         "water": "水·忌神", "metal": "金·忌神"}.get(
                __import__("agent_system").TRIGRAM_ELEMENT.get(pid, "earth"), "")}
            for pid, p in PERSONAS.items()
        ]
    except Exception:
        status["personas"] = []
    # v4.7: CEO状态（当前阶段+策略）
    status["ceo"] = {
        "role": "CEO·明烛主人格",
        "phases": ["initiation", "planning", "execution", "review", "retrospective"],
        "strategies": ["pipeline", "react", "parallel", "sequential", "mixed", "discuss", "iterative"],
    }
    # v4.7: 元元认知
    try:
        from .meta_cognition import evaluate_reflection
        status["meta_cognition"] = {"available": True, "dimensions": ["具体性", "根因性", "可执行性", "诚实性", "闭环性"]}
    except Exception:
        status["meta_cognition"] = {"available": False}
    # v4.7: LangSmith
    import os as _os
    status["langsmith"] = {
        "enabled": bool(_os.environ.get("LANGCHAIN_API_KEY")),
        "project": _os.environ.get("LANGCHAIN_PROJECT", "mingzhu"),
        "url": "https://app.langsmith.com",
    }
    return status


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


def evolution_summary() -> Dict:
    """获取自我进化状态（经验数、教训数、偏好数）"""
    from .evolution import get_engine
    return get_engine().summary()


def search_memory(query: str, limit: int = 5) -> List[Dict]:
    """情景记忆语义检索：v3.6 升级为向量嵌入检索

    从关键词匹配升级为 TF-IDF + 余弦相似度语义检索。
    理解语义近似（如"微服务"能匹配"microservice架构"）。
    零外部依赖，部署友好。未来可升级为 sentence-transformers。
    """
    try:
        from .vector_search import get_vector_search
        searcher = get_vector_search()
        results = searcher.search(query, limit=limit)
        if results:
            return results
    except Exception:
        pass
    # 降级：关键词匹配
    from .memory import get_memory
    memory = get_memory()
    results = []
    for session_file in memory.memory_dir.glob("*.json"):
        try:
            history = json.loads(session_file.read_text(encoding="utf-8"))
            for entry in history:
                text = (entry.get("user_input", "") + " " + entry.get("output", "")).lower()
                if query.lower() in text:
                    score = text.count(query.lower())
                    results.append({
                        "session_id": session_file.stem,
                        "timestamp": entry.get("timestamp", ""),
                        "user_input": entry.get("user_input", "")[:100],
                        "output": entry.get("output", "")[:200],
                        "score": score,
                    })
        except Exception:
            continue
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return results[:limit]


def evolution_metrics() -> Dict:
    """进化效果量化：统计明烛是否越用越好（v3.5 新增）

    指标：
    - 经验复用率：可复用经验占比
    - 纠正下降率：近期纠正数 vs 早期纠正数（是否在减少）
    - 反思质量趋势：元元认知分数是否在提升
    - 教训积累曲线
    """
    from .evolution import get_engine
    from pathlib import Path
    engine = get_engine()
    exps = engine._load(engine.exp_file)
    prefs = engine._load(engine.pref_file)

    if not exps:
        return {"status": "no_data", "message": "尚无经验数据，多对话几次后再看"}

    total = len(exps)
    reusable = [e for e in exps if e.get("reusable")]
    corrected = [e for e in exps if e.get("outcome") == "corrected"]

    # 早期 vs 近期纠正率
    mid = total // 2
    early_corrected = len([e for e in exps[:mid] if e.get("outcome") == "corrected"])
    recent_corrected = len([e for e in exps[mid:] if e.get("outcome") == "corrected"])
    early_rate = early_corrected / max(mid, 1)
    recent_rate = recent_corrected / max(total - mid, 1)
    correction_trend = "下降(变好)" if recent_rate < early_rate else "上升(需关注)"

    # 元元认知分数趋势（从认知循环记录中提取，简化：从经验里找）
    meta_scores = [e.get("meta_score", 0) for e in exps if e.get("meta_score")]
    avg_meta = sum(meta_scores) / len(meta_scores) if meta_scores else 0

    return {
        "total_experiences": total,
        "reusable_lessons": len(reusable),
        "reuse_rate": round(len(reusable) / total, 2),
        "total_corrections": len(corrected),
        "correction_rate": round(len(corrected) / total, 2),
        "early_correction_rate": round(early_rate, 2),
        "recent_correction_rate": round(recent_rate, 2),
        "correction_trend": correction_trend,
        "avg_meta_cognition_score": round(avg_meta, 1),
        "preferences_learned": len(prefs),
        "verdict": "明烛在进步" if recent_rate < early_rate else "需更多数据或关注",
    }


def reset_session(session_id: str = "default"):
    """重置内存中的图状态（不影响已持久化的文件记忆）"""
    global _graph
    _graph = None


def _should_clarify(user_input: str, router) -> str:
    """v3.5: 判断是否需要向用户澄清（人机协作）

    触发条件：输入模糊、缺乏关键信息、有多种理解可能。
    返回澄清问题字符串，不需要澄清时返回空字符串。
    为控制成本，只在输入很短或含模糊词时触发LLM判断。
    """
    # 快速规则判断：太短或含模糊词
    ambiguous_words = ["那个", "这个", "它", "之前说的", "刚才", "帮我看看", "分析一下"]
    is_ambiguous = (
        len(user_input) < 15 or
        any(w in user_input for w in ambiguous_words)
    )
    if not is_ambiguous:
        return ""

    try:
        from .llm_backends import Scene
        resp = router.generate(
            prompt=f"""判断以下用户输入是否需要澄清才能回答。
如果需要，返回一个具体的澄清问题（只返回问题，不要其他内容）。
如果不需要澄清，只返回"NO"。

用户输入：{user_input}""",
            scene=Scene.ROUTING, max_tokens=80,
        )
        if resp.ok and resp.content.strip() and resp.content.strip() != "NO":
            return resp.content.strip()[:150]
    except Exception:
        pass
    return ""


def chat_stream(user_input: str, session_id: str = "default",
                clarify_callback=None):
    """流式对话接口（生成器，逐步 yield 进度）

    v3.5 新增 clarify_callback：人机协作回调。
    当明烛需要澄清时，yield clarify 事件，调用方可通过 clarify_callback
    获取用户输入后继续。CLI 传 input() 回调，Web 传异步收集回调。

    Args:
        clarify_callback: 可选，签名 (question: str) -> str，返回用户回答。
                         为 None 时，clarify 事件直接 yield，由调用方处理。

    yield 的事件类型：
    - routing / schedule / tool / persona_start / persona_done / synthesizing / output / observer / done
    - clarify（v3.5新增）: {"type":"clarify","question":"...","persona":"乾断"}
    """
    import time as _time
    from .langgraph_engine import MingZhuGraph, PERSONAS
    from .llm_backends import Scene

    graph = _get_graph()
    start = _time.time()

    # 阶段1：路由
    state = {"user_input": user_input, "context": "", "thread_id": session_id}
    route_result = graph._node_route(state)
    persona_ids = route_result["persona_ids"]
    yield {"type": "routing", "method": route_result.get("routing_method", ""),
           "personas": [PERSONAS[p]["name"] for p in persona_ids]}

    # v3.5: 人机协作——判断是否需要澄清
    needs_clarify = _should_clarify(user_input, graph.router)
    if needs_clarify:
        question = needs_clarify
        yield {"type": "clarify", "question": question, "persona": "明烛"}
        if clarify_callback:
            try:
                answer = clarify_callback(question)
                if answer:
                    user_input = f"{user_input}\n[用户补充：{answer}]"
            except Exception:
                pass

    # 阶段2：工具调用
    tool_ctx = graph._maybe_call_tools(persona_ids, user_input)
    if tool_ctx:
        for line in tool_ctx.split("\n\n"):
            if line.startswith("["):
                end = line.find("]")
                if end > 0:
                    yield {"type": "tool", "info": line[:end+1], "detail": line[end+1:][:200]}

    # 阶段3：走完整5阶段图（initiation→planning→[memory/learn]→execution→review→retrospective）
    context = tool_ctx
    full_state = {
        "user_input": user_input,
        "context": context,
        "thread_id": session_id,
    }
    # 调用完整图
    full_result = graph.invoke(user_input, thread_id=session_id)
    persona_results = full_result.get("persona_results", [])
    schedule = full_result.get("schedule", {})

    if schedule:
        yield {"type": "schedule", "strategy": schedule.get("strategy", ""),
               "groups": schedule.get("groups", []),
               "reason": schedule.get("reason", "")}

    for r in persona_results:
        yield {"type": "persona_done", "name": r.get("name", ""),
               "content": r.get("content", ""), "confidence": r.get("confidence", "")}

    # 阶段4：安全检查 + 冲突检测（从完整结果取）
    state = {"persona_results": persona_results, "final_output": full_result.get("final_output", "")}
    safety = graph._node_safety_check(state)
    conflicts = graph._node_conflict_check(state)

    # 阶段5：汇总
    yield {"type": "synthesizing"}
    state.update({"user_input": user_input, "conflicts": conflicts, **safety})
    synth = graph._node_synthesize(state)
    output = synth["final_output"]
    yield {"type": "output", "content": output}

    # 阶段6：坎观观察
    state["final_output"] = output
    obs = graph._node_observe(state)
    yield {"type": "observer", "content": obs.get("observer_report", "")}

    # 阶段7：完成 + 自评
    latency = (_time.time() - start) * 1000
    models = list(set(r.get("model", "") for r in persona_results if r.get("model")))

    # 持久化记忆
    try:
        from .memory import get_memory, MemoryEntry
        entry = MemoryEntry(
            timestamp=_time.strftime("%Y-%m-%d %H:%M:%S"),
            user_input=user_input, output=output,
            personas=[{"name": r["name"], "model": r.get("model", "")} for r in persona_results],
            models=models, observer=obs.get("observer_report", ""),
            latency_ms=round(latency, 1),
        )
        get_memory().save_turn(session_id, entry)
    except Exception:
        pass

    # v3.6: 明烛自评
    self_score = {}
    try:
        self_score = _self_evaluate(
            user_input, output, obs.get("observer_report", ""),
            [{"name": r["name"]} for r in persona_results], graph.router,
        )
    except Exception:
        pass

    yield {"type": "done", "latency_ms": round(latency, 1), "models": models,
           "self_score": self_score}


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
