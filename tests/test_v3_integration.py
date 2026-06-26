#!/usr/bin/env python3
"""
明烛 v3.0 集成测试
验证 LangGraph 引擎 + LLM 后端 + 工具系统的端到端集成。

测试维度：
1. LLM 后端：智谱可用、DeepSeek 降级、场景路由
2. 工具系统：calculator/code_execute/file_read/安全拦截
3. LangGraph 引擎：状态图流程、多轮记忆、冲突检测
4. 端到端：真实 LLM 调用 + 人格调度 + 汇总输出
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_system.llm_backends import get_router, Scene
from agent_system.tools import get_registry
from agent_system.langgraph_engine import MingZhuGraph

# v3.9.1: CI 环境无 API key 时跳过需真实 LLM 的测试
_HAS_LLM = bool(os.environ.get("ZHIPU_API_KEY") or os.environ.get("DEEPSEEK_API_KEY"))
_SKIP_REASON = "需要 ZHIPU_API_KEY 或 DEEPSEEK_API_KEY 环境变量（CI无key时跳过）"


# ============================================================
# 测试1：LLM 后端
# ============================================================

def test_llm_backends():
    print("=== 测试1：LLM 后端 ===")
    if not _HAS_LLM:
        print(f"  ⏭️ 跳过（{_SKIP_REASON}）")
        return 0, 0
    router = get_router()
    passed = 0
    total = 0

    # 1.1 智谱后端可用
    total += 1
    resp = router.generate("回复OK", scene=Scene.DEFAULT)
    assert resp.ok, f"智谱应可用，error={resp.error}"
    assert resp.backend == "zhipu", f"默认应路由到智谱，实际{resp.backend}"
    print(f"  ✅ 智谱后端可用（model={resp.model}）")
    passed += 1

    # 1.2 DeepSeek 状态正确（未激活时降级）
    total += 1
    status = router.status()
    assert "zhipu" in status and "deepseek" in status
    print(f"  ✅ 双后端状态：智谱={status['zhipu']['available']}, DeepSeek={status['deepseek']['available']}")
    passed += 1

    # 1.3 场景路由：SAFETY 场景应路由到智谱
    total += 1
    resp = router.generate("这是安全测试", scene=Scene.SAFETY)
    assert resp.backend == "zhipu", f"安全场景应用智谱，实际{resp.backend}"
    print(f"  ✅ SAFETY 场景路由到智谱")
    passed += 1

    # 1.4 调用日志记录
    total += 1
    logs = router.get_call_log()
    assert len(logs) >= 2, f"应有≥2条日志，实际{len(logs)}"
    # 验证日志结构完整
    if logs:
        log = logs[-1]
        assert "scene" in log and "backend" in log and "ok" in log, f"日志结构不完整：{log}"
    print(f"  ✅ 调用日志记录（{len(logs)}条，结构完整）")
    passed += 1

    print(f"  → LLM 后端：{passed}/{total} 通过\n")
    return passed, total


# ============================================================
# 测试2：工具系统
# ============================================================

def test_tools():
    print("=== 测试2：工具系统 ===")
    reg = get_registry()
    passed = 0
    total = 0

    # 2.1 calculator
    total += 1
    r = reg.call("calculator", expression="3 * 7 + 1")
    assert r.success and "22" in r.output, f"calculator 应返回22，实际{r.output}"
    print(f"  ✅ calculator: 3*7+1={r.output.strip()}")
    passed += 1

    # 2.2 code_execute 正常
    total += 1
    r = reg.call("code_execute", code="print(sum(range(10)))")
    assert r.success and "45" in r.output, f"应返回45，实际{r.output}"
    print(f"  ✅ code_execute: sum(range(10))={r.output.strip()}")
    passed += 1

    # 2.3 code_execute 安全拦截
    total += 1
    r = reg.call("code_execute", code="import os; os.system('ls')")
    assert not r.success, "含 os.system 应被拦截"
    assert "禁止" in r.error or "拦截" in r.error, f"应提示禁止，实际{r.error}"
    print(f"  ✅ 安全拦截：import os 被拒绝")
    passed += 1

    # 2.4 file_read
    total += 1
    r = reg.call("file_read", path="SOUL.md")
    assert r.success and "明烛" in r.output, f"应读到明烛，实际{r.output[:50]}"
    print(f"  ✅ file_read: 读取 SOUL.md 成功")
    passed += 1

    # 2.5 工具权限：巽风只能用 web_search
    total += 1
    xun_feng_tools = reg.get_tools_for_persona("xun_feng")
    assert "web_search" in xun_feng_tools, "巽风应有 web_search"
    assert "code_execute" not in xun_feng_tools, "巽风不应有 code_execute"
    print(f"  ✅ 工具权限：巽风={xun_feng_tools}")
    passed += 1

    print(f"  → 工具系统：{passed}/{total} 通过\n")
    return passed, total


# ============================================================
# 测试3：LangGraph 引擎
# ============================================================

def test_langgraph_engine():
    print("=== 测试3：LangGraph 引擎（真实 LLM）===")
    if not _HAS_LLM:
        print(f"  ⏭️ 跳过（{_SKIP_REASON}）")
        return 0, 0
    passed = 0
    total = 0

    graph = MingZhuGraph()

    # 3.1 状态图构建
    total += 1
    assert graph.graph is not None, "状态图应构建成功"
    print(f"  ✅ 状态图构建成功")
    passed += 1

    # 3.2 端到端调用（真实 LLM）
    total += 1
    result = graph.invoke("1+1等于几", thread_id="test-integration")
    assert "final_output" in result, "应有最终输出"
    assert len(result.get("final_output", "")) > 10, "输出不应为空"
    assert "persona_results" in result, "应有人格结果"
    print(f"  ✅ 端到端调用成功（{len(result.get('persona_results', []))}个人格）")
    passed += 1

    # 3.3 多轮记忆（相同 thread_id）
    total += 1
    result2 = graph.invoke("刚才说的再详细点", thread_id="test-integration")
    assert "final_output" in result2, "第二轮应有输出"
    print(f"  ✅ 多轮记忆生效（相同 thread_id 第二轮成功）")
    passed += 1

    # 3.4 路由正确性
    total += 1
    result3 = graph.invoke("帮我分析这个商业模式", thread_id="test-routing")
    persona_ids = result3.get("persona_ids", [])
    assert "qian_duan" in persona_ids, f"商业应触发乾断，实际{persona_ids}"
    print(f"  ✅ 路由正确：商业模式→乾断（{persona_ids}）")
    passed += 1

    # 3.5 LLM 真实调用（非规则模式）
    total += 1
    persona_results = result3.get("persona_results", [])
    has_real_llm = any(r.get("backend") == "zhipu" for r in persona_results)
    assert has_real_llm, f"应真实调用 LLM，实际{[r.get('backend') for r in persona_results]}"
    print(f"  ✅ LLM 真实调用（backend=zhipu）")
    passed += 1

    # 3.6 坎观 LLM 深度审查（v3.1 新增）
    total += 1
    observer = result3.get("observer_report", "")
    # LLM审查报告应该比纯统计更长（含分析内容）
    assert len(observer) > 50, f"坎观观察报告应含LLM深度分析，实际过短：{observer}"
    print(f"  ✅ 坎观 LLM 深度审查（报告{len(observer)}字）")
    passed += 1

    # 3.7 统一入口 api.chat 可用
    total += 1
    from agent_system.api import chat
    reply = chat("回复OK", session_id="api-test")
    assert len(reply) > 0, "统一入口应返回非空回复"
    print(f"  ✅ 统一入口 api.chat 可用（回复{len(reply)}字）")
    passed += 1

    print(f"  → LangGraph 引擎：{passed}/{total} 通过\n")
    return passed, total


# ============================================================
# 主入口
# ============================================================

def test_v3_integration():
    print("=" * 70)
    print("明烛 v3.0 集成测试（LangGraph + LLM + 工具系统）")
    print("=" * 70 + "\n")

    total_passed = 0
    total_tests = 0

    for test_fn in [test_llm_backends, test_tools, test_langgraph_engine]:
        passed, total = test_fn()
        total_passed += passed
        total_tests += total

    print("=" * 70)
    print(f"v3.0 集成测试汇总：{total_passed}/{total_tests} 通过")
    print("=" * 70)
    return total_passed, total_tests


if __name__ == "__main__":
    passed, total = test_v3_integration()
    sys.exit(0 if passed == total else 1)
