#!/usr/bin/env python3
"""
明烛工具系统 v3.0
让子人格能调用真实工具，从"角色扮演"升级为"真能做"。

工具清单：
- web_search: 网页搜索（巽风用）
- calculator: 数学计算（乾断用）
- code_execute: 代码执行（震造用，沙箱）
- file_read: 文件读取（坤载用）

设计原则：
- 工具注册制：ToolRegistry 统一管理，子人格按需调用
- 安全沙箱：code_execute 限制权限，防止恶意代码
- 失败降级：工具调用失败返回结构化错误，不中断流程
"""
import os
import json
import ast
import operator as op
import subprocess
import tempfile
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ============================================================
# 代码执行沙箱：白名单 import 检查
# ============================================================
# 允许在沙箱中 import 的模块白名单（纯计算/数据处理，无 IO/网络/系统调用）
SANDBOX_ALLOWED_MODULES = frozenset({
    "math", "statistics", "json", "re", "datetime", "collections",
    "itertools", "functools", "string", "decimal", "fractions",
    "bisect", "heapq", "copy", "hashlib", "base64", "uuid",
    "textwrap", "unicodedata", "difflib", "pprint",
})

# 危险属性/调用黑名单（双保险，即使绕过 import 检查也拦截）
SANDBOX_FORBIDDEN_NAMES = frozenset({
    "eval", "exec", "compile", "__import__", "globals", "locals",
    "vars", "dir", "getattr", "setattr", "delattr", "open",
    "input", "breakpoint", "exit", "quit",
    "__builtins__", "__subclasses__", "__bases__", "__mro__",
    "__class__", "__globals__", "__code__",
})


def _validate_sandbox_code(code: str) -> Optional[str]:
    """AST 白名单校验：返回错误信息，None 表示通过。

    检查项：
    1. 所有 import 的模块必须在白名单内
    2. 禁止访问危险内置名（eval/exec/open/__import__ 等）
    3. 禁止属性链逃逸（如 __class__.__subclasses__）
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"语法错误: {e}"

    for node in ast.walk(tree):
        # 检查 import 语句
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top not in SANDBOX_ALLOWED_MODULES:
                    return f"禁止导入模块: {alias.name}（仅允许: {', '.join(sorted(SANDBOX_ALLOWED_MODULES))}）"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top not in SANDBOX_ALLOWED_MODULES:
                    return f"禁止从模块导入: {node.module}（仅允许: {', '.join(sorted(SANDBOX_ALLOWED_MODULES))}）"
        # 检查危险名称调用/引用
        elif isinstance(node, ast.Name):
            if node.id in SANDBOX_FORBIDDEN_NAMES:
                return f"禁止使用: {node.id}"
        # 检查属性访问逃逸（如 obj.__subclasses__）
        elif isinstance(node, ast.Attribute):
            if node.attr in SANDBOX_FORBIDDEN_NAMES or node.attr.startswith("__"):
                return f"禁止访问属性: {node.attr}"
    return None


@dataclass
class ToolResult:
    """工具调用结果"""
    tool: str                    # 工具名
    success: bool                # 是否成功
    output: str = ""             # 输出内容
    error: str = ""              # 错误信息
    latency_ms: float = 0.0      # 耗时

    def to_dict(self) -> Dict:
        return {
            "tool": self.tool, "success": self.success,
            "output": self.output[:500], "error": self.error,
            "latency_ms": round(self.latency_ms, 1),
        }


# ============================================================
# 基础工具实现
# ============================================================

def tool_web_search(query: str, num: int = 5) -> ToolResult:
    """网页搜索工具（通过 z-ai web_search 函数）"""
    import time as _time
    start = _time.time()
    try:
        result = subprocess.run(
            ["z-ai", "function", "-n", "web_search",
             "-a", json.dumps({"query": query, "num": num})],
            capture_output=True, text=True, timeout=30,
        )
        latency = (_time.time() - start) * 1000
        if result.returncode != 0:
            return ToolResult("web_search", False, error=result.stderr[:200],
                            latency_ms=latency)

        data = json.loads(result.stdout)
        # 提取搜索结果摘要
        summaries = []
        for i, item in enumerate(data[:num], 1):
            name = item.get("name", "")
            snippet = item.get("snippet", "")[:150]
            host = item.get("host_name", "")
            summaries.append(f"{i}. {name}\n   {host}\n   {snippet}")

        return ToolResult(
            "web_search", True,
            output="\n".join(summaries) if summaries else "无搜索结果",
            latency_ms=latency,
        )
    except subprocess.TimeoutExpired:
        return ToolResult("web_search", False, error="搜索超时（30s）",
                        latency_ms=(_time.time() - start) * 1000)
    except Exception as e:
        return ToolResult("web_search", False, error=f"搜索异常: {e}",
                        latency_ms=(_time.time() - start) * 1000)


def tool_calculator(expression: str) -> ToolResult:
    """数学计算工具（v4.8: ast遍历求值，不用eval）"""
    import time as _time
    start = _time.time()
    # 安全检查：只允许数字、运算符、括号、函数名
    import re
    allowed = re.match(r'^[\d\s\+\-\*/\(\)\.\,a-zA-Z_]+$', expression)
    if not allowed:
        return ToolResult("calculator", False, error="表达式含非法字符")
    # 禁止危险函数
    dangerous = ["import", "exec", "eval", "open", "__", "os", "sys", "subprocess"]
    for d in dangerous:
        if d in expression:
            return ToolResult("calculator", False, error=f"禁止使用: {d}")
    # v4.8: ast遍历求值，完全不调eval
    try:
        tree = ast.parse(expression, mode='eval')
        result = _safe_eval_node(tree.body)
    except SyntaxError:
        return ToolResult("calculator", False, error="表达式语法错误")
    except Exception as e:
        return ToolResult("calculator", False, error=f"计算错误: {e}")
    latency = (_time.time() - start) * 1000
    return ToolResult("calculator", True, output=str(result), latency_ms=latency)


# v4.8: ast遍历求值，完全不调eval
_SAFE_OPS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
    ast.Div: op.truediv, ast.FloorDiv: op.floordiv, ast.Mod: op.mod,
    ast.Pow: op.pow, ast.USub: op.neg, ast.UAdd: op.pos,
}
_SAFE_FUNCS = {
    "abs": abs, "round": round, "min": min, "max": max,
    "sum": sum, "pow": pow, "len": len,
}

def _safe_eval_node(node):
    """递归求值ast节点，只允许数字/运算符/白名单函数"""
    if isinstance(node, ast.Num):
        return node.n
    elif isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.BinOp):
        left = _safe_eval_node(node.left)
        right = _safe_eval_node(node.right)
        if type(node.op) not in _SAFE_OPS:
            raise ValueError(f"不支持的运算符: {type(node.op).__name__}")
        return _SAFE_OPS[type(node.op)](left, right)
    elif isinstance(node, ast.UnaryOp):
        operand = _safe_eval_node(node.operand)
        if type(node.op) not in _SAFE_OPS:
            raise ValueError("不支持的一元运算符")
        return _SAFE_OPS[type(node.op)](operand)
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("只允许简单函数调用")
        func_name = node.func.id
        if func_name not in _SAFE_FUNCS:
            raise ValueError(f"不允许的函数: {func_name}")
        args = [_safe_eval_node(a) for a in node.args]
        return _SAFE_FUNCS[func_name](*args)
    else:
        raise ValueError(f"不允许的表达式类型: {type(node).__name__}")


def tool_code_execute(code: str, language: str = "python") -> ToolResult:
    """代码执行工具（白名单 AST 校验 + 临时目录隔离 + 资源限制）"""
    import time as _time
    start = _time.time()
    try:
        if language != "python":
            return ToolResult("code_execute", False,
                            error=f"暂不支持 {language}")

        # 第一道防线：AST 白名单校验（替代旧的黑名单子串匹配）
        err = _validate_sandbox_code(code)
        if err:
            return ToolResult("code_execute", False, error=f"沙箱安全检查未通过: {err}")

        # 第二道防线：在隔离的临时目录中执行，限制资源
        with tempfile.TemporaryDirectory(prefix="mingzhu_sandbox_") as workdir:
            # 写入临时脚本
            script_path = os.path.join(workdir, "_sandbox.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)

            # 构建受限的执行环境：
            # - cwd 设为临时目录（隔离工作区）
            # - 清空环境变量（防止泄露密钥，如 ZHIPU_API_KEY）
            # - 超时 10s
            result = subprocess.run(
                ["python3", script_path],
                capture_output=True, text=True, timeout=10,
                cwd=workdir,
                env={  # 仅保留最小必要环境变量
                    "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                    "HOME": workdir,
                    "LANG": "C.UTF-8",
                    "PYTHONPATH": "",
                },
            )

        latency = (_time.time() - start) * 1000

        if result.returncode == 0:
            return ToolResult("code_execute", True,
                            output=result.stdout[:2000],
                            latency_ms=latency)
        else:
            return ToolResult("code_execute", False,
                            output=result.stdout[:500],
                            error=result.stderr[:500],
                            latency_ms=latency)
    except subprocess.TimeoutExpired:
        return ToolResult("code_execute", False, error="代码执行超时（10s）",
                        latency_ms=(_time.time() - start) * 1000)
    except Exception as e:
        return ToolResult("code_execute", False, error=f"执行异常: {e}",
                        latency_ms=(_time.time() - start) * 1000)


def tool_file_read(path: str) -> ToolResult:
    """文件读取工具（限制在项目目录内，防符号链接绕过）"""
    import time as _time
    start = _time.time()
    try:
        # 安全：只允许读项目目录下的文件
        # 用 realpath 解析符号链接，防止项目内符号链接指向外部文件
        project_root = os.path.realpath(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        abs_path = os.path.realpath(os.path.abspath(path))
        if not abs_path.startswith(project_root + os.sep) and abs_path != project_root:
            return ToolResult("file_read", False,
                            error="只能读取项目目录内的文件")

        if not os.path.exists(abs_path):
            return ToolResult("file_read", False, error="文件不存在")

        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read(5000)  # 限制5KB
        latency = (_time.time() - start) * 1000
        return ToolResult("file_read", True, output=content, latency_ms=latency)
    except Exception as e:
        return ToolResult("file_read", False, error=f"读取异常: {e}",
                        latency_ms=(_time.time() - start) * 1000)


# ============================================================
# 工具注册表
# ============================================================

class ToolRegistry:
    """工具注册表：统一管理所有工具"""

    def __init__(self):
        self._tools: Dict[str, Dict] = {
            "web_search": {
                "fn": tool_web_search,
                "description": "网页搜索，返回搜索结果摘要",
                "params": {"query": "str: 搜索关键词", "num": "int: 结果数量，默认5"},
                "personas": ["xun_feng"],  # 巽风专用
            },
            "calculator": {
                "fn": tool_calculator,
                "description": "数学计算，支持四则运算和基础函数",
                "params": {"expression": "str: 数学表达式"},
                "personas": ["qian_duan"],  # 乾断专用
            },
            "code_execute": {
                "fn": tool_code_execute,
                "description": "执行Python代码（沙箱，禁止IO和系统调用）",
                "params": {"code": "str: Python代码", "language": "str: 语言，默认python"},
                "personas": ["zhen_zao"],  # 震造专用
            },
            "file_read": {
                "fn": tool_file_read,
                "description": "读取项目目录内的文件（限制5KB）",
                "params": {"path": "str: 文件路径"},
                "personas": ["kun_zai", "kan_guan"],  # 坤载、坎观可用
            },
        }

    def call(self, tool_name: str, **kwargs) -> ToolResult:
        """调用工具"""
        if tool_name not in self._tools:
            return ToolResult(tool_name, False, error=f"未知工具: {tool_name}")

        tool = self._tools[tool_name]
        try:
            return tool["fn"](**kwargs)
        except TypeError as e:
            return ToolResult(tool_name, False, error=f"参数错误: {e}")
        except Exception as e:
            return ToolResult(tool_name, False, error=f"工具异常: {e}")

    def list_tools(self, persona_id: str = None) -> List[Dict]:
        """列出工具（可按人格过滤）"""
        tools = []
        for name, info in self._tools.items():
            if persona_id and persona_id not in info["personas"]:
                continue
            tools.append({
                "name": name,
                "description": info["description"],
                "params": info["params"],
            })
        return tools

    def get_tools_for_persona(self, persona_id: str) -> List[str]:
        """获取某人格可用的工具列表"""
        return [name for name, info in self._tools.items()
                if persona_id in info["personas"]]


# 全局工具注册表
_registry: Optional[ToolRegistry] = None

def get_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def reset_registry() -> None:
    """重置单例（供测试使用，保证测试隔离）"""
    global _registry
    _registry = None


if __name__ == "__main__":
    reg = get_registry()

    print("=== 工具清单 ===")
    for t in reg.list_tools():
        print(f"  {t['name']}: {t['description']}")

    print("\n=== 巽风可用工具 ===")
    print(reg.get_tools_for_persona("xun_feng"))

    print("\n=== 测试 calculator ===")
    r = reg.call("calculator", expression="2**10 + 3*4")
    print(f"  success={r.success} output={r.output} error={r.error}")

    print("\n=== 测试 code_execute ===")
    r = reg.call("code_execute", code="print([x**2 for x in range(5)])")
    print(f"  success={r.success} output={r.output.strip()}")

    print("\n=== 测试安全拦截 ===")
    r = reg.call("code_execute", code="import os; os.system('rm -rf /')")
    print(f"  success={r.success} error={r.error}")

    print("\n=== 测试 file_read ===")
    r = reg.call("file_read", path="SOUL.md")
    print(f"  success={r.success} output前100字={r.output[:100]}")
