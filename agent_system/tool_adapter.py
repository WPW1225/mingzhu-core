#!/usr/bin/env python3
"""
明烛工具调用适配器 v4.4
兼容多种LLM的工具调用方式：Function Calling(新模型) vs 关键词预编排(旧模型)
"""
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict

    def to_openai_format(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }


class ToolAdapter:
    """工具调用适配器：检测LLM能力，选择最佳调用方式"""

    FC_CAPABLE_MODELS = {
        "glm-4-plus", "glm-4", "glm-4-flash",
        "deepseek-chat", "deepseek-v4-flash",
        "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo",
    }

    def __init__(self, router, tools_registry=None):
        self.router = router
        if tools_registry is None:
            from .tools import get_registry
            tools_registry = get_registry()
        self.tools = tools_registry
        self._tool_defs = self._build_tool_defs()

    def _build_tool_defs(self) -> List[ToolDefinition]:
        return [
            ToolDefinition("web_search", "搜索网页获取最新信息",
                {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}),
            ToolDefinition("calculator", "数学计算",
                {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}),
            ToolDefinition("code_execute", "执行Python代码（沙箱）",
                {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}),
            ToolDefinition("file_read", "读取文件内容",
                {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}),
        ]

    def supports_function_calling(self, model: str) -> bool:
        return model in self.FC_CAPABLE_MODELS

    def get_tools_for_llm(self, model: str) -> List[Dict]:
        if self.supports_function_calling(model):
            return [td.to_openai_format() for td in self._tool_defs]
        return []

    def execute_tool_call(self, call: ToolCall) -> Dict:
        result = self.tools.call(call.name, **call.arguments)
        return {
            "tool": call.name, "success": result.success,
            "output": result.output[:500] if result.success else "",
            "error": result.error,
        }

    def parse_fc_response(self, response: Dict) -> List[ToolCall]:
        calls = []
        for tc in response.get("tool_calls", []):
            func = tc.get("function", {})
            try:
                args = json.loads(func.get("arguments", "{}"))
            except Exception:
                args = {}
            calls.append(ToolCall(name=func.get("name", ""), arguments=args))
        return calls


_adapter: Optional[ToolAdapter] = None

def get_tool_adapter(router=None) -> ToolAdapter:
    global _adapter
    if _adapter is None or router is not None:
        if router is None:
            from .llm_backends import get_router
            router = get_router()
        _adapter = ToolAdapter(router)
    return _adapter


if __name__ == "__main__":
    adapter = get_tool_adapter()
    print("=== 工具定义 ===")
    for td in adapter._tool_defs:
        print(f"  {td.name}: {td.description}")
    print("\n=== FC能力检测 ===")
    for model in ["glm-4-plus", "deepseek-chat", "unknown-model"]:
        print(f"  {model}: {adapter.supports_function_calling(model)}")
