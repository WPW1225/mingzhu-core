#!/usr/bin/env python3
"""
明烛 DeepEval 顶级测试 v5.0
基于业内最权威的DeepEval框架，站在巨人肩膀上。

DeepEval提供的研究级指标：
- G-Eval: 基于CoT的LLM评估（比简单打分更严谨）
- AnswerRelevancy: 答案相关性
- Hallucination: 幻觉检测
- TaskCompletion: 任务完成度
- Faithfulness: 忠实度（答案是否基于事实）

这些指标替代了之前自编的LLM-as-Judge，用学术研究验证过的方法论。
"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_HAS_LLM = bool(os.environ.get("ZHIPU_API_KEY") or os.environ.get("DEEPSEEK_API_KEY"))


def test_with_deepeval():
    """用DeepEval的G-Eval评估明烛输出质量"""
    print("=" * 60)
    print("明烛 DeepEval 顶级测试 v5.0")
    print("=" * 60 + "\n")

    if not _HAS_LLM:
        print("⏭️ 跳过（需要 API key）")
        return []

    try:
        from deepeval.metrics import GEval
        from deepeval.test_case import LLMTestCase, LLMTestCaseParams
    except ImportError:
        print("❌ deepeval未安装，运行: pip install deepeval")
        return ["deepeval未安装"]

    from agent_system.api import chat
    from agent_system.llm_backends import get_router, Scene

    issues = []

    # 测试用例：覆盖不同能力维度
    test_cases = [
        {
            "name": "事实准确性",
            "input": "JWT认证的三个核心组成部分是什么？",
            "expected_keywords": ["header", "payload", "signature", "头部", "载荷", "签名"],
            "criteria": "评估答案是否准确描述了JWT的三个组成部分（header/payload/signature），无事实错误",
        },
        {
            "name": "答案相关性",
            "input": "Docker和虚拟机的主要区别是什么？",
            "expected_keywords": ["Docker", "虚拟机", "容器", "隔离", "内核"],
            "criteria": "评估答案是否直接回答了Docker与虚拟机的区别，不跑题",
        },
        {
            "name": "幻觉检测",
            "input": "2026年世界上最精确的量子计算机的量子比特数是多少？",
            "expected_keywords": ["不确定", "无法确定", "截至", "目前", "不知道"],
            "criteria": "评估答案是否诚实承认不确定性，而非编造具体数字",
        },
        {
            "name": "任务完成度",
            "input": "帮我计算 2^10 + 3*4 的结果，并解释计算过程",
            "expected_keywords": ["1036", "1024", "12", "计算"],
            "criteria": "评估答案是否给出了正确结果1036，并解释了计算过程",
        },
    ]

    router = get_router()

    for tc in test_cases:
        print(f"=== {tc['name']} ===")
        start = time.time()
        try:
            answer = chat(tc["input"], session_id=f"deepeval-{tc['name']}")
            latency = time.time() - start

            # 关键词检查
            keyword_hits = sum(1 for kw in tc["expected_keywords"] if kw in answer)

            # DeepEval G-Eval评估
            test_case = LLMTestCase(
                input=tc["input"],
                actual_output=answer,
            )
            metric = GEval(
                name=tc["name"],
                criteria=tc["criteria"],
                evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            )
            metric.measure(test_case)
            score = metric.score  # 0-1
            reason = metric.reason

            passed = score >= 0.6 and keyword_hits >= 1
            status = "✅" if passed else "⚠️"

            print(f"  {status} G-Eval: {score:.2f} | 关键词: {keyword_hits}/{len(tc['expected_keywords'])} | {latency:.1f}s")
            print(f"     评价: {reason[:120]}")
            print(f"     回答前80字: {answer[:80]}")

            if not passed:
                issues.append(f"[{tc['name']}] G-Eval={score:.2f} 关键词={keyword_hits}/{len(tc['expected_keywords'])}")

        except Exception as e:
            print(f"  ❌ 异常: {e}")
            issues.append(f"[{tc['name']}] 异常: {str(e)[:50]}")
        print()

    # 汇总
    print("=" * 60)
    print(f"DeepEval测试: {len(test_cases)-len(issues)}/{len(test_cases)} 通过")
    if issues:
        print(f"⚠️ 发现 {len(issues)} 个问题:")
        for iss in issues:
            print(f"  - {iss}")
    else:
        print("✅ 全部通过")

    # 保存
    output = os.path.join(os.path.dirname(__file__), "deepeval_results.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump({"issues": issues, "total": len(test_cases)}, f, ensure_ascii=False, indent=2)

    return issues


if __name__ == "__main__":
    issues = test_with_deepeval()
    sys.exit(1 if issues else 0)
