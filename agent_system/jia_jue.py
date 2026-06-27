#!/usr/bin/env python3
"""
甲觉 · 学习官（v4.3）

命名：甲觉为用神之首（生丁火），阳木主生发学习。
职责：被明烛(CEO)调用时才工作，学习外部知识存入知识库。
  1. 搜索：用web_search获取外部知识
  2. 提炼：从搜索结果提取结构化知识
  3. 归档：存入knowledge_base/，供后续检索

与进化系统(evolution.py)的区别：
- 甲觉：向外学习（外部知识）
- evolution：向内归纳（内部经验）

设计原则：明烛判断"需要外部知识吗"才调用甲觉，不需要就休息。
"""
import json
import time
import logging
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

KB_DIR = Path(__file__).parent.parent / "knowledge_base"
KB_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Knowledge:
    id: str
    topic: str          # 主题
    content: str        # 知识内容
    source: str = ""    # 来源URL或说明
    created_at: str = ""
    used_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "topic": self.topic, "content": self.content,
            "source": self.source, "created_at": self.created_at,
            "used_count": self.used_count,
        }


class JiaJue:
    """甲觉·学习官"""

    def __init__(self):
        self.kb_file = KB_DIR / "external.json"
        if not self.kb_file.exists():
            self.kb_file.write_text("[]", encoding="utf-8")

    def learn(self, topic: str, router) -> Dict:
        """被明烛调用：学习某主题的外部知识

        Args:
            topic: 要学习的主题
            router: LLM路由器
        Returns:
            学到的知识摘要
        """
        # 第一步：搜索外部知识
        search_result = self._search_external(topic)
        if not search_result:
            return {"learned": False, "reason": "搜索无结果"}

        # 第二步：用LLM提炼结构化知识
        knowledge = self._extract_knowledge(topic, search_result, router)
        if not knowledge:
            return {"learned": False, "reason": "提炼失败"}

        # 第三步：归档到知识库
        self._archive(knowledge)
        return {"learned": True, "topic": topic, "content": knowledge.content[:200]}

    def _search_external(self, topic: str) -> str:
        """用web_search工具搜索外部知识"""
        try:
            from .tools import get_registry
            reg = get_registry()
            result = reg.call("web_search", query=topic, num=5)
            return result.output if result.success else ""
        except Exception as e:
            logger.debug(f"甲觉搜索失败: {e}")
            return ""

    def _extract_knowledge(self, topic: str, search_text: str, router) -> Optional[Knowledge]:
        """用LLM从搜索结果提炼结构化知识"""
        try:
            from .llm_backends import Scene
            prompt = f"""从以下搜索结果中提炼关于「{topic}」的结构化知识。

搜索结果：
{search_text[:1500]}

提炼要点：
1. 核心概念（1-2句）
2. 关键特性（3-5条）
3. 适用场景
4. 注意事项

直接输出知识内容，不要前言。"""
            resp = router.generate(prompt, scene=Scene.ANALYSIS, max_tokens=500)
            if not resp.ok:
                return None
            return Knowledge(
                id=f"kb_{int(time.time()*1000)}",
                topic=topic,
                content=resp.content,
                source="web_search",
                created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
        except Exception as e:
            logger.debug(f"甲觉提炼失败: {e}")
            return None

    def _archive(self, knowledge: Knowledge):
        """归档到知识库"""
        data = self._load()
        data.append(knowledge.to_dict())
        self._save(data)

    def query(self, topic: str, limit: int = 3) -> str:
        """被明烛调用：查询知识库中某主题的知识"""
        data = self._load()
        relevant = [d for d in data if topic.lower() in d.get("topic", "").lower()
                    or topic.lower() in d.get("content", "").lower()]
        if not relevant:
            return ""
        parts = [f"【甲觉·知识库·{topic}】"]
        for d in relevant[-limit:]:
            parts.append(d.get("content", "")[:300])
        return "\n".join(parts)

    def _load(self) -> List[Dict]:
        try:
            return json.loads(self.kb_file.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save(self, data: List[Dict]):
        self.kb_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def get_status(self) -> Dict:
        data = self._load()
        return {
            "total_knowledge": len(data),
            "topics": list(set(d.get("topic", "") for d in data))[:10],
        }


_officer: Optional[JiaJue] = None

def get_jia_jue() -> JiaJue:
    global _officer
    if _officer is None:
        _officer = JiaJue()
    return _officer
