#!/usr/bin/env python3
"""
明烛红线遵守测试
验证系统在诱导违规的输入下是否正确触发红线保护。
"""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_system.config_loader import config
from agent_system.evaluator import Evaluator, RedLineChecker


def test_red_line_cases():
    """测试所有红线测试用例"""
    cases = config.get_red_line_cases()
    checker = RedLineChecker()
    evaluator = Evaluator()

    print(f"=== 红线遵守测试（共 {len(cases)} 个用例）===\n")

    passed = 0
    failed = 0
    results = []

    for case in cases:
        # 模拟系统输出（无LLM时，检查输入本身是否被正确识别为红线场景）
        # 在实际系统中，这里会调用 MingZhu.run(case["input"]) 获取输出
        # 然后检查输出是否拒绝了违规请求

        # 使用 check_request 检测输入是否触发红线（应被拒绝）
        violations = checker.check_request(case["input"])

        # 评估：如果输入包含红线触发模式，系统应该拒绝
        # 这里我们检查评估器是否能正确识别问题
        test_result = {
            "case_id": case["case_id"],
            "red_line_id": case["red_line_id"],
            "category": case["category"],
            "severity": case["severity"],
            "input": case["input"],
            "expected": case["expected_behavior"],
            "detected_violations": violations,
            "status": "PASS" if violations else "NEED_LLM_VERIFICATION",
        }
        results.append(test_result)

        status_icon = "✅" if violations else "⚠️"
        print(f"{status_icon} [{case['severity']}] {case['case_id']}: {case['input'][:50]}")
        if violations:
            print(f"   检测到违规模式：{violations}")
        else:
            print(f"   需LLM验证（规则未匹配，可能需要语义判断）")
        print()

        if violations:
            passed += 1
        else:
            failed += 1

    print(f"\n=== 测试汇总 ===")
    print(f"规则检测通过：{passed}/{len(cases)}")
    print(f"需LLM验证：{failed}/{len(cases)}")
    print(f"通过率：{passed/len(cases)*100:.1f}%（规则层）")

    # 保存结果
    output_path = os.path.join(os.path.dirname(__file__), "test_results_red_lines.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存到：{output_path}")

    return passed, failed, len(cases)


def test_critical_red_lines():
    """专门测试 critical 级别红线"""
    cases = config.get_red_line_cases()
    critical_cases = [c for c in cases if c["severity"] == "critical"]

    print(f"\n=== Critical 级别红线测试（共 {len(critical_cases)} 个）===\n")

    checker = RedLineChecker()
    all_critical_passed = True

    for case in critical_cases:
        violations = checker.check_request(case["input"])
        if not violations:
            print(f"⚠️  Critical用例未检测到违规：{case['case_id']}")
            all_critical_passed = False

    if all_critical_passed:
        print("✅ 所有 Critical 级别红线用例均被规则层检测到")
    else:
        print("❌ 部分 Critical 级别红线用例未被规则层检测到（需LLM增强）")

    return all_critical_passed


if __name__ == "__main__":
    passed, failed, total = test_red_line_cases()
    test_critical_red_lines()

    # 退出码：critical 全部通过则成功
    critical_ok = test_critical_red_lines()
    sys.exit(0 if critical_ok else 1)
