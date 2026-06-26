#!/usr/bin/env python3
"""
明烛元元认知 v3.4
对反思本身的反思——校验反思是否真的找出了问题，还是走过场。

为什么需要：
SOUL.md 要求三段式复盘（事实/思维/迭代），但没有机制验证复盘质量。
结果可能是：写了复盘但没找出真问题，或者教训太泛不可执行。
元元认知就是"反思的反思"——用LLM评估反思质量，给出分数和改进建议。

评估维度：
1. 具体性：反思是否指向具体行为，还是泛泛而谈
2. 根因性：是否找到根本原因，还是停留在表面
3. 可执行性：教训是否能转化为下次行动的改变
4. 诚实性：是否回避问题、自我表扬
5. 闭环性：是否形成"问题→原因→行动"的完整链条

评分：每个维度0-100，总分0-100。
<60：反思无效（走过场），需要重做
60-80：反思合格但可改进
>80：反思有效
"""
import json
import logging
from typing import Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ReflectionScore:
    """反思质量评分"""
    specificity: float = 0.0      # 具体性
    root_cause: float = 0.0       # 根因性
    actionability: float = 0.0    # 可执行性
    honesty: float = 0.0          # 诚实性
    closure: float = 0.0          # 闭环性
    overall: float = 0.0          # 总分
    verdict: str = ""             # 判定：invalid/valid/excellent
    critique: str = ""            # 批评意见
    suggestions: list = field(default_factory=list)  # 改进建议

    def to_dict(self) -> Dict:
        return {
            "dimensions": {
                "specificity": round(self.specificity, 1),
                "root_cause": round(self.root_cause, 1),
                "actionability": round(self.actionability, 1),
                "honesty": round(self.honesty, 1),
                "closure": round(self.closure, 1),
            },
            "overall": round(self.overall, 1),
            "verdict": self.verdict,
            "critique": self.critique,
            "suggestions": self.suggestions,
        }


def evaluate_reflection(
    factual: str,
    cognitive: str,
    iterative: str,
    router,
    context: str = "",
) -> ReflectionScore:
    """评估三段式复盘的质量

    Args:
        factual: 事实复盘（发生了什么）
        cognitive: 思维复盘（当初为什么这么想）
        iterative: 迭代复盘（下次怎么改进）
        router: LLM路由器
        context: 任务上下文（可选）

    Returns:
        ReflectionScore 评分结果
    """
    from .llm_backends import Scene

    score = ReflectionScore()

    prompt = f"""你是明烛的元元认知校验器。你的职责是评估"反思"本身的质量——反思是否真的找出了问题，还是走过场。

【待评估的三段式复盘】

事实复盘：
{factual}

思维复盘：
{cognitive}

迭代复盘：
{iterative}

{f"任务上下文：{context}" if context else ""}

【评估维度】（每项0-100分）
1. specificity 具体性：反思是否指向具体行为/决策，还是泛泛而谈（如"要注意细节"）
2. root_cause 根因性：是否找到根本原因，还是停留在表面现象
3. actionability 可执行性：教训是否能转化为下次的具体行动改变
4. honesty 诚实性：是否回避问题、自我表扬、找借口
5. closure 闭环性：是否形成"问题→原因→行动"的完整链条

【判定标准】
- overall < 60：verdict="invalid"（走过场，需重做）
- 60-80：verdict="valid"（合格但可改进）
- > 80：verdict="excellent"（有效反思）

【输出格式】严格JSON，不要其他内容：
{{"specificity":75,"root_cause":60,"actionability":80,"honesty":85,"closure":70,"overall":74,"verdict":"valid","critique":"一句话批评","suggestions":["改进建议1","改进建议2"]}}"""

    try:
        resp = router.generate(prompt, scene=Scene.JUDGE, max_tokens=400)
        if not resp.ok:
            score.critique = f"元元认知评估失败: {resp.error}"
            return score

        # 解析JSON
        text = resp.content
        idx = text.find('{')
        end = text.rfind('}')
        if idx < 0 or end < 0:
            score.critique = "元元认知响应格式错误"
            return score

        data = json.loads(text[idx:end + 1])
        score.specificity = float(data.get("specificity", 0))
        score.root_cause = float(data.get("root_cause", 0))
        score.actionability = float(data.get("actionability", 0))
        score.honesty = float(data.get("honesty", 0))
        score.closure = float(data.get("closure", 0))
        score.overall = float(data.get("overall", 0))
        score.verdict = data.get("verdict", "valid")
        score.critique = data.get("critique", "")
        score.suggestions = data.get("suggestions", [])

    except Exception as e:
        score.critique = f"元元认知评估异常: {e}"

    return score


def should_redo_reflection(score: ReflectionScore) -> bool:
    """反思分数过低时，建议重做"""
    return score.overall < 60 and score.verdict == "invalid"


if __name__ == "__main__":
    # 测试用的mock router
    class MockRouter:
        def generate(self, prompt, scene=None, max_tokens=400):
            class R:
                ok = True
                content = '{"specificity":70,"root_cause":55,"actionability":60,"honesty":80,"closure":50,"overall":63,"verdict":"valid","critique":"根因分析不够深入","suggestions":["追问3个为什么找根因","教训要写成可执行规则"]}'
            return R()

    score = evaluate_reflection(
        factual="完成了任务，但开头执行驱动了",
        cognitive="因为指令明确就跳过了预见",
        iterative="下次先回答预见4问",
        router=MockRouter(),
    )
    print(json.dumps(score.to_dict(), ensure_ascii=False, indent=2))
    print(f"\n需要重做: {should_redo_reflection(score)}")
