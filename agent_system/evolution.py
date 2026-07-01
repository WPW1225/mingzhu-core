#!/usr/bin/env python3
"""
明烛自我进化系统 v3.4
让明烛在对话中学习、成长、自我训练。

进化机制（基于 self-evolving agent 研究）：
1. 经验提取：每次对话后，从执行轨迹中提取可复用的经验
2. 规则发现：识别重复出现的模式，提炼成规则
3. 偏好学习：记录用户的纠正和反馈，调整行为
4. 记忆更新：把学到的东西写入长期记忆，影响后续行为

存储：
- agent_system/evolution/experiences.json   经验库
- agent_system/evolution/preferences.json   用户偏好
- agent_system/evolution/rules.json         发现的规则
"""
import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

EVOLUTION_DIR = Path(__file__).parent.parent / "evolution"
EVOLUTION_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Experience:
    """单条经验"""
    timestamp: str
    user_input: str
    output: str
    personas: List[str]
    schedule: str               # 用的调度策略
    observer_report: str        # 坎观评价
    # 进化标签
    outcome: str = "unknown"    # success / failure / corrected
    lesson: str = ""            # 提炼的教训
    reusable: bool = False      # 是否可复用

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Preference:
    """用户偏好（从纠正中学习）"""
    timestamp: str
    trigger: str        # 触发偏好的场景
    preference: str     # 用户偏好
    source: str = "correction"  # correction / explicit / observed

    def to_dict(self) -> Dict:
        return asdict(self)


class EvolutionEngine:
    """自我进化引擎"""

    def __init__(self):
        self.exp_file = EVOLUTION_DIR / "experiences.json"
        self.pref_file = EVOLUTION_DIR / "preferences.json"
        self.rule_file = EVOLUTION_DIR / "rules.json"

    def record_experience(self, exp: Experience):
        """记录一次对话经验"""
        exps = self._load(self.exp_file)
        exps.append(exp.to_dict())
        # 限制最多500条经验
        if len(exps) > 500:
            exps = exps[-500:]
        self._save(self.exp_file, exps)

    def record_preference(self, pref: Preference):
        """记录用户偏好"""
        prefs = self._load(self.pref_file)
        prefs.append(pref.to_dict())
        if len(prefs) > 100:
            prefs = prefs[-100:]
        self._save(self.pref_file, prefs)

    def extract_lesson(self, user_input: str, output: str,
                       observer: str, router) -> str:
        """用LLM从单次对话中提取可复用的教训"""
        from .llm_backends import Scene

        prompt = f"""从以下明烛的对话中提取1条可复用的经验教训（1句话，具体可执行）。

用户问题：{user_input[:200]}
明烛回复：{output[:300]}
坎观评价：{observer[:200]}

只输出教训本身，不要前缀。如果无可提取的教训，输出"无"。"""

        try:
            resp = router.generate(prompt, scene=Scene.JUDGE, max_tokens=100)
            if resp.ok and resp.content.strip() and resp.content.strip() != "无":
                return resp.content.strip()
        except Exception:
            pass
        return ""

    def detect_correction(self, user_input: str, router) -> Optional[str]:
        """检测用户输入是否是对明烛的纠正/反馈，如果是则提取偏好"""
        from .llm_backends import Scene

        prompt = f"""判断以下用户输入是否是对AI助手的纠正或反馈。

用户输入：{user_input}

如果是纠正/反馈，提取用户表达的偏好（1句话）。
如果不是，输出"无"。

只输出偏好本身或"无"。"""

        try:
            resp = router.generate(prompt, scene=Scene.ROUTING, max_tokens=80)
            if resp.ok:
                content = resp.content.strip()
                if content and content != "无":
                    return content
        except Exception:
            pass
        return None

    def get_relevant_experiences(self, user_input: str, limit: int = 3) -> List[Dict]:
        """获取与当前输入相关的历史经验（v4.4: 修复字符遍历bug，改为2-3字滑窗）"""
        exps = self._load(self.exp_file)
        if not exps:
            return []
        # v4.4: 2-3字滑窗分词，替代字符遍历
        keywords = set()
        for n in (2, 3):
            for i in range(len(user_input) - n + 1):
                keywords.add(user_input[i:i+n])
        scored = []
        for e in exps:
            exp_text = e.get("user_input", "") + " " + e.get("lesson", "")
            score = sum(1 for kw in keywords if kw in exp_text)
            if score > 0:
                scored.append((score, e))
        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored[:limit]]

    def get_preferences(self) -> List[Dict]:
        """获取所有用户偏好"""
        return self._load(self.pref_file)

    def get_evolution_context(self, user_input: str) -> str:
        """获取进化上下文（相关经验+偏好），注入到人格执行的system prompt"""
        parts = []
        exps = self.get_relevant_experiences(user_input, 2)
        if exps:
            lessons = [e["lesson"] for e in exps if e.get("lesson")]
            if lessons:
                parts.append("【历史经验】\n" + "\n".join(f"- {l}" for l in lessons))

        prefs = self.get_preferences()
        if prefs:
            recent_prefs = prefs[-3:]
            parts.append("【用户偏好】\n" + "\n".join(f"- {p['preference']}" for p in recent_prefs))

        return "\n\n".join(parts) if parts else ""

    def summary(self) -> Dict:
        """进化状态摘要"""
        exps = self._load(self.exp_file)
        prefs = self._load(self.pref_file)
        lessons = [e for e in exps if e.get("lesson")]
        return {
            "total_experiences": len(exps),
            "lessons_extracted": len(lessons),
            "preferences_learned": len(prefs),
            "recent_lessons": [e["lesson"] for e in lessons[-5:] if e.get("lesson")],
            "recent_preferences": [p["preference"] for p in prefs[-5:]],
        }

    def _load(self, path: Path) -> List[Dict]:
        if not path.exists():
            return []
        try:
            return json.load(open(path, encoding="utf-8"))
        except Exception:
            return []

    def _save(self, path: Path, data: List[Dict]):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# 全局实例
_engine: Optional[EvolutionEngine] = None

def get_engine() -> EvolutionEngine:
    global _engine
    if _engine is None:
        _engine = EvolutionEngine()
    return _engine


def reset_engine() -> None:
    """重置单例（供测试使用，保证测试隔离）"""
    global _engine
    _engine = None


if __name__ == "__main__":
    eng = get_engine()
    print("=== 进化状态 ===")
    print(json.dumps(eng.summary(), ensure_ascii=False, indent=2))
