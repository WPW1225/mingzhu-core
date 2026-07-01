"""pytest 全局 fixtures

提供：
- reset_singletons：每个测试后重置全局单例，保证测试隔离
- tmp_cost_log：临时成本日志，测试不污染真实 cost_log.json
- isolated_memory：临时记忆目录
"""
import os
import sys
import shutil
import tempfile
from pathlib import Path

import pytest

# 确保项目根在 sys.path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def reset_singletons():
    """每个测试后重置全局单例，保证测试间隔离。

    自动应用到所有测试，无需显式声明。
    调用各模块的 reset_xxx() 函数，确保下次 get_xxx() 重新创建实例。
    """
    yield
    # 测试后清理单例缓存
    resets = [
        ("agent_system.config_loader", "ConfigLoader", "_instance"),
        ("agent_system.cost_monitor", "reset_monitor", None),
        ("agent_system.memory", "reset_memory", None),
        ("agent_system.llm_backends", "reset_router", None),
        ("agent_system.tools", "reset_registry", None),
        ("agent_system.langgraph_engine", None, "_graph"),
    ]
    for mod_name, attr, var in resets:
        try:
            import importlib
            mod = importlib.import_module(mod_name)
            if attr and var is None:
                # 调用 reset_xxx() 函数
                fn = getattr(mod, attr, None)
                if callable(fn):
                    fn()
            elif attr and var:
                # 类属性重置
                cls = getattr(mod, attr, None)
                if cls is not None:
                    setattr(cls, var, None)
            elif var:
                setattr(mod, var, None)
        except Exception:
            pass


@pytest.fixture
def tmp_cost_log(tmp_path):
    """临时成本日志文件，测试不污染真实日志"""
    log_file = tmp_path / "test_cost_log.json"
    return log_file


@pytest.fixture
def isolated_memory(tmp_path):
    """临时记忆目录"""
    mem_dir = tmp_path / "test_memory"
    mem_dir.mkdir()
    return mem_dir
