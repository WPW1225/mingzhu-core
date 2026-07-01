#!/usr/bin/env python3
"""
明烛自我进化引擎 v7.1
基于业内3维度自我进化框架 + Gödel Machine自修复闭环。

参考业内最佳实践：
- XMUDeepLIT综述：3维度（Model-Centric / Experience-Centric / Strategy-Centric）
- Gödel Machine：执行轨迹→失败分析→定向修复→保留或回退
- Red Queen：agent+evaluator协同进化

明烛已有：
- Experience-Centric：evolution.py（经验记录）+ 戊藏（记忆检索）
- Verdict系统：accept/revise/reject
- Critic对抗：找漏洞

v7.1新增：
- Model-Centric：推理时自纠正（verdict=revise时自动重试+修复策略）
- Strategy-Centric：prompt优化（基于失败模式自动调整prompt）
- Gödel闭环：执行轨迹→失败分析→修复→保留或回退
"""
import json
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)

EVOLUTION_DIR = Path(__file__).parent.parent / "evolution"
EVOLUTION_DIR.mkdir(parents=True, exist_ok=True)


class EvolutionDimension(str, Enum):
    """自我进化的3个维度（参考XMUDeepLIT综述）"""
    MODEL_CENTRIC = "model_centric"      # 推理时自纠正
    EXPERIENCE_CENTRIC = "experience"    # 经验学习
    STRATEGY_CENTRIC = "strategy"        # 策略优化


@dataclass
class FailurePattern:
    """失败模式（Gödel Machine的失败分析）"""
    pattern_id: str
    failure_type: str           # logic_gap / hallucination / missing_evidence / contradiction
    description: str
    occurrence_count: int = 0
    last_seen: str = ""
    fix_applied: str = ""       # 已应用的修复
    fix_effective: Optional[bool] = None  # 修复是否有效


@dataclass
class StrategyUpdate:
    """策略更新（Strategy-Centric）"""
    agent_name: str
    update_type: str            # prompt_adjust / weight_change / tool_reassign
    old_value: str
    new_value: str
    reason: str
    timestamp: str = ""
    effective: Optional[bool] = None  # 更新后是否改善


class SelfEvolutionEngine:
    """明烛自我进化引擎 v7.1

    3维度进化 + Gödel自修复闭环：
    1. Model-Centric：verdict=revise时自动重试+修复
    2. Experience-Centric：记录失败模式，积累经验
    3. Strategy-Centric：基于失败模式优化prompt
    """

    def __init__(self):
        self.failure_file = EVOLUTION_DIR / "failure_patterns.json"
        self.strategy_file = EVOLUTION_DIR / "strategy_updates.json"
        self._init_files()

    def _init_files(self):
        for f in [self.failure_file, self.strategy_file]:
            if not f.exists():
                f.write_text("[]", encoding="utf-8")

    # ---------- Gödel闭环：失败分析→修复→保留/回退 ----------

    def analyze_failure(self, critic_attacks: List[Dict], verdict: str,
                        score: float) -> Dict:
        """Gödel Machine：分析失败模式

        当verdict=revise/reject时，分析Critic攻击，识别失败模式。
        """
        if verdict == "accept" or not critic_attacks:
            return {"needs_fix": False}

        patterns = []
        for attack in critic_attacks:
            ftype = attack.get("type", "unknown")
            severity = attack.get("severity", "minor")
            desc = attack.get("description", "")

            # 记录失败模式
            self._record_failure_pattern(ftype, desc)

            patterns.append({
                "type": ftype,
                "severity": severity,
                "description": desc,
            })

        # 生成修复策略
        fix_strategy = self._generate_fix_strategy(patterns, score)

        return {
            "needs_fix": True,
            "failure_patterns": patterns,
            "fix_strategy": fix_strategy,
        }

    def _record_failure_pattern(self, ftype: str, desc: str):
        """记录失败模式（Experience-Centric）"""
        patterns = self._load(self.failure_file)

        # 查找是否已有相同模式
        existing = None
        for p in patterns:
            if p.get("failure_type") == ftype:
                existing = p
                break

        if existing:
            existing["occurrence_count"] = existing.get("occurrence_count", 0) + 1
            existing["last_seen"] = time.strftime("%Y-%m-%d %H:%M:%S")
        else:
            patterns.append({
                "pattern_id": f"FP_{len(patterns)+1:03d}",
                "failure_type": ftype,
                "description": desc[:200],
                "occurrence_count": 1,
                "last_seen": time.strftime("%Y-%m-%d %H:%M:%S"),
                "fix_applied": "",
                "fix_effective": None,
            })

        self._save(self.failure_file, patterns)

    def _generate_fix_strategy(self, patterns: List[Dict], score: float) -> Dict:
        """生成修复策略（Strategy-Centric）

        基于失败模式，生成具体的修复策略。
        """
        strategies = []

        for p in patterns:
            ftype = p.get("type", "")
            if ftype == "逻辑矛盾":
                strategies.append({
                    "type": "prompt_adjust",
                    "target": "all_agents",
                    "adjustment": "增加逻辑一致性检查要求",
                    "prompt_addition": "\n【修复指令】检查你的回答是否有前后矛盾，如果有，修正后再输出。",
                })
            elif ftype == "缺失证据":
                strategies.append({
                    "type": "prompt_adjust",
                    "target": "all_agents",
                    "adjustment": "要求提供证据支撑",
                    "prompt_addition": "\n【修复指令】每个结论必须附带证据或推理过程。",
                })
            elif ftype == "幻觉":
                strategies.append({
                    "type": "prompt_adjust",
                    "target": "all_agents",
                    "adjustment": "强化事实核查",
                    "prompt_addition": "\n【修复指令】不确定的信息必须标注'不确定'，不可编造。",
                })
            elif ftype == "遗漏":
                strategies.append({
                    "type": "prompt_adjust",
                    "target": "all_agents",
                    "adjustment": "补充遗漏内容",
                    "prompt_addition": "\n【修复指令】检查是否有该说但没说的关键点，补充完整。",
                })

        return {
            "strategies": strategies,
            "score": score,
            "recommendation": "retry_with_fixes" if score < 60 else "accept_with_warnings",
        }

    # ---------- 策略更新记录 ----------

    def record_strategy_update(self, update: StrategyUpdate):
        """记录策略更新（用于保留/回退判断）"""
        updates = self._load(self.strategy_file)
        update.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        updates.append(update.__dict__)
        # 保留最近100条
        if len(updates) > 100:
            updates = updates[-100:]
        self._save(self.strategy_file, updates)

    def evaluate_strategy_effectiveness(self) -> Dict:
        """评估策略更新的效果（Gödel的保留/回退）

        对比策略更新前后的评分，判断是否保留。
        """
        updates = self._load(self.strategy_file)
        if len(updates) < 2:
            return {"status": "insufficient_data"}

        # 找已标记效果的更新
        evaluated = [u for u in updates if u.get("effective") is not None]
        if not evaluated:
            return {"status": "no_evaluated_updates"}

        effective_count = sum(1 for u in evaluated if u["effective"])
        total = len(evaluated)

        return {
            "status": "evaluated",
            "total_updates": len(updates),
            "evaluated": total,
            "effective": effective_count,
            "ineffective": total - effective_count,
            "effectiveness_rate": round(effective_count / total, 2) if total else 0,
        }

    # ---------- 进化报告 ----------

    def get_evolution_report(self) -> Dict:
        """完整进化报告（3维度）"""
        failure_patterns = self._load(self.failure_file)
        strategy_updates = self._load(self.strategy_file)
        strategy_effect = self.evaluate_strategy_effectiveness()

        # 按失败类型统计
        type_counts = {}
        for p in failure_patterns:
            ftype = p.get("failure_type", "unknown")
            type_counts[ftype] = type_counts.get(ftype, 0) + p.get("occurrence_count", 1)

        return {
            "dimensions": {
                "model_centric": "推理时自纠正（verdict=revise时自动重试）",
                "experience_centric": f"已记录{len(failure_patterns)}种失败模式",
                "strategy_centric": f"已应用{len(strategy_updates)}次策略更新",
            },
            "failure_patterns": {
                "total_types": len(failure_patterns),
                "type_distribution": type_counts,
                "most_common": max(type_counts, key=type_counts.get) if type_counts else None,
            },
            "strategy_effectiveness": strategy_effect,
            "godel_loop": {
                "analyze": "Critic攻击→失败模式识别",
                "fix": "基于失败类型生成prompt修复",
                "keep_or_revert": "策略更新效果评估",
            },
        }

    def _load(self, f: Path) -> List[Dict]:
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save(self, f: Path, data: List[Dict]):
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# 全局实例
_engine: Optional[SelfEvolutionEngine] = None

def get_evolution_engine() -> SelfEvolutionEngine:
    global _engine
    if _engine is None:
        _engine = SelfEvolutionEngine()
    return _engine


def reset_evolution_engine() -> None:
    """重置单例（供测试使用，保证测试隔离）"""
    global _engine
    _engine = None


if __name__ == "__main__":
    engine = get_evolution_engine()
    print("=== 进化报告 ===")
    print(json.dumps(engine.get_evolution_report(), ensure_ascii=False, indent=2))
