#!/usr/bin/env python3
"""
明烛健壮性测试 v2.2
验证基于 AgentBench 等业内评测标准诊断出的问题修复：
1. 目标漂移检测（P0-3）：CognitiveCycle.detect_goal_drift
2. 失败恢复（P1-6）：MingZhu._execute_persona 的 retry + fallback
3. 冲突检测（P1-5）：MingZhu._detect_conflicts
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_system.cognitive_cycle import CognitiveCycle
from agent_system import MingZhu, AgentResult


# ============================================================
# 测试1：目标漂移检测
# ============================================================

def test_goal_drift_detection():
    print("=== 测试1：目标漂移检测 ===")
    cycle = CognitiveCycle()
    passed = 0
    total = 0

    # 1.1 高度相关——不应漂移
    total += 1
    goal = "给项目增加 CI 测试和自动化部署"
    output = "已为项目增加 GitHub Actions CI 测试，配置了自动化部署流程，测试全部通过。"
    drift = cycle.detect_goal_drift(goal, output)
    assert drift["drifted"] is False, f"高度相关不应漂移，覆盖率={drift['coverage']}"
    assert drift["coverage"] > 0.3, f"覆盖率应>0.3，实际{drift['coverage']}"
    print(f"  ✅ 高度相关不漂移（覆盖率={drift['coverage']}）")
    passed += 1

    # 1.2 完全无关——应漂移
    total += 1
    goal = "给项目增加 CI 测试和自动化部署"
    output = "今天天气很好，我去公园散步，看到了很多小鸟和花朵。"
    drift = cycle.detect_goal_drift(goal, output)
    assert drift["drifted"] is True, f"完全无关应漂移，覆盖率={drift['coverage']}"
    assert drift["coverage"] < 0.3, f"覆盖率应<0.3，实际{drift['coverage']}"
    assert "目标漂移警告" in drift["warning"], "漂移时应含警告"
    print(f"  ✅ 完全无关触发漂移（覆盖率={drift['coverage']}）")
    passed += 1

    # 1.3 部分相关——边界情况
    total += 1
    goal = "优化代码架构，增加测试覆盖"
    output = "优化了代码架构，重构了模块。"
    drift = cycle.detect_goal_drift(goal, output, threshold=0.3)
    # 部分相关，覆盖率和相似度应在0-1之间
    assert 0 <= drift["coverage"] <= 1, "覆盖率应在[0,1]"
    assert 0 <= drift["similarity"] <= 1, "相似度应在[0,1]"
    print(f"  ✅ 部分相关边界正确（覆盖率={drift['coverage']}，漂移={drift['drifted']}）")
    passed += 1

    # 1.4 空目标——不漂移
    total += 1
    drift = cycle.detect_goal_drift("", "任意输出")
    assert drift["drifted"] is False, "空目标不应漂移"
    assert drift["coverage"] == 1.0, "空目标覆盖率应为1.0"
    print(f"  ✅ 空目标不漂移")
    passed += 1

    # 1.5 missing 关键词正确计算
    total += 1
    goal = "增加 CI 测试"
    output = "增加了部署"
    drift = cycle.detect_goal_drift(goal, output)
    assert "测试" in drift["missing"], f"missing 应含'测试'，实际{drift['missing']}"
    print(f"  ✅ missing 关键词正确：{drift['missing']}")
    passed += 1

    print(f"  → 目标漂移检测：{passed}/{total} 通过\n")
    return passed, total


# ============================================================
# 测试2：失败恢复（retry + fallback）
# ============================================================

def test_retry_fallback():
    print("=== 测试2：失败恢复（retry + fallback）===")
    passed = 0
    total = 0

    mz = MingZhu()

    # 2.1 正常执行（LLM未启用，走规则模式，应成功）
    total += 1
    result = mz._execute_persona("qian_duan", "分析这个决策", max_retries=1)
    assert result.error is None or result.error == "", f"正常执行不应有error：{result.error}"
    assert result.content != "", "正常执行应有内容"
    print(f"  ✅ 正常执行成功（{result.name}）")
    passed += 1

    # 2.2 模拟持续失败 → fallback
    total += 1
    # 用一个会持续抛异常的 mock
    original_load = mz._load_persona
    call_count = {"n": 0}
    def failing_load(pid):
        call_count["n"] += 1
        raise RuntimeError(f"模拟失败 #{call_count['n']}")
    mz._load_persona = failing_load
    try:
        result = mz._execute_persona("qian_duan", "测试", max_retries=2)
        assert result.error is not None, "持续失败应有error"
        assert "重试" in result.error or "失败" in result.error, f"error应提及重试：{result.error}"
        assert result.confidence == "低", "fallback 置信度应为低"
        assert call_count["n"] == 3, f"应重试3次（1+2），实际{call_count['n']}"
        print(f"  ✅ 持续失败触发 fallback（重试{call_count['n']}次后降级，confidence=低）")
        passed += 1
    finally:
        mz._load_persona = original_load

    # 2.3 第二次重试成功
    total += 1
    call_count2 = {"n": 0}
    def fail_then_succeed(pid):
        call_count2["n"] += 1
        if call_count2["n"] == 1:
            raise RuntimeError("第一次失败")
        return original_load(pid)  # 第二次成功
    mz._load_persona = fail_then_succeed
    try:
        result = mz._execute_persona("qian_duan", "测试", max_retries=2)
        assert result.error is None or result.error == "", f"重试后成功不应有error：{result.error}"
        assert call_count2["n"] == 2, f"应在第2次成功，实际调用{call_count2['n']}次"
        print(f"  ✅ 重试后成功（第{call_count2['n']}次成功）")
        passed += 1
    finally:
        mz._load_persona = original_load

    print(f"  → 失败恢复：{passed}/{total} 通过\n")
    return passed, total


# ============================================================
# 测试3：冲突检测
# ============================================================

def test_conflict_detection():
    print("=== 测试3：冲突检测 ===")
    passed = 0
    total = 0

    mz = MingZhu()

    # 3.1 无冲突
    total += 1
    results = [
        AgentResult(persona="qian_duan", name="乾断", icon="☰",
                    content="建议采用方案A，可行性高。", confidence="高"),
        AgentResult(persona="zhen_zao", name="震造", icon="☳",
                    content="可以实现，推荐执行。", confidence="高"),
    ]
    conflicts = mz._detect_conflicts(results)
    assert conflicts == [], f"无冲突应返回空，实际{conflicts}"
    print(f"  ✅ 无冲突正确识别")
    passed += 1

    # 3.2 行动建议对立（建议 vs 否决）
    total += 1
    results = [
        AgentResult(persona="qian_duan", name="乾断", icon="☰",
                    content="建议立即执行这个方案。", confidence="高"),
        AgentResult(persona="gen_shou", name="艮守", icon="☶",
                    content="否决，存在安全风险。", confidence="高"),
    ]
    conflicts = mz._detect_conflicts(results)
    assert len(conflicts) >= 1, f"应检测到冲突，实际{conflicts}"
    assert "乾断" in conflicts[0] and "艮守" in conflicts[0], f"冲突应含人格名：{conflicts[0]}"
    print(f"  ✅ 检测到行动建议冲突：{conflicts[0]}")
    passed += 1

    # 3.3 安全判断对立
    total += 1
    results = [
        AgentResult(persona="zhen_zao", name="震造", icon="☳",
                    content="这个方案安全合规。", confidence="高"),
        AgentResult(persona="gen_shou", name="艮守", icon="☶",
                    content="这个方案有风险，存在漏洞。", confidence="高"),
    ]
    conflicts = mz._detect_conflicts(results)
    assert len(conflicts) >= 1, f"应检测到安全冲突，实际{conflicts}"
    print(f"  ✅ 检测到安全判断冲突：{conflicts[0]}")
    passed += 1

    # 3.4 单个人格不报冲突
    total += 1
    results = [
        AgentResult(persona="qian_duan", name="乾断", icon="☰",
                    content="建议做，但也不建议做。", confidence="中"),
    ]
    conflicts = mz._detect_conflicts(results)
    assert conflicts == [], "单个人格内部矛盾不应报跨人格冲突"
    print(f"  ✅ 单人格不报跨人格冲突")
    passed += 1

    # 3.5 error 的人格不参与冲突检测
    total += 1
    results = [
        AgentResult(persona="qian_duan", name="乾断", icon="☰",
                    content="建议执行。", confidence="高"),
        AgentResult(persona="gen_shou", name="艮守", icon="☶",
                    content="", confidence="低", error="执行失败"),
    ]
    conflicts = mz._detect_conflicts(results)
    assert conflicts == [], "error的人格不应参与冲突检测"
    print(f"  ✅ error人格不参与冲突检测")
    passed += 1

    print(f"  → 冲突检测：{passed}/{total} 通过\n")
    return passed, total


# ============================================================
# 主入口
# ============================================================

def test_robustness():
    print("=" * 70)
    print("明烛健壮性测试 v2.2（基于 AgentBench 等业内标准诊断）")
    print("=" * 70 + "\n")

    total_passed = 0
    total_tests = 0

    for test_fn in [test_goal_drift_detection, test_retry_fallback, test_conflict_detection]:
        passed, total = test_fn()
        total_passed += passed
        total_tests += total

    print("=" * 70)
    print(f"健壮性测试汇总：{total_passed}/{total_tests} 通过")
    print("=" * 70)
    return total_passed, total_tests


if __name__ == "__main__":
    passed, total = test_robustness()
    sys.exit(0 if passed == total else 1)
