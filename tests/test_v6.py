#!/usr/bin/env python3
"""
明烛 v6.0 新功能测试
验证 CognitiveState / Verdict / Critic 对抗闭环
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_cognitive_state():
    """测试1: CognitiveState统一状态"""
    print("=== 测试1: CognitiveState ===")
    from agent_system.cognitive_state import CognitiveState
    cs = CognitiveState(user_input="测试输入")
    cs.add_trace("test", "action1", "detail1")
    cs.add_trace("test", "action2", "detail2")
    d = cs.to_dict()
    assert d["user_input"] == "测试输入"
    assert d["trace_count"] == 2
    print("  ✅ CognitiveState创建+追踪+序列化正常")
    return True


def test_verdict():
    """测试2: Verdict裁决系统"""
    print("=== 测试2: Verdict裁决 ===")
    from agent_system.cognitive_state import determine_verdict, Verdict

    # 高分→ACCEPT
    assert determine_verdict(85) == Verdict.ACCEPT
    # 低分→REVISE
    assert determine_verdict(50) == Verdict.REVISE
    # 红线违规→REJECT
    assert determine_verdict(90, has_red_line_violation=True) == Verdict.REJECT
    # Critic致命→REJECT
    assert determine_verdict(90, has_critic_fatal=True) == Verdict.REJECT
    print("  ✅ Verdict三态裁决正确（accept/revise/reject）")
    return True


def test_critic_attack():
    """测试3: Critic对抗（无LLM时降级）"""
    print("=== 测试3: Critic对抗 ===")
    from agent_system.langgraph_engine import MingZhuGraph
    graph = MingZhuGraph()
    # 无persona_results时应返回空
    attacks = graph._critic_attack({"persona_results": []})
    assert attacks == [], "空输入应返回空攻击列表"
    print("  ✅ Critic空输入处理正常")
    return True


def test_verdict_in_review():
    """测试4: review节点输出verdict"""
    print("=== 测试4: review节点verdict ===")
    from agent_system.langgraph_engine import MingZhuGraph
    graph = MingZhuGraph()
    # 模拟review（无LLM）
    result = graph._node_review({
        "persona_results": [],
        "user_input": "test",
    })
    assert "review_verdict" in result, "review应输出verdict"
    assert "review_score" in result, "review应输出score"
    assert "critic_attacks" in result, "review应输出critic_attacks"
    print(f"  ✅ review输出: verdict={result['review_verdict']} score={result['review_score']}")
    return True


def run_v6_tests():
    print("=" * 60)
    print("明烛 v6.0 新功能测试")
    print("=" * 60 + "\n")
    tests = [test_cognitive_state, test_verdict, test_critic_attack, test_verdict_in_review]
    passed = 0
    for t in tests:
        try:
            if t():
                passed += 1
        except Exception as e:
            print(f"  ❌ {t.__name__}: {e}")
    print(f"\n{'='*60}")
    print(f"v6.0测试: {passed}/{len(tests)} 通过")
    return passed == len(tests)


if __name__ == "__main__":
    ok = run_v6_tests()
    sys.exit(0 if ok else 1)
