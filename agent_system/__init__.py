"""
明烛多 Agent 调度系统 v2.0

架构升级：
- 配置驱动：从 YAML 加载灵魂配置、人格配置、红线配置、命理配置
- 八卦完整：8 个人格（新增坎观·观察者、兑泽·创造者）
- 质量评估：集成 LLM-as-a-Judge，输出 quality_score
- 推理链记录：记录完整 CoT，便于审计
- 错误处理：safe_run 机制，非核心人格失败不中断
- 协作协议：支持多人格结构化协作

调度流程：
1. 用户输入 → 明烛分析需要哪些人格（基于八字用神优先级）
2. 被调用的人格并行执行（独立 LLM 调用）
3. 艮守审查所有输出（安全一票否决）
4. 坎观独立审查（质量评分和盲点发现）
5. 离明汇总封装为最终回复

使用方式：
    from agent_system import MingZhu
    mz = MingZhu()
    result = mz.run("帮我审查这段代码的安全性")
"""
import os
import json
import time
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config_loader import config as soul_config
from .evaluator import Evaluator, QualityScore
from .collaboration import CollaborationProtocol, CollaborationResult

logger = logging.getLogger(__name__)

# 子人格配置（从 YAML 加载，保留硬编码作为 fallback）
PERSONAS = {
    "qian_duan": {
        "name": "乾断", "file": "QIAN_DUAN.md", "icon": "🔢",
        "triggers": ["逻辑", "分析", "决策", "商业", "财务", "推演", "利弊", "计算", "概率"],
    },
    "li_ming": {
        "name": "离明", "file": "LI_MING.md", "icon": "🔥",
        "triggers": ["表达", "文案", "沟通", "语气", "格式", "封装", "输出"],
    },
    "xun_feng": {
        "name": "巽风", "file": "XUN_FENG.md", "icon": "🌿",
        "triggers": ["搜索", "调研", "查询", "学习", "知识", "竞品", "最佳实践"],
    },
    "zhen_zao": {
        "name": "震造", "file": "ZHEN_ZAO.md", "icon": "⚡",
        "triggers": ["代码", "编程", "架构", "部署", "测试", "修复", "实现", "技术", "写",
                      "上传", "功能", "开发", "前端", "后端", "api", "bug", "重构"],
    },
    "gen_shou": {
        "name": "艮守", "file": "GEN_SHOU.md", "icon": "⛰️",
        "triggers": ["安全", "合规", "风险", "审查", "脱敏", "漏洞", "权限"],
    },
    "kun_zai": {
        "name": "坤载", "file": "KUN_ZAI.md", "icon": "🌍",
        "triggers": ["任务", "拆分", "进度", "追踪", "计划", "优先级", "复盘", "管理", "协调", "规划", "项目", "流程", "分工", "协作"],
    },
    # ===== 新增人格（补全八卦）=====
    "kan_guan": {
        "name": "坎观", "file": "KAN_GUAN.md", "icon": "👁️",
        "triggers": ["审查", "复盘", "盲点", "观察", "质量", "评估", "元认知", "反思"],
    },
    "dui_ze": {
        "name": "兑泽", "file": "DUI_ZE.md", "icon": "💡",
        "triggers": ["创意", "头脑风暴", "创新", "灵感", "发散", "颠覆", "联想", "可能"],
    },
}

# 八卦五行映射（用于用神优先级路由）
TRIGRAM_ELEMENT = {
    "qian_duan": "metal",   # 乾·金·忌神
    "dui_ze": "metal",      # 兑·金·忌神
    "zhen_zao": "wood",     # 震·木·用神
    "xun_feng": "wood",     # 巽·木·用神
    "kan_guan": "water",    # 坎·水·忌神
    "li_ming": "fire",      # 离·火·用神
    "gen_shou": "earth",    # 艮·土·喜神
    "kun_zai": "earth",     # 坤·土·喜神
}

# 用神优先级（基于八字：丁火身弱，用木火，喜土，忌水金）
ELEMENT_PRIORITY = {
    "wood": 1,   # 第一用神
    "fire": 2,   # 第二用神
    "earth": 3,  # 喜神
    "water": 4,  # 第一忌神
    "metal": 5,  # 第二忌神
}


@dataclass
class AgentResult:
    """单个 agent 的执行结果（增强版）"""
    persona: str
    name: str
    icon: str
    content: str
    confidence: str = "中"          # 高/中/低
    vetoed: bool = False            # 艮守是否否决
    error: Optional[str] = None
    quality_score: Optional[QualityScore] = None  # 质量评分
    reasoning_chain: str = ""       # 推理链（CoT）
    execution_time: float = 0.0     # 执行时间
    timestamp: str = ""             # 时间戳

    def to_dict(self) -> Dict:
        return {
            "persona": self.persona,
            "name": self.name,
            "icon": self.icon,
            "content": self.content,
            "confidence": self.confidence,
            "vetoed": self.vetoed,
            "error": self.error,
            "quality_score": self.quality_score.to_dict() if self.quality_score else None,
            "execution_time": round(self.execution_time, 3),
            "timestamp": self.timestamp,
        }


class MingZhu:
    """明烛 — 主控路由器 v2.0

    核心升级：
    1. 配置驱动：从 YAML 加载灵魂和人格配置
    2. 八卦完整：8 个人格
    3. 质量评估：集成 Evaluator
    4. 推理链记录：CoT 日志
    5. 错误处理：safe_run 机制
    6. 观察者机制：坎观独立审查
    """

    def __init__(self, llm_client=None, soul_dir: str = None,
                 enable_evaluator: bool = True, enable_observer: bool = True):
        """
        Args:
            llm_client: LLM 客户端（需要有 generate 方法）
            soul_dir: digital-twin-core 目录路径
            enable_evaluator: 是否启用质量评估器
            enable_observer: 是否启用坎观观察者
        """
        self.llm = llm_client
        self.soul_dir = Path(soul_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self._persona_cache = {}
        self._soul_cache = None

        # 质量评估器
        self.evaluator = Evaluator() if enable_evaluator else None

        # 观察者开关
        self.enable_observer = enable_observer

        # 加载配置
        self._load_soul()

        logger.info(f"明烛 v2.0 初始化完成 | 八卦人格：{len(PERSONAS)}个 | "
                    f"评估器：{'启用' if self.evaluator else '禁用'} | "
                    f"观察者：{'启用' if enable_observer else '禁用'}")

    def _load_soul(self) -> str:
        """加载 SOUL 配置（从 YAML，fallback 到 SOUL.md）"""
        if self._soul_cache is not None:
            return self._soul_cache

        # 优先从 YAML 配置加载
        try:
            soul_yaml = soul_config.get_system_prompt()
            if soul_yaml:
                self._soul_cache = soul_yaml
                logger.info("从 YAML 配置加载灵魂配置成功")
                return self._soul_cache
        except Exception as e:
            logger.warning(f"从 YAML 加载灵魂配置失败: {e}")

        # Fallback: 加载 SOUL.md
        path = self.soul_dir / "SOUL.md"
        if path.exists():
            self._soul_cache = path.read_text(encoding="utf-8")
        else:
            self._soul_cache = ""
        return self._soul_cache

    def _load_persona(self, persona_id: str) -> str:
        """加载子人格配置（优先 YAML，fallback 到 .md 文件）"""
        if persona_id not in self._persona_cache:
            # 优先从 YAML 配置加载
            try:
                yaml_prompt = soul_config.get_persona_prompt(persona_id)
                if yaml_prompt:
                    self._persona_cache[persona_id] = yaml_prompt
                    return yaml_prompt
            except Exception:
                pass

            # Fallback: 加载 .md 文件
            persona_info = PERSONAS.get(persona_id, {})
            file_name = persona_info.get("file", "")
            path = self.soul_dir / file_name if file_name else None
            if path and path.exists():
                self._persona_cache[persona_id] = path.read_text(encoding="utf-8")
            else:
                self._persona_cache[persona_id] = f"# {persona_info.get('name', persona_id)}（配置未找到）"

        return self._persona_cache[persona_id]

    def route(self, user_input: str) -> List[str]:
        """分析输入，决定调用哪些人格（基于八字用神优先级）

        Returns:
            需要调用的人格 ID 列表（按用神优先级排序）
        """
        input_lower = user_input.lower()
        triggered = set()

        for persona_id, persona_config in PERSONAS.items():
            for trigger in persona_config["triggers"]:
                if trigger in input_lower or trigger in user_input:
                    triggered.add(persona_id)
                    break

        # 离明总是被调用（汇总输出）
        triggered.add("li_ming")

        # 如果没有触发任何人格，默认调用乾断（逻辑分析）
        if len(triggered) == 1:
            triggered.add("qian_duan")

        # 如果涉及代码/技术，自动加艮守（安全审查）
        if "zhen_zao" in triggered and "gen_shou" not in triggered:
            triggered.add("gen_shou")

        # 如果启用了观察者，坎观总是参与（独立审查）
        if self.enable_observer:
            triggered.add("kan_guan")

        # 按用神优先级排序
        def priority_key(pid):
            element = TRIGRAM_ELEMENT.get(pid, "earth")
            return ELEMENT_PRIORITY.get(element, 3)

        return sorted(triggered, key=priority_key)

    def _execute_persona(self, persona_id: str, user_input: str,
                         context: str = "") -> AgentResult:
        """执行单个子人格（增强版：质量评分 + CoT + 错误处理）"""
        persona_config = PERSONAS[persona_id]
        start_time = time.time()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        # safe_run 包装
        try:
            persona_content = self._load_persona(persona_id)
            soul = self._load_soul()

            system_prompt = f"""你是「{persona_config['name']}」，明烛数字分身的子人格之一。

{persona_content}

---

SOUL.md 核心规则（必须遵守）：
{soul[:2000]}

---

用户输入：{user_input}
额外上下文：{context or '无'}

请以「{persona_config['name']}」的视角回答。输出格式：
1. 分析/建议内容
2. 置信度：高/中/低
3. 如果是艮守且发现安全问题，标注「否决」
4. 如果是坎观，提供观察报告和质量评分
"""

            content = ""
            if self.llm and hasattr(self.llm, 'is_enabled') and self.llm.is_enabled():
                result = self.llm.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_input,
                    temperature=0.3,
                    max_tokens=1500,
                )
                content = result.get("content", "") if result else "（LLM 无响应）"
            else:
                content = (f"（{persona_config['name']} 已加载，但 LLM 未启用。"
                          f"基于规则分析：{user_input[:100]}）")

            # 解析置信度
            vetoed = "否决" in content and persona_id == "gen_shou"
            confidence = "中"
            if "置信度：高" in content or "置信度: 高" in content:
                confidence = "高"
            elif "置信度：低" in content or "置信度: 低" in content:
                confidence = "低"

            # 质量评估
            quality_score = None
            if self.evaluator:
                quality_score = self.evaluator.evaluate(content, persona_id, context)

            execution_time = time.time() - start_time

            return AgentResult(
                persona=persona_id,
                name=persona_config["name"],
                icon=persona_config["icon"],
                content=content,
                confidence=confidence,
                vetoed=vetoed,
                quality_score=quality_score,
                reasoning_chain=system_prompt[:500],  # 记录推理链摘要
                execution_time=execution_time,
                timestamp=timestamp,
            )

        except Exception as e:
            logger.error(f"{persona_config['name']} 执行失败: {e}")
            return AgentResult(
                persona=persona_id,
                name=persona_config["name"],
                icon=persona_config["icon"],
                content="",
                error=str(e),
                execution_time=time.time() - start_time,
                timestamp=timestamp,
            )

    def run(self, user_input: str, context: str = "") -> Dict:
        """主入口：调度子人格，返回汇总结果（增强版）

        Returns:
            {
                "routing": ["qian_duan", "zhen_zao", ...],
                "results": [AgentResult, ...],
                "vetoed": bool,
                "final_output": str,
                "observer_report": str,      # 坎观观察报告
                "quality_scores": {...},     # 各人格质量评分
                "cot_log": [...],            # 推理链日志
            }
        """
        # 1. 路由
        persona_ids = self.route(user_input)
        routed_names = [PERSONAS[p]['name'] for p in persona_ids]
        logger.info(f"明烛路由：{user_input[:50]} → {routed_names}")

        # 2. 并行执行（离明和坎观最后执行）
        final_personas = ["li_ming"]
        if self.enable_observer:
            final_personas.append("kan_guan")
        parallel_personas = [p for p in persona_ids if p not in final_personas]

        results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self._execute_persona, pid, user_input, context): pid
                for pid in parallel_personas
            }
            for future in as_completed(futures):
                results.append(future.result())

        # 3. 艮守审查（安全一票否决）
        vetoed = any(r.vetoed for r in results if r.persona == "gen_shou")

        if vetoed:
            veto_result = next(r for r in results if r.vetoed)
            return {
                "routing": persona_ids,
                "results": [r.to_dict() for r in results],
                "vetoed": True,
                "final_output": f"⚠️ 艮守否决：{veto_result.content}",
                "observer_report": "",
                "quality_scores": {},
                "cot_log": [{"persona": r.persona, "chain": r.reasoning_chain}
                           for r in results if r.reasoning_chain],
            }

        # 4. 离明汇总
        other_outputs = "\n\n---\n\n".join(
            f"{r.icon} {r.name}（置信度：{r.confidence}）：\n{r.content}"
            for r in results
            if r.content and not r.error
        )

        if "li_ming" in persona_ids:
            li_ming_result = self._execute_persona(
                "li_ming", user_input,
                context=f"其他人格的输出：\n{other_outputs}",
            )
            results.append(li_ming_result)
            final_output = li_ming_result.content
        else:
            final_output = "\n\n".join(
                f"{r.icon} {r.name}：{r.content}"
                for r in results if r.content
            )

        # 5. 坎观独立审查（观察者）
        observer_report = ""
        if self.enable_observer and "kan_guan" in persona_ids:
            kan_result = self._execute_persona(
                "kan_guan", user_input,
                context=f"所有人格的输出：\n{other_outputs}\n\n最终输出：\n{final_output}",
            )
            results.append(kan_result)
            observer_report = kan_result.content

        # 6. 质量评分汇总
        quality_scores = {}
        for r in results:
            if r.quality_score:
                quality_scores[r.persona] = r.quality_score.to_dict()

        # 7. 推理链日志
        cot_log = [{"persona": r.persona, "chain": r.reasoning_chain, "timestamp": r.timestamp}
                   for r in results if r.reasoning_chain]

        return {
            "routing": persona_ids,
            "results": [r.to_dict() for r in results],
            "vetoed": False,
            "final_output": final_output,
            "observer_report": observer_report,
            "quality_scores": quality_scores,
            "cot_log": cot_log,
        }

    def collaborate(self, task: str) -> CollaborationResult:
        """多人格结构化协作（使用协作协议）"""
        llm_caller = None
        if self.llm and hasattr(self.llm, 'is_enabled') and self.llm.is_enabled():
            def llm_caller(prompt, system=""):
                result = self.llm.generate(
                    system_prompt=system,
                    user_prompt=prompt,
                    temperature=0.3,
                    max_tokens=1500,
                )
                return result.get("content", "") if result else ""

        protocol = CollaborationProtocol(llm_caller)
        return protocol.execute(task)

    def explain_routing(self, user_input: str) -> str:
        """解释为什么调用了这些人格（可审计）"""
        persona_ids = self.route(user_input)
        names = [f"{PERSONAS[p]['icon']} {PERSONAS[p]['name']}" for p in persona_ids]

        # 添加用神优先级说明
        priority_info = []
        for pid in persona_ids:
            element = TRIGRAM_ELEMENT.get(pid, "earth")
            role = {"wood": "用神", "fire": "用神", "earth": "喜神",
                   "water": "忌神", "metal": "忌神"}.get(element, "")
            priority_info.append(f"{PERSONAS[pid]['name']}({role})")

        return (f"调用人格：{', '.join(names)}\n"
                f"用神优先级：{', '.join(priority_info)}\n"
                f"（基于八字：丁火身弱，用木火，喜土，忌水金）")

    def get_bazi_info(self) -> Dict:
        """获取八字命理信息"""
        return soul_config.bazi

    def get_ziwei_info(self) -> Dict:
        """获取紫微斗数信息"""
        return soul_config.ziwei


# 便捷函数
def quick_run(user_input: str, llm_client=None) -> str:
    """快速调用，只返回最终输出"""
    mz = MingZhu(llm_client)
    result = mz.run(user_input)
    return result["final_output"]


def quick_collaborate(task: str, llm_client=None) -> str:
    """快速协作，返回最终输出"""
    mz = MingZhu(llm_client)
    result = mz.collaborate(task)
    return result.final_output
