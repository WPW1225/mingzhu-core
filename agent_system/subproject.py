#!/usr/bin/env python3
"""
明烛插件化子项目机制 v4.6
母框架核心：子项目以插件形式接入，互不污染。

子项目继承 BaseSubProject，实现：
- load_knowledge_base: 加载领域知识
- get_prompt_suffix: 返回领域专属提示词
- custom_tools: 定义领域专属工具
- get_strategy: 指定执行策略(pipeline/react)

母框架通过 SubProjectRegistry 管理插件，按需加载。
"""
import logging
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class BaseSubProject(ABC):
    """子项目抽象基类（母框架提供，子项目实现）"""

    @property
    @abstractmethod
    def name(self) -> str:
        """子项目名称"""

    @property
    @abstractmethod
    def description(self) -> str:
        """子项目描述"""

    @abstractmethod
    def load_knowledge_base(self) -> Dict:
        """加载领域知识库"""

    @abstractmethod
    def get_prompt_suffix(self) -> str:
        """返回领域专属提示词后缀"""

    def custom_tools(self) -> List[Dict]:
        """领域专属工具（可选，默认无）"""
        return []

    def get_strategy(self) -> str:
        """执行策略：pipeline(默认) 或 react"""
        return "pipeline"

    def get_personas(self) -> List[str]:
        """指定该子项目用哪些人格（可选，默认自动路由）"""
        return []


class SubProjectRegistry:
    """子项目注册表（母框架管理插件）"""

    def __init__(self):
        self._projects: Dict[str, BaseSubProject] = {}

    def register(self, project: BaseSubProject):
        """注册子项目"""
        self._projects[project.name] = project
        logger.info(f"子项目已注册: {project.name}")

    def get(self, name: str) -> Optional[BaseSubProject]:
        """获取子项目"""
        return self._projects.get(name)

    def list_projects(self) -> List[Dict]:
        """列出所有子项目"""
        return [
            {"name": p.name, "description": p.description, "strategy": p.get_strategy()}
            for p in self._projects.values()
        ]

    def auto_detect(self, user_input: str) -> Optional[BaseSubProject]:
        """根据用户输入自动检测该用哪个子项目（无匹配返回None，走默认）"""
        for p in self._projects.values():
            keywords = p.description.lower().split()
            if any(kw in user_input.lower() for kw in keywords if len(kw) > 2):
                return p
        return None


# 全局注册表
_registry: Optional[SubProjectRegistry] = None

def get_registry() -> SubProjectRegistry:
    global _registry
    if _registry is None:
        _registry = SubProjectRegistry()
    return _registry


def reset_registry() -> None:
    """重置单例（供测试使用，保证测试隔离）"""
    global _registry
    _registry = None


if __name__ == "__main__":
    # 示例：如何定义一个子项目
    class CodeAuditProject(BaseSubProject):
        @property
        def name(self): return "code_audit"
        @property
        def description(self): return "代码审计 安全漏洞检查"
        def load_knowledge_base(self): return {"owasp_top10": ["SQL注入", "XSS"]}
        def get_prompt_suffix(self): return "\n请按OWASP Top10标准审查。"
        def get_strategy(self): return "react"

    reg = get_registry()
    reg.register(CodeAuditProject())
    print("=== 已注册子项目 ===")
    print(reg.list_projects())
    print("\n=== 自动检测 ===")
    detected = reg.auto_detect("帮我做代码审计")
    print(f"检测到: {detected.name if detected else '无'}")
