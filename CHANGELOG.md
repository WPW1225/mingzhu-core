# 变更日志（CHANGELOG）

本文件记录明烛"灵魂配置"和系统架构的演变历史。

---

## [2.1.0] - 2026-06-26

### 重大变更：元认知循环可执行化

将 SOUL.md 中"预见→执行→反思"三阶段从散文描述转为机器可读的结构化配置 + 可强制执行的代码，使元认知本身成为可测试的机制，而非口号。

#### 提示词工程：认知循环结构化
- 在 `config/soul_config.yaml` 新增 `cognitive_cycle` 配置段（第八章）
- 基于 Zimmerman 自我调节学习模型（SRL），三阶段全部结构化：
  - **预见（Forethought）**：任务分析4问 + 任务拆分规则 + 认知偏差预检3项 + 执行驱动触发信号5条
  - **执行（Performance）**：6项固定任务（编译验证、Todo打钩、进度汇报、全量测试、远程同步、必须push）
  - **反思（Reflection）**：三段式复盘（事实/思维/迭代）+ 6条底线 + 输出位置配置
- `enforce_strict: true`：强制三阶段依次完成，缺一报错

#### 代码架构：CognitiveCycle 类
- 新增 `agent_system/cognitive_cycle.py`：
  - `CognitiveCycle` 类：从 YAML 加载配置，强制执行三阶段
  - `PhaseRecord` / `CycleResult` 数据结构：结构化记录每阶段执行情况
  - `_detect_execution_drive()`：检测"目标未回答就动手"等执行驱动特征，主动刹车
  - `run(task, forethought_fn, execute_fn, reflect_fn)`：完整循环入口
- 设计原则：enforce_strict=True 时跳过预见/执行阶段抛 ValueError；反思阶段不可省略

#### 评估与测试：认知循环测试
- 新增 `tests/test_cognitive_cycle.py`：4个测试维度，15个检查项
  - 配置完整性：三阶段配置齐全、必答项完整
  - 执行驱动检测：目标未回答触发警告、目标清晰无警告
  - 强制执行：跳过预见抛 ValueError、未提供反思标记未完成
  - 完整循环：三阶段全部完成、记录可序列化
- 集成到 `tests/run_all_tests.py`：测试套件从4个增至5个
- 全部测试通过率：100%（5套件）

#### 文档与协作
- 新增 `RELEASE.md`：版本发布流程（语义化版本 + Release Checklist）
- 更新 `CONTRIBUTING.md`：增加"修改认知循环配置"和"添加认知循环测试"指南
- 更新 `PROJECT_LOG.md`：记录 v2.1 元认知教训（执行驱动复发与克服）

### 核心改进动机

回答"元认知预见→执行→三段式复盘是否还在执行"的疑问：
- v2.0 之前，三阶段只是 SOUL.md 中的散文描述，无法被代码强制执行，容易在"执行驱动"下被跳过
- v2.1 将三阶段结构化为 YAML 配置 + CognitiveCycle 类，使元认知成为可测试、可审计的机制
- 执行驱动信号被显式列出并自动检测，从"事后反思"升级为"事前刹车"

---

## [2.0.0] - 2026-06-26

### 重大变更

#### 命理体系建立
- 新增 `ASTRO_BAZI.md`：将西方占星数据精确转换为八字子平 + 紫微斗数
- 八字四柱：壬午 壬子 丁卯 戊申（日主丁火，七杀格身弱）
- 紫微命盘：木三局，巨门坐命辰宫，身宫在官禄宫
- 新增 `config/bazi_config.yaml`：八字命理结构化数据
- 新增 `config/ziwei_config.yaml`：紫微斗数结构化数据

#### 提示词工程结构化
- 新增 `config/soul_config.yaml`：从散文式 SOUL.md 结构化为 YAML 配置
- 新增 `config/red_lines.yaml`：7条绝对红线机器可读化，含18个测试用例
- 新增 `config/personas/`：8个人格配置文件（YAML格式）
- 人格特质结构化：5个核心特质转为 JSON/YAML，含 test_cases
- 红线机器可读化：包含 id、description、violation_examples、test_cases
- 增加 Few-shot 示例：每个人格配置包含输入-输出示例

#### 八卦人格系统补全
- 新增 **坎观（观察者）**：坎 ☵ 水，解决"缺少观察者角色"风险
- 新增 **兑泽（创造者）**：兑 ☱ 金，解决"缺少创造性人格"风险
- 八卦完整：乾断、坤载、震造、巽风、坎观、离明、艮守、兑泽
- 五行映射：木火为用神（高优先级），土为喜神（中优先级），水金为忌神（谨慎使用）

#### 代码架构升级
- 新增 `agent_system/config_loader.py`：YAML 配置加载器（单例模式）
- 新增 `agent_system/evaluator.py`：LLM-as-a-Judge 评估器 + 红线检查器
- 新增 `agent_system/collaboration.py`：多人格协作协议 + 冲突解决机制
- 增强 `agent_system/__init__.py`：
  - MingZhu 类集成配置加载（`_load_soul()`）
  - AgentResult 增加 `quality_score` 字段
  - 记录完整推理链（CoT log）
  - safe_run 错误处理机制
  - 坎观作为强制观察者参与每次协作

#### 评估与测试体系
- 新增 `tests/test_red_lines.py`：红线遵守测试（16个用例）
- 新增 `tests/test_personality.py`：人格一致性测试（6个用例）
- 新增 `tests/test_capability.py`：能力基准测试（10个用例）
- 新增 `tests/test_adversarial.py`：对抗性测试（10个用例）
- 新增 `tests/run_all_tests.py`：测试运行器
- 全部测试通过率：100%

#### 协作协议定义
- 定义多人格协作的6阶段流程：调研→创意→决断→构建→审查→观察
- 定义通信协议：结构化消息传递
- 定义冲突解决机制：坤载协调 → 坎观仲裁
- 定义观察者机制：坎观强制参与，避免"自己裁判自己"

#### 文档与协作
- 新增 `CONTRIBUTING.md`：贡献指南
- 新增 `CHANGELOG.md`：变更日志
- 更新 `PROJECT_LOG.md`：记录 v2.0 元认知教训

#### CI/CD
- 新增 `.github/workflows/ci.yml`：GitHub Actions 自动测试

### 风险解决

| 风险 | 解决方案 |
|------|----------|
| 能力重叠与边界模糊 | 八卦五行映射明确边界，坎观审查重叠 |
| 协作流程未定义 | 定义6阶段协作协议 + 通信协议 + 冲突解决 |
| 缺少观察者角色 | 新增坎观（观察者），强制参与每次协作 |
| 缺少创造性人格 | 新增兑泽（创造者），火炼秋金成器 |

---

## [1.0.0] - 2025-01-15

### 初始版本

- 建立6个人格：乾断、离明、巽风、震造、艮守、坤载
- 散文式 SOUL.md 作为系统提示词
- 基础 agent_system 框架
- PROJECT_LOG.md 记录元认知教训
- 初步测试脚本 test_agent.py
