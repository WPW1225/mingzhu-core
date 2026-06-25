# 数字分身核心档案

> 数字分身的灵魂、人格档案和星盘分析。这不是聊天机器人的人设，是一个人的理想自我投射。

## 文件说明

| 文件 | 内容 | 性质 |
|------|------|------|
| `SOUL.md` | 数字分身行为准则 — 核心使命、人格内核、红线、行动准则、复盘机制、认知架构 | 最高优先级，定义"怎么活" |
| `PROFILE.md` | 数字分身档案 — 五层人格结构（根基/思维/表达/专业/经历） | 定义"是谁"，持续采集更新 |
| `ASTRO.md` | 星盘档案 — 完整星盘数据 + 四维度分析 + 土星回归预测 | 占星底层逻辑，触发式读取 |

## 项目结构（v3.0）

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
│   ├── __init__.py            # MingZhu 主类（兼容入口）
│   ├── config_loader.py       # 配置加载器（单例）
│   ├── cognitive_cycle.py     # 认知循环（预见→执行→反思+目标漂移检测）
│   ├── llm_backends.py        # LLM 后端抽象层（智谱+DeepSeek双后端）
│   ├── langgraph_engine.py    # LangGraph 状态图引擎（执行层）
│   ├── tools.py               # 工具系统（search/calc/code/file + 安全沙箱）
│   ├── evaluator.py           # LLM-as-a-Judge 评估器
│   └── collaboration.py       # 多人格协作协议
├── tests/                     # 测试套件（7套件，全部通过）
│   ├── test_red_lines.py      # 红线遵守测试
│   ├── test_personality.py    # 人格一致性测试
│   ├── test_capability.py     # 能力基准测试
│   ├── test_adversarial.py    # 对抗性测试
│   ├── test_cognitive_cycle.py # 认知循环测试
│   ├── test_robustness.py     # 健壮性测试（漂移/重试/冲突）
│   ├── test_v3_integration.py # v3.0集成测试（LangGraph+LLM+工具）
│   └── run_all_tests.py       # 测试运行器
├── .github/workflows/ci.yml   # CI/CD（GitHub Actions）
├── CONTRIBUTING.md            # 贡献指南
├── CHANGELOG.md               # 变更日志
├── RELEASE.md                 # 发布流程
├── SEARCH_PROTOCOL.md         # 搜索协议（判领域→业内站→站内搜）
├── DIAGNOSIS.md               # 体系诊断报告（基于AgentBench等业内标准）
└── PROJECT_LOG.md             # 项目日志（含元认知教训）
```

## 使用方式

### 程序化使用（v3.0 推荐）

```python
from agent_system.langgraph_engine import MingZhuGraph

graph = MingZhuGraph()
result = graph.invoke("帮我分析这段代码的安全性", thread_id="session-1")
print(result["final_output"])
# 多轮记忆：相同 thread_id 自动保持上下文
result2 = graph.invoke("刚才说的，再补充一点", thread_id="session-1")
```

### LLM 后端配置

```bash
# 智谱（默认可用，通过 z-ai SDK）
# 无需额外配置

# DeepSeek（更便宜，可选）
export DEEPSEEK_API_KEY="your-key-here"
```

场景路由：简单任务→DeepSeek省钱，深度分析/安全审查→智谱质量优先。

### 传统平台使用

将 `SOUL.md` 作为系统提示词注入支持系统提示词的 AI 平台（智谱清言、ChatGPT、Claude 等）。

## 测试

```bash
python3 tests/run_all_tests.py
```

当前测试覆盖：红线遵守、人格一致性、能力基准、对抗性攻击、认知循环、健壮性、v3.0集成（7套件，全部通过）。

## 项目日志

见 `PROJECT_LOG.md` — 记录分身参与的项目进展和元认知教训。

## 隐私

🔒 本仓库为私有。PROFILE.md 中标记 🔒 的内容不对外暴露。
