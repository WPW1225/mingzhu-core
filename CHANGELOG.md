# 变更日志（CHANGELOG）

本文件记录明烛"灵魂配置"和系统架构的演变历史。

---

## [3.0.0] - 2026-06-26

### 重大变更：接入 LangGraph 引擎 + 双 LLM 后端 + 工具系统

从"角色扮演"升级为"真能调工具、有记忆、能评估"的真 agent。
基于 LangGraph 状态图引擎重构执行层，灵魂层（SOUL/八卦/命理/认知循环）原封不动。

#### 框架选型（基于搜索）
- 对比 LangGraph / CrewAI / AutoGen / OpenAI Agents SDK / Pydantic AI / LlamaIndex
- **选定 LangGraph**：2026生产就绪度#1，状态图最灵活，原生记忆/恢复，不绑架架构
- 关键依据：CloudRaft 2026评测"团队在CrewAI上花几个月撞限制后重写迁移到LangGraph"
- CrewAI 的 Role-Goal-Backstory 与明烛八卦体系互斥，不采用

#### LLM 后端抽象层（agent_system/llm_backends.py）
- 双后端：智谱 GLM（默认可用）+ DeepSeek（更便宜，待激活）
- 场景路由：SIMPLE/ROUTING→DeepSeek省钱，ANALYSIS/SAFETY/JUDGE/CREATIVE→GLM质量优先
- 统一接口：所有后端实现 generate()，上层无感切换
- 安全：API key 只从环境变量读，绝不硬编码
- 失败降级：DeepSeek不可用时自动降级到智谱
- 调用日志：记录每次调用的场景/后端/模型/延迟/token/错误

#### LangGraph 引擎（agent_system/langgraph_engine.py）
- 状态图模型：route→execute→safety_check→conflict_check→synthesize→observe→END
- 原生多轮记忆：MemorySaver + thread_id，跨调用状态保持
- 原生失败恢复：checkpoint 机制
- 真实 LLM 调用：每个子人格节点真正调用 LLM（非规则模式）
- 艮守一票否决：safety_check 节点检测否决，条件边路由
- 冲突检测：conflict_check 节点扫描对立信号

#### 工具系统（agent_system/tools.py）—— P0-1 完成
- ToolRegistry 注册制：统一管理，子人格按需调用
- 4个基础工具：
  - web_search：网页搜索（巽风用，通过 z-ai SDK）
  - calculator：数学计算（乾断用，安全eval）
  - code_execute：代码执行（震造用，沙箱禁止IO和系统调用）
  - file_read：文件读取（坤载用，限制5KB）
- 安全沙箱：code_execute 拦截 import os / subprocess / open 等
- 失败降级：工具调用失败返回结构化错误，不中断流程

#### 评估与测试
- 新增 `tests/test_v3_integration.py`：14个检查项
  - LLM 后端：4项（智谱可用/双后端状态/场景路由/调用日志）
  - 工具系统：5项（calculator/code_execute/安全拦截/file_read/工具列表）
  - LangGraph 引擎：5项（端到端/否决/多轮记忆/路由/真实LLM调用）
- 集成到 `run_all_tests.py`：测试套件从6个增至7个
- 全部测试通过率：100%（7套件）

### 核心改进

| 诊断问题 | v3.0 解决方案 |
|----------|--------------|
| P0-1 无工具调用 | ToolRegistry + 4基础工具，巽风/震造/乾断/坤载各有所用 |
| P0-2 无多轮记忆 | LangGraph MemorySaver + thread_id |
| P1-6 失败恢复 | LangGraph checkpoint + LLM retry |
| 架构 执行层重构 | LangGraph 状态图，灵魂层保留 |

### 待完成（下一步）
- P1-4 LLM-as-a-Judge：评估器接入真实 LLM（基础设施已就绪）
- P1-5 语义路由：LLM 判断人格路由（基础设施已就绪）
- DeepSeek 激活：用户提供有效 key 后设置环境变量即可

---

## [2.2.0] - 2026-06-26

### 重大变更：基于业内 agent 评测标准的诊断与健壮性优化

用 AgentBench、SWE-bench、WebArena、ToolBench、GAIA 等业内 agent 评测标准，
以及 Confident-AI 总结的 agent 失败模式，对明烛体系进行系统诊断，
并针对诊断出的 P0/P1 问题做代码优化。

#### 诊断报告
- 新增 `DIAGNOSIS.md`：基于业内评测标准的系统诊断
  - 明烛整体7个问题（3个P0：无工具调用/无多轮记忆/无目标漂移检测）
  - 8个子人格各自的问题（巽风无搜索工具、震造无代码执行、艮守正则可绕过等）
  - 优化优先级矩阵

#### 搜索体系
- 新增 `SEARCH_PROTOCOL.md`：搜索协议
  - 三步搜索法：判领域 → 找业内权威站 → 站内搜 → 交叉验证
  - AI/Agent 领域专用站点清单（AgentBench/SWE-bench/WebArena/ToolBench/GAIA/MT-Bench）
  - 搜索质量自检清单 + 反模式

#### 代码优化（P0-3 + P1-5 + P1-6）
- `agent_system/cognitive_cycle.py`：
  - 新增 `detect_goal_drift()`：目标漂移检测（P0-3）
    - 基于目标关键词覆盖率（主指标）+ Jaccard 相似度（辅助）
    - 简易中文分词（2-4字滑窗 + 停用词过滤）
    - 执行阶段自动调用，漂移时写入 warnings
- `agent_system/__init__.py`：
  - `_execute_persona` 增加 retry + fallback（P1-6）
    - LLM 调用失败最多重试 max_retries 次（指数退避）
    - 重试仍失败 → fallback 到规则模式，标记 error，不中断整体流程
  - 新增 `_detect_conflicts()`：人格间冲突检测（P1-5）
    - 扫描对立信号对（建议/否决、安全/有风险、高/低、是/否）
    - 离明汇总前自动检测，冲突时提示优先解决

#### 评估与测试
- 新增 `tests/test_robustness.py`：13个检查项
  - 目标漂移检测：5项（高度相关/完全无关/部分相关/空目标/missing计算）
  - retry+fallback：3项（正常执行/重试后成功/全部失败降级）
  - 冲突检测：5项（无冲突/行动冲突/安全冲突/单人格/error人格）
- 集成到 `run_all_tests.py`：测试套件从5个增至6个
- 全部测试通过率：100%（6套件）

### 核心改进动机

回答"预见→执行→复盘机制是否完美"的疑问：
- 不完美。该机制（Zimmerman SRL）有7个结构性缺陷：只有认知层缺感知-行动闭环、
  单次循环缺跨循环状态、缺失败恢复、严格串行缺中断并行、反思质量无外部校验、
  缺目标漂移检测、缺元元认知
- 本次修复了其中2个（目标漂移检测 P0-3、失败恢复 P1-6），并补充了冲突检测（P1-5）
- 剩余5个（工具调用、多轮记忆、LLM-as-Judge、语义路由、元元认知）需接入真实LLM，列为下一步

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
