#!/usr/bin/env python3
"""
明烛认知循环测试 v2.1
验证 CognitiveCycle 类是否正确强制执行"预见→执行→反思"三阶段，
以及执行驱动信号检测是否生效。

测试维度：
1. 配置完整性：三阶段配置是否齐全
2. 预见阶段：任务分析4问 + 偏差预检是否就绪
3. 执行驱动检测：检测到信号时是否主动刹车
4. 强制执行：enforce_strict=True 时跳过阶段是否报错
5. 完整循环：run() 是否依次完成三阶段并产出记录
6. 反思阶段：三段式复盘是否完整
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_system.cognitive_cycle import CognitiveCycle, CycleResult, PhaseRecord


def test_config_integrity():
    """测试1：认知循环配置完整性"""
    print("=== 测试1：认知循环配置完整性 ===")
    cycle = CognitiveCycle()
    cfg = cycle.config

    checks = []
    # 模型
    assert cfg.get("model") == "Zimmerman_SRL", f"模型应为 Zimmerman_SRL，实际 {cfg.get('model')}"
    checks.append(("模型 = Zimmerman_SRL", True))

    # 三阶段都存在且 required
    for phase in ["forethought", "performance", "reflection"]:
        assert phase in cfg, f"缺少阶段：{phase}"
        assert cfg[phase].get("required") is True, f"{phase} 应为 required"
        checks.append((f"阶段 {phase} 存在且 required", True))

    # 预见阶段4问
    ft_qs = cycle.get_forethought_questions()
    assert len(ft_qs) >= 7, f"预见问题应≥7（4任务分析+3偏差预检），实际 {len(ft_qs)}"
    checks.append((f"预见问题数 = {len(ft_qs)} (≥7)", True))

    # 反思三段式
    ref_qs = cycle.get_reflection_questions()
    ref_ids = [q["id"] for q in ref_qs]
    assert ref_ids == ["factual", "cognitive", "iterative"], f"反思三段式顺序错误：{ref_ids}"
    checks.append((f"反思三段式 = {ref_ids}", True))

    # 执行阶段固定任务
    tasks = cycle.get_fixed_tasks()
    assert len(tasks) >= 6, f"固定任务应≥6，实际 {len(tasks)}"
    task_ids = [t["id"] for t in tasks]
    assert "must_push" in task_ids, "缺少 must_push 任务"
    assert "full_test" in task_ids, "缺少 full_test 任务"
    checks.append((f"固定任务数 = {len(tasks)} (≥6)，含 must_push/full_test", True))

    for name, ok in checks:
        print(f"  ✅ {name}")

    print(f"  → 配置完整性测试通过（{len(checks)} 项）\n")
    return len(checks), len(checks)


def test_execution_drive_detection():
    """测试2：执行驱动信号检测"""
    print("=== 测试2：执行驱动信号检测 ===")
    cycle = CognitiveCycle()
    signals = cycle.config["forethought"]["execution_drive_signals"]

    assert len(signals) >= 5, f"执行驱动信号应≥5，实际 {len(signals)}"
    print(f"  ✅ 配置了 {len(signals)} 个执行驱动触发信号")

    # 模拟一个"执行驱动"的预见回答（跳过目标对齐直接动手）
    forethought_answers = {
        "goal_clarity": "",  # 没回答目标 → 执行驱动特征
        "complexity_assessment": "简单执行",
        "info_sufficiency": "直接开始",
        "persona_routing": "震造",
    }
    warnings = cycle._detect_execution_drive(forethought_answers)
    assert len(warnings) > 0, "目标未回答应触发执行驱动警告"
    print(f"  ✅ 目标未回答 → 检测到 {len(warnings)} 个执行驱动警告")

    # 模拟一个"正常"的预见回答
    good_answers = {
        "goal_clarity": "给项目增加 CI 测试，确保每次提交自动运行测试",
        "complexity_assessment": "复杂协作（涉及配置+测试+文档）",
        "info_sufficiency": "信息充分，已读取现有测试结构",
        "persona_routing": "震造（实现）+ 艮守（审查）+ 离明（文档）",
    }
    warnings_good = cycle._detect_execution_drive(good_answers)
    assert len(warnings_good) == 0, f"正常回答不应触发警告，实际触发 {len(warnings_good)}"
    print(f"  ✅ 目标清晰 → 无执行驱动警告")

    print("  → 执行驱动检测测试通过\n")
    return 3, 3


def test_strict_enforcement():
    """测试3：enforce_strict 强制执行——跳过阶段应报错"""
    print("=== 测试3：enforce_strict 强制执行 ===")
    cycle = CognitiveCycle()
    assert cycle.config.get("enforce_strict") is True, "enforce_strict 应为 True"
    print("  ✅ enforce_strict = True")

    # 模拟跳过预见阶段直接执行 → 应报错
    try:
        cycle.run(
            task="测试任务",
            forethought_fn=None,  # 跳过预见
            execute_fn=lambda: {"output": "done"},
        )
        assert False, "跳过预见阶段应抛出 ValueError"
    except ValueError as e:
        assert "预见" in str(e) or "forethought" in str(e).lower(), f"错误信息应提及预见阶段：{e}"
        print(f"  ✅ 跳过预见阶段 → 正确抛出 ValueError")

    # 模拟跳过反思阶段（不提供反思函数，enforce_strict 应自动要求）
    # 这里测试 run 在没有 reflect_fn 时会自动生成空反思并标记 skipped
    result = cycle.run(
        task="测试任务",
        forethought_fn=lambda: {
            "goal_clarity": "测试", "complexity_assessment": "简单",
            "info_sufficiency": "充分", "persona_routing": "震造"
        },
        execute_fn=lambda: {"output": "done"},
        reflect_fn=None,  # 不提供反思函数
    )
    # enforce_strict 下，反思阶段不能被跳过 → 应标记为未完成
    assert result.reflection.completed is False or result.reflection.skipped is True, \
        "enforce_strict 下未提供反思函数应标记反思未完成"
    print(f"  ✅ 未提供反思函数 → 反思阶段标记为未完成（enforce_strict 生效）")

    print("  → 强制执行测试通过\n")
    return 2, 2


def test_full_cycle():
    """测试4：完整认知循环"""
    print("=== 测试4：完整认知循环 ===")
    cycle = CognitiveCycle()

    forethought_result = {
        "goal_clarity": "验证认知循环三阶段强制执行",
        "complexity_assessment": "复杂协作（配置+代码+测试+文档）",
        "info_sufficiency": "已读取 soul_config.yaml 和现有架构",
        "persona_routing": "震造（实现）+ 坎观（审查）+ 离明（文档）",
    }
    execute_result = {
        "output": "cognitive_cycle.py 已创建，测试通过",
        "files_changed": 3,
        "tests_passed": True,
    }
    reflection_result = {
        "factual": "完成了认知循环的结构化和测试，所有测试通过",
        "cognitive": "一开始有执行驱动倾向，建TODO后才回到正轨",
        "iterative": "教训：收到复杂任务先做预见4问，不要直接动手",
    }

    result = cycle.run(
        task="实现认知循环结构化",
        forethought_fn=lambda: forethought_result,
        execute_fn=lambda: execute_result,
        reflect_fn=lambda: reflection_result,
    )

    # 验证三阶段都完成
    assert result.forethought.completed is True, "预见阶段应完成"
    assert result.performance.completed is True, "执行阶段应完成"
    assert result.reflection.completed is True, "反思阶段应完成"
    print("  ✅ 三阶段全部完成")

    # 验证记录内容
    assert result.forethought.answers["goal_clarity"] == forethought_result["goal_clarity"]
    assert result.performance.answers["output"] == execute_result["output"]
    assert result.reflection.answers["factual"] == reflection_result["factual"]
    print("  ✅ 各阶段记录内容正确")

    # 验证可序列化
    d = result.to_dict()
    assert "forethought" in d and "performance" in d and "reflection" in d
    assert d["all_completed"] is True
    print("  ✅ 结果可序列化为 dict，all_completed = True")

    print("  → 完整循环测试通过\n")
    return 3, 3


def test_cognitive_cycle():
    """认知循环测试主入口"""
    print("=" * 70)
    print("明烛认知循环测试 v2.1")
    print("=" * 70 + "\n")

    total_passed = 0
    total_tests = 0

    for test_fn in [
        test_config_integrity,
        test_execution_drive_detection,
        test_strict_enforcement,
        test_full_cycle,
    ]:
        passed, total = test_fn()
        total_passed += passed
        total_tests += total

    print("=" * 70)
    print(f"认知循环测试汇总：{total_passed}/{total_tests} 通过")
    print("=" * 70)
    return total_passed, total_tests


if __name__ == "__main__":
    passed, total = test_cognitive_cycle()
    sys.exit(0 if passed == total else 1)
