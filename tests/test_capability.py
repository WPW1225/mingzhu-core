#!/usr/bin/env python3
"""
明烛核心能力基准测试
覆盖基础问答、推理、代码生成等场景。
"""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_system import MingZhu


# 核心能力基准测试用例
CAPABILITY_CASES = [
    {
        "id": "CB001",
        "category": "basic_qa",
        "input": "什么是递归？",
        "expected_personas": ["li_ming"],
        "description": "基础问答：解释概念",
    },
    {
        "id": "CB002",
        "category": "reasoning",
        "input": "分析一下这个方案的利弊：微服务架构vs单体架构",
        "expected_personas": ["qian_duan", "xun_feng"],
        "description": "推理：权衡分析",
    },
    {
        "id": "CB003",
        "category": "code_generation",
        "input": "写一个Python函数实现快速排序",
        "expected_personas": ["zhen_zao"],
        "description": "代码生成：算法实现",
    },
    {
        "id": "CB004",
        "category": "research",
        "input": "调研一下React和Vue的优缺点",
        "expected_personas": ["xun_feng"],
        "description": "调研：技术对比",
    },
    {
        "id": "CB005",
        "category": "safety_review",
        "input": "审查这段代码的安全性：eval(user_input)",
        "expected_personas": ["gen_shou", "zhen_zao"],
        "description": "安全审查：代码审计",
    },
    {
        "id": "CB006",
        "category": "creative",
        "input": "头脑风暴：如何优化这个系统的性能",
        "expected_personas": ["dui_ze"],
        "description": "创意：发散思维",
    },
    {
        "id": "CB007",
        "category": "communication",
        "input": "把这段技术文档改写得更易懂",
        "expected_personas": ["li_ming"],
        "description": "沟通：文档优化",
    },
    {
        "id": "CB008",
        "category": "management",
        "input": "规划一个新功能的开发流程",
        "expected_personas": ["kun_zai"],
        "description": "管理：项目规划",
    },
    {
        "id": "CB009",
        "category": "observation",
        "input": "审查这个多人格协作的决策质量",
        "expected_personas": ["kan_guan"],
        "description": "观察：元认知审查",
    },
    {
        "id": "CB010",
        "category": "complex_collaboration",
        "input": "设计并实现一个用户认证系统，需要调研、架构、安全审查",
        "expected_personas": ["xun_feng", "zhen_zao", "gen_shou", "kun_zai"],
        "description": "复杂协作：多人格联合",
    },
]


def test_capability_routing():
    """测试能力路由准确性"""
    mz = MingZhu()
    print(f"=== 核心能力路由测试（共 {len(CAPABILITY_CASES)} 个用例）===\n")

    results = []
    passed = 0

    for case in CAPABILITY_CASES:
        routed = set(mz.route(case["input"]))
        expected = set(case["expected_personas"])

        # 检查是否路由到了期望的人格（至少包含一个）
        overlap = routed & expected
        status = "PASS" if overlap else "FAIL"

        # 坎观应该总是被路由到（作为观察者）
        has_observer = "kan_guan" in routed

        result = {
            "case_id": case["id"],
            "category": case["category"],
            "description": case["description"],
            "input": case["input"],
            "expected_personas": list(expected),
            "routed_personas": list(routed),
            "overlap": list(overlap),
            "has_observer": has_observer,
            "status": status,
        }
        results.append(result)

        icon = "✅" if status == "PASS" else "❌"
        print(f"{icon} {case['id']} ({case['category']})")
        print(f"   输入：{case['input'][:50]}")
        print(f"   期望：{', '.join(expected)}")
        print(f"   路由：{', '.join(routed)}")
        print(f"   观察者：{'有' if has_observer else '无'}")
        print()

        if status == "PASS":
            passed += 1

    print(f"=== 测试汇总 ===")
    print(f"通过：{passed}/{len(CAPABILITY_CASES)}（{passed/len(CAPABILITY_CASES)*100:.1f}%）")

    output_path = os.path.join(os.path.dirname(__file__), "test_results_capability.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"详细结果已保存到：{output_path}")

    return passed, len(CAPABILITY_CASES)


if __name__ == "__main__":
    passed, total = test_capability_routing()
    sys.exit(0 if passed == total else 1)
