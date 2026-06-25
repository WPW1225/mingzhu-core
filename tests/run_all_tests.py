#!/usr/bin/env python3
"""
明烛测试套件运行器
运行所有测试并汇总结果。
"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_all_tests():
    """运行所有测试"""
    print("=" * 70)
    print("明烛测试套件 v2.0")
    print("=" * 70)
    print()

    results = {}
    start_time = time.time()

    # 1. 红线测试
    print(">>> 运行红线遵守测试...")
    try:
        from tests.test_red_lines import test_red_line_cases, test_critical_red_lines
        passed, failed, total = test_red_line_cases()
        critical_ok = test_critical_red_lines()
        results["red_lines"] = {
            "passed": passed,
            "failed": failed,
            "total": total,
            "critical_ok": critical_ok,
            "status": "PASS" if critical_ok else "FAIL",
        }
    except Exception as e:
        results["red_lines"] = {"status": "ERROR", "error": str(e)}
        print(f"❌ 红线测试出错：{e}")
    print()

    # 2. 人格一致性测试
    print(">>> 运行人格一致性测试...")
    try:
        from tests.test_personality import test_personality_consistency
        passed, total = test_personality_consistency()
        results["personality"] = {
            "passed": passed,
            "total": total,
            "status": "PASS" if passed == total else "FAIL",
        }
    except Exception as e:
        results["personality"] = {"status": "ERROR", "error": str(e)}
        print(f"❌ 人格测试出错：{e}")
    print()

    # 3. 能力基准测试
    print(">>> 运行核心能力基准测试...")
    try:
        from tests.test_capability import test_capability_routing
        passed, total = test_capability_routing()
        results["capability"] = {
            "passed": passed,
            "total": total,
            "status": "PASS" if passed == total else "FAIL",
        }
    except Exception as e:
        results["capability"] = {"status": "ERROR", "error": str(e)}
        print(f"❌ 能力测试出错：{e}")
    print()

    # 4. 对抗性测试
    print(">>> 运行对抗性测试...")
    try:
        from tests.test_adversarial import test_adversarial
        critical_detected, critical_total = test_adversarial()
        results["adversarial"] = {
            "critical_detected": critical_detected,
            "critical_total": critical_total,
            "status": "PASS" if critical_detected == critical_total else "FAIL",
        }
    except Exception as e:
        results["adversarial"] = {"status": "ERROR", "error": str(e)}
        print(f"❌ 对抗性测试出错：{e}")
    print()

    # 5. 认知循环测试
    print(">>> 运行认知循环测试...")
    try:
        from tests.test_cognitive_cycle import test_cognitive_cycle
        passed, total = test_cognitive_cycle()
        results["cognitive_cycle"] = {
            "passed": passed,
            "total": total,
            "status": "PASS" if passed == total else "FAIL",
        }
    except Exception as e:
        results["cognitive_cycle"] = {"status": "ERROR", "error": str(e)}
        print(f"❌ 认知循环测试出错：{e}")
    print()

    # 6. 健壮性测试
    print(">>> 运行健壮性测试...")
    try:
        from tests.test_robustness import test_robustness
        passed, total = test_robustness()
        results["robustness"] = {
            "passed": passed,
            "total": total,
            "status": "PASS" if passed == total else "FAIL",
        }
    except Exception as e:
        results["robustness"] = {"status": "ERROR", "error": str(e)}
        print(f"❌ 健壮性测试出错：{e}")
    print()

    # 7. v3.0 集成测试（需真实 LLM，可能较慢）
    print(">>> 运行 v3.0 集成测试（LangGraph + LLM + 工具）...")
    try:
        from tests.test_v3_integration import test_v3_integration
        passed, total = test_v3_integration()
        results["v3_integration"] = {
            "passed": passed,
            "total": total,
            "status": "PASS" if passed == total else "FAIL",
        }
    except Exception as e:
        results["v3_integration"] = {"status": "ERROR", "error": str(e)}
        print(f"❌ v3.0 集成测试出错：{e}")
    print()

    # 汇总
    duration = time.time() - start_time
    print("=" * 70)
    print("测试汇总")
    print("=" * 70)

    all_pass = True
    for suite, result in results.items():
        status = result.get("status", "UNKNOWN")
        icon = "✅" if status == "PASS" else "❌"
        print(f"  {icon} {suite}: {status}")
        if status != "PASS":
            all_pass = False

    print(f"\n总耗时：{duration:.1f}s")
    print(f"总体结果：{'✅ ALL PASS' if all_pass else '❌ HAS FAILURES'}")

    # 保存汇总
    output_path = os.path.join(os.path.dirname(__file__), "test_summary.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": duration,
            "results": results,
            "overall": "PASS" if all_pass else "FAIL",
        }, f, ensure_ascii=False, indent=2)
    print(f"汇总已保存到：{output_path}")

    return all_pass


if __name__ == "__main__":
    # 创建 __init__.py 使 tests 成为包
    init_path = os.path.join(os.path.dirname(__file__), "__init__.py")
    if not os.path.exists(init_path):
        with open(init_path, "w") as f:
            f.write("")

    success = run_all_tests()
    sys.exit(0 if success else 1)
