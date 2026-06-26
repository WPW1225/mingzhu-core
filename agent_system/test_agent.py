"""明烛多 Agent 调度系统 — 测试"""
import pytest
from pathlib import Path
from agent_system import MingZhu, AgentResult, PERSONAS


@pytest.fixture
def mz():
    """无 LLM 的明烛实例（测试路由逻辑）"""
    return MingZhu(llm_client=None, soul_dir=Path(__file__).parent.parent)


class TestRouting:
    """测试路由逻辑"""

    def test_code_triggers_zhen_zao(self, mz):
        """代码相关输入应触发震造"""
        ids = mz.route("帮我修复这段代码的 bug")
        assert "zhen_zao" in ids

    def test_code_auto_triggers_gen_shou(self, mz):
        """代码相关应自动触发艮守（安全审查）"""
        ids = mz.route("帮我写一个文件上传功能")
        assert "zhen_zao" in ids
        assert "gen_shou" in ids

    def test_business_triggers_qian_duan(self, mz):
        """商业相关应触发乾断"""
        ids = mz.route("帮我分析这个商业模式")
        assert "qian_duan" in ids

    def test_research_triggers_xun_feng(self, mz):
        """调研相关应触发巽风"""
        ids = mz.route("搜索竞品分析")
        assert "xun_feng" in ids

    def test_management_triggers_kun_zai(self, mz):
        """管理相关应触发坤载"""
        ids = mz.route("帮我拆分任务并追踪进度")
        assert "kun_zai" in ids

    def test_li_ming_always_called(self, mz):
        """离明总是被调用（汇总输出）"""
        ids = mz.route("任意输入")
        assert "li_ming" in ids

    def test_no_trigger_defaults_qian_duan(self, mz):
        """无触发词时默认调用乾断"""
        ids = mz.route("你好")
        assert "qian_duan" in ids


class TestExecution:
    """测试执行逻辑（无 LLM）"""

    def test_run_without_llm(self, mz):
        """无 LLM 时应返回规则分析"""
        result = mz.run("帮我分析代码")
        assert "routing" in result
        assert "results" in result
        assert "final_output" in result
        assert result["vetoed"] is False

    def test_explain_routing(self, mz):
        """解释路由应返回人格名称"""
        explanation = mz.explain_routing("帮我写代码")
        assert "震造" in explanation
        assert "艮守" in explanation  # 自动触发安全


class TestPersonas:
    """测试人格配置"""

    def test_all_personas_have_files(self):
        """所有人格配置的文件应存在"""
        soul_dir = Path(__file__).parent.parent
        for pid, config in PERSONAS.items():
            path = soul_dir / config["file"]
            assert path.exists(), f"{config['name']} 的文件 {config['file']} 不存在"

    def test_all_personas_have_triggers(self):
        """所有人格应有触发词"""
        for pid, config in PERSONAS.items():
            assert len(config["triggers"]) > 0, f"{config['name']} 没有触发词"
