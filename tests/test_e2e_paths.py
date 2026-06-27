#!/usr/bin/env python3
"""
明烛 E2E 三路径测试 v4.7
真实LLM调用，验证三条执行路径物理跑通。

路径1：直线流水线（Pipeline）—— 报告生成类
路径2：ReAct循环 —— 搜索调研类
路径3：多人格协作（DISCUSS）—— 复杂讨论类

与GAIA测试的区别：GAIA测能力，E2E测路径是否跑通（不挂不崩）。
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_HAS_LLM = bool(os.environ.get("ZHIPU_API_KEY") or os.environ.get("DEEPSEEK_API_KEY"))


def test_pipeline_path():
    """路径1：直线流水线"""
    print("=== 路径1：直线流水线（Pipeline）===")
    if not _HAS_LLM:
        print("  ⏭️ 跳过（无API key）"); return True
    from agent_system.api import chat
    start = time.time()
    try:
        output = chat("总结JWT认证的3个核心优点", session_id="e2e-pipeline")
        latency = time.time() - start
        ok = len(output) > 50 and not output.startswith("（")
        print(f"  {'✅' if ok else '❌'} 耗时{latency:.1f}s 输出{len(output)}字")
        print(f"     前80字: {output[:80]}")
        return ok
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        return False


def test_react_path():
    """路径2：ReAct循环"""
    print("\n=== 路径2：ReAct循环 ===")
    if not _HAS_LLM:
        print("  ⏭️ 跳过（无API key）"); return True
    from agent_system.execution_strategy import ReactStrategy, select_strategy, ExecutionStrategyType
    from agent_system.llm_backends import get_router
    strategy_type = select_strategy("搜索LangGraph最新特性")
    if strategy_type != ExecutionStrategyType.REACT:
        print(f"  ⚠️ 策略选择不符: {strategy_type}")
    start = time.time()
    try:
        react = ReactStrategy(get_router())
        result = react.execute("什么是Python的GIL", "", get_router())
        latency = time.time() - start
        ok = bool(result.get("output")) and result.get("strategy") == "react"
        print(f"  {'✅' if ok else '❌'} 耗时{latency:.1f}s 迭代{result.get('iterations',0)}次")
        print(f"     前80字: {result.get('output','')[:80]}")
        return ok
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        return False


def test_collaboration_path():
    """路径3：多人格协作"""
    print("\n=== 路径3：多人格协作（DISCUSS）===")
    if not _HAS_LLM:
        print("  ⏭️ 跳过（无API key）"); return True
    from agent_system.api import chat_with_details
    start = time.time()
    try:
        result = chat_with_details(
            "从工程、安全、商业三个角度讨论：初创公司该不该用微服务",
            session_id="e2e-collab"
        )
        latency = time.time() - start
        personas = result.get("personas", [])
        ok = len(personas) >= 2 and len(result.get("output", "")) > 50
        print(f"  {'✅' if ok else '❌'} 耗时{latency:.1f}s 人格{len(personas)}个")
        print(f"     人格: {[p['name'] for p in personas]}")
        print(f"     自评: {result.get('self_score',{}).get('overall','?')}")
        return ok
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        return False


def run_e2e_tests():
    print("=" * 60)
    print("明烛 E2E 三路径测试 v4.7")
    print("=" * 60 + "\n")
    results = [
        ("Pipeline直线", test_pipeline_path()),
        ("ReAct循环", test_react_path()),
        ("多人格协作", test_collaboration_path()),
    ]
    print("\n" + "=" * 60)
    passed = sum(1 for _, ok in results if ok)
    print(f"E2E测试: {passed}/{len(results)} 通过")
    for name, ok in results:
        print(f"  {'✅' if ok else '❌'} {name}")
    return passed == len(results)


if __name__ == "__main__":
    ok = run_e2e_tests()
    sys.exit(0 if ok else 1)
