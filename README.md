# 数字分身核心档案

> 数字分身的灵魂、人格档案和星盘分析。这不是聊天机器人的人设，是一个人的理想自我投射。

## 文件说明

| 文件 | 内容 | 性质 |
|------|------|------|
| `SOUL.md` | 数字分身行为准则 — 核心使命、人格内核、红线、行动准则、复盘机制、认知架构 | 最高优先级，定义"怎么活" |
| `PROFILE.md` | 数字分身档案 — 五层人格结构（根基/思维/表达/专业/经历） | 定义"是谁"，持续采集更新 |
| `ASTRO.md` | 星盘档案 — 完整星盘数据 + 四维度分析 + 土星回归预测 | 占星底层逻辑，触发式读取 |

## 项目结构（v2.1）

```
digital-twin-core/
├── SOUL.md                    # 灵魂准则（人类可读）
├── config/                    # 结构化配置（机器可读）
│   ├── soul_config.yaml       # 灵魂配置：特质/红线/认知循环/人格路由
│   ├── red_lines.yaml         # 红线规则（7条，18个测试用例）
│   ├── personas/              # 8个人格配置（八卦完整）
│   ├── bazi_config.yaml       # 八字四柱配置
│   └── ziwei_config.yaml      # 紫微斗数配置
├── agent_system/              # Agent 系统
│   ├── __init__.py            # MingZhu 主类
│   ├── config_loader.py       # 配置加载器（单例）
│   ├── cognitive_cycle.py     # 认知循环（预见→执行→反思）
│   ├── evaluator.py           # LLM-as-a-Judge 评估器
│   └── collaboration.py       # 多人格协作协议
├── tests/                     # 测试套件（5套件，全部通过）
│   ├── test_red_lines.py      # 红线遵守测试
│   ├── test_personality.py    # 人格一致性测试
│   ├── test_capability.py     # 能力基准测试
│   ├── test_adversarial.py    # 对抗性测试
│   ├── test_cognitive_cycle.py # 认知循环测试
│   └── run_all_tests.py       # 测试运行器
├── .github/workflows/ci.yml   # CI/CD（GitHub Actions）
├── CONTRIBUTING.md            # 贡献指南
├── CHANGELOG.md               # 变更日志
├── RELEASE.md                 # 发布流程
└── PROJECT_LOG.md             # 项目日志（含元认知教训）
```

## 使用方式

这些文件是数字分身的"灵魂配置"。在支持系统提示词的 AI 平台（智谱清言、ChatGPT、Claude 等）中，将 `SOUL.md` 作为系统提示词注入即可。

`PROFILE.md` 和 `ASTRO.md` 是内部参考文件，不需要注入系统提示词，分身按需读取。

程序化使用：

```python
from agent_system import MingZhu

mingzhu = MingZhu()
result = mingzhu.chat("帮我分析这个项目的风险")
print(result.response)
print(f"质量评分: {result.quality_score}")
```

## 测试

```bash
python3 tests/run_all_tests.py
```

当前测试覆盖：红线遵守、人格一致性、能力基准、对抗性攻击、认知循环（5套件，全部通过）。

## 项目日志

见 `PROJECT_LOG.md` — 记录分身参与的项目进展和元认知教训。

## 隐私

🔒 本仓库为私有。PROFILE.md 中标记 🔒 的内容不对外暴露。
