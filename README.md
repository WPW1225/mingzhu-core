# 明烛 · 数字分身核心档案 (mingzhu-core)

> 数字分身的灵魂、人格档案和星盘分析。这不是聊天机器人的人设，是一个人的理想自我投射。

> 仓库：[github.com/WPW1225/mingzhu-core](https://github.com/WPW1225/mingzhu-core)

> ⚠️ 隐私保护：敏感个人信息已移至 `.env`（不入版本控制），见 `.env.example`。

## 文件说明

| 文件 | 内容 | 性质 |
|------|------|------|
| `SOUL.md` | 数字分身行为准则 — 核心使命、人格内核、红线、行动准则、复盘机制、认知架构 | 最高优先级，定义"怎么活" |
| `PROFILE.md` | 数字分身档案 — 五层人格结构（根基/思维/表达/专业/经历） | 定义"是谁"，持续采集更新 |
| `ASTRO.md` | 星盘档案 — 完整星盘数据 + 四维度分析 + 土星回归预测 | 占星底层逻辑，触发式读取 |

## 项目结构（v3.1）

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
│   ├── api.py                 # 统一入口：chat() / chat_with_details()
│   ├── langgraph_engine.py    # LangGraph 状态图引擎（执行层）
│   ├── llm_backends.py        # LLM 后端抽象层（智谱+DeepSeek双后端）
│   ├── tools.py               # 工具系统（search/calc/code/file + 安全沙箱）
│   ├── cognitive_cycle.py     # 认知循环（预见→执行→反思+目标漂移检测）
│   ├── evaluator.py           # LLM-as-a-Judge 评估器
│   ├── collaboration.py       # 多人格协作协议
│   ├── __init__.py            # MingZhu 主类（兼容入口）
│   └── config_loader.py       # 配置加载器（单例）
├── tests/                     # 测试套件（7套件，全部通过）
│   ├── test_red_lines.py      # 红线遵守测试
│   ├── test_personality.py    # 人格一致性测试
│   ├── test_capability.py     # 能力基准测试
│   ├── test_adversarial.py    # 对抗性测试
│   ├── test_cognitive_cycle.py # 认知循环测试
│   ├── test_robustness.py     # 健壮性测试（漂移/重试/冲突）
│   ├── test_v3_integration.py # v3.0集成测试（LangGraph+LLM+工具）
│   └── run_all_tests.py       # 测试运行器
├── archive/daily/             # 历史日志归档
├── .github/workflows/ci.yml   # CI/CD（GitHub Actions）
├── CONTRIBUTING.md / CHANGELOG.md / RELEASE.md
├── SEARCH_PROTOCOL.md         # 搜索协议
├── DIAGNOSIS.md               # 体系诊断报告
└── PROJECT_LOG.md             # 项目日志（含元认知教训）
```

## 使用方式

### 安装（全局命令）

```bash
cd digital-twin-core
pip install -e .
```
安装后终端直接用 `mingzhu` 命令。

### 方式一：mingzhu 命令（推荐，像 Claude Code）

```bash
export ZHIPU_API_KEY="你的智谱key"
export DEEPSEEK_API_KEY="你的deepseekkey"  # 可选，省钱

mingzhu                              # 交互模式
mingzhu "帮我分析这段代码的安全性"      # 直接给任务（流式输出）
mingzhu "继续刚才的" -s work          # 指定会话
mingzhu sessions                     # 查看所有会话
mingzhu cost                         # 查看成本
mingzhu web                          # 启动网页
```

流式输出：实时显示路由→工具调用→各人格分析→汇总→坎观观察全过程，不再干等。

### 方式二：Web 网页

```bash
mingzhu web
# 或
python web_app.py
```
浏览器访问 `http://localhost:8000`，聊天界面，支持会话切换、人格详情、成本查看。

### 方式三：Python 代码

```python
from agent_system.api import chat, chat_stream, cost_summary

# 简单对话
reply = chat("帮我分析")

# 流式（实时进度）
for event in chat_stream("帮我分析", session_id="s1"):
    if event["type"] == "output":
        print(event["content"])

# 成本统计
print(cost_summary())
```

### LLM 后端配置

```bash
export ZHIPU_API_KEY="your-zhipu-key"      # 智谱（必需）
export DEEPSEEK_API_KEY="your-deepseek-key" # DeepSeek（可选，省钱）
```

场景路由：简单任务/路由判断→DeepSeek省钱，深度分析/安全审查/评估→智谱质量优先。

## 测试

```bash
python3 tests/run_all_tests.py
```

当前测试覆盖：红线遵守、人格一致性、能力基准、对抗性攻击、认知循环、健壮性、v3.0集成（7套件，全部通过）。

## 项目日志

见 `PROJECT_LOG.md` — 记录分身参与的项目进展和元认知教训。

## 隐私

🔒 本仓库为私有。PROFILE.md 中标记 🔒 的内容不对外暴露。
