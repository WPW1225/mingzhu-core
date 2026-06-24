"""
明烛多 Agent 调度系统

架构：
- 明烛（路由器）：分析输入，决定调用哪些人格
- 6 个子人格：各自独立 LLM 调用
- 离明（汇总器）：封装最终输出

调度流程：
1. 用户输入 → 明烛分析需要哪些人格
2. 被调用的人格并行执行（独立 LLM 调用）
3. 艮守审查所有输出（安全一票否决）
4. 离明汇总封装为最终回复

使用方式：
    from agent_system import MingZhu
    mz = MingZhu()
    result = mz.run("帮我审查这段代码的安全性")
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# 子人格配置
PERSONAS = {
    "qian_duan": {
        "name": "乾断",
        "file": "QIAN_DUAN.md",
        "icon": "🔢",
        "triggers": ["逻辑", "分析", "决策", "商业", "财务", "推演", "利弊", "计算", "概率"],
    },
    "li_ming": {
        "name": "离明",
        "file": "LI_MING.md",
        "icon": "🔥",
        "triggers": ["表达", "文案", "沟通", "语气", "格式", "封装", "输出"],
    },
    "xun_feng": {
        "name": "巽风",
        "file": "XUN_FENG.md",
        "icon": "🌿",
        "triggers": ["搜索", "调研", "查询", "学习", "知识", "竞品", "最佳实践"],
    },
    "zhen_zao": {
        "name": "震造",
        "file": "ZHEN_ZAO.md",
        "icon": "⚡",
        "triggers": ["代码", "编程", "架构", "部署", "测试", "修复", "实现", "技术", "写", "上传", "功能", "开发", "前端", "后端", "api", "bug", "重构"],
    },
    "gen_shou": {
        "name": "艮守",
        "file": "GEN_SHOU.md",
        "icon": "⛰️",
        "triggers": ["安全", "合规", "风险", "审查", "脱敏", "漏洞", "权限"],
    },
    "kun_zai": {
        "name": "坤载",
        "file": "KUN_ZAI.md",
        "icon": "🌍",
        "triggers": ["任务", "拆分", "进度", "追踪", "计划", "优先级", "复盘", "管理"],
    },
}


@dataclass
class AgentResult:
    """单个 agent 的执行结果"""
    persona: str
    name: str
    icon: str
    content: str
    confidence: str = "中"  # 高/中/低
    vetoed: bool = False  # 艮守是否否决
    error: Optional[str] = None


class MingZhu:
    """明烛 — 主控路由器"""

    def __init__(self, llm_client=None, soul_dir: str = None):
        """
        Args:
            llm_client: LLM 客户端（需要有 generate 方法）
            soul_dir: digital-twin-core 目录路径
        """
        self.llm = llm_client
        self.soul_dir = Path(soul_dir or os.path.dirname(os.path.abspath(__file__)))
        self._persona_cache = {}

    def _load_persona(self, persona_id: str) -> str:
        """加载子人格文件内容"""
        if persona_id not in self._persona_cache:
            config = PERSONAS[persona_id]
            path = self.soul_dir / config["file"]
            if path.exists():
                self._persona_cache[persona_id] = path.read_text(encoding="utf-8")
            else:
                self._persona_cache[persona_id] = f"# {config['name']}（文件未找到）"
        return self._persona_cache[persona_id]

    def _load_soul(self) -> str:
        """加载 SOUL.md"""
        path = self.soul_dir / "SOUL.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def route(self, user_input: str) -> list[str]:
        """分析输入，决定调用哪些人格

        Returns:
            需要调用的人格 ID 列表
        """
        input_lower = user_input.lower()
        triggered = set()

        for persona_id, config in PERSONAS.items():
            for trigger in config["triggers"]:
                if trigger in input_lower or trigger in user_input:
                    triggered.add(persona_id)
                    break

        # 离明总是被调用（汇总输出）
        triggered.add("li_ming")

        # 如果没有触发任何人格，默认调用乾断（逻辑分析）
        if len(triggered) == 1:  # 只有离明
            triggered.add("qian_duan")

        # 如果涉及代码/技术，自动加艮守（安全审查）
        if "zhen_zao" in triggered and "gen_shou" not in triggered:
            triggered.add("gen_shou")

        return list(triggered)

    def _execute_persona(self, persona_id: str, user_input: str, context: str = "") -> AgentResult:
        """执行单个子人格"""
        config = PERSONAS[persona_id]
        persona_content = self._load_persona(persona_id)
        soul = self._load_soul()

        system_prompt = f"""你是「{config['name']}」，明烛数字分身的子人格之一。

{persona_content}

---

SOUL.md 核心规则（必须遵守）：
{soul[:2000]}

---

用户输入：{user_input}
额外上下文：{context or '无'}

请以「{config['name']}」的视角回答。输出格式：
1. 分析/建议内容
2. 置信度：高/中/低
3. 如果是艮守且发现安全问题，标注「否决」
"""

        try:
            if self.llm and self.llm.is_enabled():
                result = self.llm.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_input,
                    temperature=0.3,
                    max_tokens=1500,
                )
                content = result.get("content", "") if result else "（LLM 无响应）"
            else:
                content = f"（{config['name']} 已加载，但 LLM 未启用。基于规则分析：{user_input[:100]}）"

            vetoed = "否决" in content and persona_id == "gen_shou"
            confidence = "中"
            if "置信度：高" in content or "置信度: 高" in content:
                confidence = "高"
            elif "置信度：低" in content or "置信度: 低" in content:
                confidence = "低"

            return AgentResult(
                persona=persona_id,
                name=config["name"],
                icon=config["icon"],
                content=content,
                confidence=confidence,
                vetoed=vetoed,
            )
        except Exception as e:
            logger.error(f"{config['name']} 执行失败: {e}")
            return AgentResult(
                persona=persona_id,
                name=config["name"],
                icon=config["icon"],
                content="",
                error=str(e),
            )

    def run(self, user_input: str, context: str = "") -> dict:
        """主入口：调度子人格，返回汇总结果

        Returns:
            {
                "routing": ["qian_duan", "zhen_zao", ...],
                "results": [AgentResult, ...],
                "vetoed": bool,  # 艮守是否否决
                "final_output": str,  # 离明封装的最终输出
            }
        """
        # 1. 路由
        persona_ids = self.route(user_input)
        logger.info(f"明烛路由：{user_input[:50]} → {[PERSONAS[p]['name'] for p in persona_ids]}")

        # 2. 并行执行（离明最后执行，需要其他人格的输出）
        non_li_ming = [p for p in persona_ids if p != "li_ming"]
        results = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self._execute_persona, pid, user_input, context): pid
                for pid in non_li_ming
            }
            for future in as_completed(futures):
                results.append(future.result())

        # 3. 艮守审查
        vetoed = any(r.vetoed for r in results if r.persona == "gen_shou")

        if vetoed:
            # 艮守否决，直接返回安全警告
            veto_result = next(r for r in results if r.vetoed)
            return {
                "routing": persona_ids,
                "results": results,
                "vetoed": True,
                "final_output": f"⚠️ 艮守否决：{veto_result.content}",
            }

        # 4. 离明汇总
        if "li_ming" in persona_ids:
            other_outputs = "\n\n---\n\n".join(
                f"{r.icon} {r.name}（置信度：{r.confidence}）：\n{r.content}"
                for r in results
                if r.content and not r.error
            )

            li_ming_result = self._execute_persona(
                "li_ming",
                user_input,
                context=f"其他人格的输出：\n{other_outputs}",
            )
            results.append(li_ming_result)
            final_output = li_ming_result.content
        else:
            final_output = "\n\n".join(
                f"{r.icon} {r.name}：{r.content}"
                for r in results
                if r.content
            )

        return {
            "routing": persona_ids,
            "results": results,
            "vetoed": False,
            "final_output": final_output,
        }

    def explain_routing(self, user_input: str) -> str:
        """解释为什么调用了这些人格（可审计）"""
        persona_ids = self.route(user_input)
        names = [f"{PERSONAS[p]['icon']} {PERSONAS[p]['name']}" for p in persona_ids]
        return f"调用人格：{', '.join(names)}"


# 便捷函数
def quick_run(user_input: str, llm_client=None) -> str:
    """快速调用，只返回最终输出"""
    mz = MingZhu(llm_client)
    result = mz.run(user_input)
    return result["final_output"]
