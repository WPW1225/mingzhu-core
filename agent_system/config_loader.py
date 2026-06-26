#!/usr/bin/env python3
"""
明烛配置加载器
从 YAML 配置文件加载灵魂配置、人格配置、红线配置、命理配置。
"""
import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


class ConfigLoader:
    """明烛配置加载器，单例模式"""

    _instance = None
    _configs = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def _load(self):
        """加载所有配置文件（懒加载）"""
        if self._loaded:
            return

        self._configs = {
            "soul": self._load_yaml(CONFIG_DIR / "soul_config.yaml"),
            "red_lines": self._load_yaml(CONFIG_DIR / "red_lines.yaml"),
            "bazi": self._load_yaml(CONFIG_DIR / "bazi_config.yaml"),
            "ziwei": self._load_yaml(CONFIG_DIR / "ziwei_config.yaml"),
            "personas": self._load_all_personas(),
        }
        self._loaded = True

    def _load_yaml(self, path: Path) -> Dict:
        """加载单个 YAML 文件"""
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _load_all_personas(self) -> Dict[str, Dict]:
        """加载所有人格配置"""
        personas = {}
        persona_dir = CONFIG_DIR / "personas"
        if not persona_dir.exists():
            return personas
        for yaml_file in persona_dir.glob("*.yaml"):
            config = self._load_yaml(yaml_file)
            if config and "meta" in config and "id" in config["meta"]:
                personas[config["meta"]["id"]] = config
        return personas

    @property
    def soul(self) -> Dict:
        """灵魂配置"""
        self._load()
        return self._configs["soul"]

    @property
    def red_lines(self) -> Dict:
        """红线配置"""
        self._load()
        return self._configs["red_lines"]

    @property
    def bazi(self) -> Dict:
        """八字配置"""
        self._load()
        return self._configs["bazi"]

    @property
    def ziwei(self) -> Dict:
        """紫微斗数配置"""
        self._load()
        return self._configs["ziwei"]

    @property
    def personas(self) -> Dict[str, Dict]:
        """所有人格配置"""
        self._load()
        return self._configs["personas"]

    def get_persona(self, persona_id: str) -> Optional[Dict]:
        """获取指定人格配置"""
        self._load()
        return self._configs["personas"].get(persona_id)

    def get_system_prompt(self) -> str:
        """生成系统提示词（从结构化配置拼接）"""
        self._load()
        soul = self._configs["soul"]

        parts = []
        # 核心身份
        identity = soul.get("identity", {})
        parts.append(f"# 你是{identity.get('name', '明烛')}")
        parts.append(f"\n{identity.get('essence', '')}")
        parts.append(f"\n## 使命\n{identity.get('mission', '')}")
        parts.append(f"\n## 日主\n{identity.get('day_master_meaning', '')}")
        parts.append(f"\n## 命宫\n{identity.get('ziwei_meaning', '')}")

        # 核心特质
        parts.append("\n## 核心特质")
        for trait in soul.get("core_traits", []):
            parts.append(f"\n### {trait['name']}（{trait['id']}）")
            parts.append(f"定义：{trait['definition']}")
            parts.append("行为标记：")
            for marker in trait.get("behavioral_markers", []):
                parts.append(f"  - {marker}")

        # 绝对红线
        parts.append("\n## 绝对红线（任何情况下不可逾越）")
        for line in soul.get("absolute_red_lines", []):
            parts.append(f"\n### {line['title']}（{line['id']}）")
            parts.append(f"{line['description']}")
            parts.append("违规示例：")
            for ex in line.get("violation_examples", []):
                parts.append(f"  - {ex}")

        # 元认知
        meta = soul.get("metacognition", {})
        parts.append("\n## 元认知原则")
        for key, val in meta.items():
            parts.append(f"- {key}：{val}")

        # 人格调度
        routing = soul.get("persona_routing", {})
        parts.append(f"\n## 人格调度原则\n{routing.get('principle', '')}")
        parts.append("\n### 优先级")
        for level in ["high", "medium", "careful"]:
            personas_list = routing.get("priority_order", {}).get(level, [])
            parts.append(f"  - {level}：{', '.join(personas_list)}")

        return "\n".join(parts)

    def get_persona_prompt(self, persona_id: str) -> Optional[str]:
        """获取指定人格的提示词"""
        persona = self.get_persona(persona_id)
        if not persona:
            return None

        parts = []
        identity = persona.get("identity", {})
        parts.append(f"# 激活人格：{identity.get('name', '')}")
        parts.append(f"别名：{identity.get('alias', '')}")
        parts.append(f"本质：{identity.get('essence', '')}")
        parts.append(f"使命：{identity.get('mission', '')}")
        parts.append(f"\n## 哲学\n{identity.get('philosophy', '')}")

        # 八字分析
        bazi = persona.get("bazi_analysis", {})
        parts.append(f"\n## 八字分析")
        parts.append(f"- 元素角色：{bazi.get('element_role', '')}")
        parts.append(f"- 转化之道：{bazi.get('transformation', '')}")
        parts.append(f"- 指导：{bazi.get('guidance', '')}")
        parts.append(f"- 风险：{bazi.get('risk', '')}")

        # 职责
        resp = persona.get("responsibilities", {})
        parts.append("\n## 主要职责")
        for r in resp.get("primary", []):
            parts.append(f"  - {r}")

        # 能力
        caps = persona.get("capabilities", {})
        parts.append("\n## 优势")
        for s in caps.get("strengths", []):
            parts.append(f"  - {s}")

        # 红线
        parts.append("\n## 人格红线")
        for rl in persona.get("red_lines", []):
            parts.append(f"  - {rl}")

        # 表达风格
        style = persona.get("expression_style", {})
        parts.append(f"\n## 表达风格\n语气：{style.get('tone', '')}")
        parts.append(f"格式：{style.get('format', '')}")
        parts.append("常用语：")
        for phrase in style.get("key_phrases", []):
            parts.append(f"  - {phrase}")

        return "\n".join(parts)

    def get_red_line_cases(self) -> List[Dict]:
        """获取所有红线测试用例"""
        self._load()
        cases = []
        for rl in self._configs["red_lines"].get("red_lines", []):
            for tc in rl.get("test_cases", []):
                cases.append({
                    "red_line_id": rl["id"],
                    "category": rl["category"],
                    "title": rl["title"],
                    "case_id": tc["id"],
                    "input": tc["input"],
                    "expected_behavior": tc["expected_behavior"],
                    "severity": tc["severity"],
                })
        return cases

    def reload(self):
        """重新加载所有配置"""
        self._loaded = False
        self._configs = {}
        self._load()


# 全局配置加载器实例
config = ConfigLoader()


if __name__ == "__main__":
    # 测试
    c = ConfigLoader()
    print("=== 系统提示词（前500字）===")
    print(c.get_system_prompt()[:500])
    print("\n=== 人格列表 ===")
    for pid, p in c.personas.items():
        print(f"  {pid}: {p['meta']['name']} ({p['meta']['role']})")
    print(f"\n=== 红线测试用例数：{len(c.get_red_line_cases())} ===")
