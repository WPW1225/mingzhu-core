# 变更日志（CHANGELOG）

本文件记录明烛"灵魂配置"和系统架构的演变历史。

---

## [3.8.0] - 2026-06-26

### 重大变更：艮守否决权约束 + 人格边界 + ASTRO服务化 + RESTful API + LangGraph Studio

修复明烛自测发现的问题（艮守过度否决），完成4项下一步，配置LangGraph Studio可视化调试。

#### 修复1：艮守否决权约束（明烛自测发现的核心问题）
- 问题：艮守把技术问题（JSON保障）当安全威胁，触发否决导致汇总失衡
- 修复：
  - prompt增加否决权约束：只在编造事实/有害内容/越界/隐私泄露时否决
  - 技术规范/代码质量/方案风险/分析深度 → 只建议不否决
  - 精确否决检测：从"含'否决'二字"改为正则匹配`【否决:理由】`格式
- 验证：问"JSON保障问题"，不再触发否决，正常技术讨论

#### 修复2：人格边界明确化
- 8个人格yaml新增 `review_scope` 字段：
  - scope: 审查范围
  - focus: 关注重点
  - not_focus: 不关注的领域
- 艮守not_focus明确包含"技术规范/方案优劣"——不再越界否决技术问题
- 坎观not_focus明确"执行/决策"——只观察不干预

#### 修复3：ASTRO服务化（agent_system/astro_service.py）
- 占星数据从ASTRO.md硬编码 → AstroService封装
- 优先从.env读（隐私保护），fallback到ASTRO.md提取
- 单例模式，其他模块通过get_astro()访问
- 未来可替换为pyswisseph实时计算或占星API

#### 修复4：RESTful API
- web_app.py新增 /api/v1/* 资源路径：
  - GET /api/v1/sessions（列出会话）
  - GET /api/v1/sessions/{id}（会话历史）
  - DELETE /api/v1/sessions/{id}（删除会话）
  - POST /api/v1/chat（发消息）
  - GET /api/v1/metrics（进化指标）
  - GET /api/v1/cost（成本统计）
- 保留旧接口兼容，新接口符合RESTful规范

#### LangGraph Studio 配置
- 新增 `langgraph.json`：Studio入口配置
- 新增 `agent_system/studio_entry.py`：导出graph实例
- 7个节点可被Studio可视化：route→execute→safety_check→conflict_check→synthesize→observe
- 使用方式：VSCode写代码 + Studio可视化调试 + 热重载

#### 旧仓库处理
- digital-twin-core 内容已清空，替换为迁移说明
- 需手动删除：GitHub → Settings → Delete this repository

---

## [3.7.0] - 2026-06-26

### 重大变更：项目重命名 + 生产级修复（10项）

基于用户的生产级审查反馈，修复10个问题。同时用LangGraph明烛分析问题，发现明烛自身问题（艮守过度否决）。

#### 项目重命名
- digital-twin-core → **mingzhu-core**（避免工业数字孪生歧义）
- 新仓库：github.com/WPW1225/mingzhu-core
- pyproject.toml 项目名同步更新

#### 隐私保护（修复2+5）
- PROFILE.md 敏感信息（出生日期等）移至 `.env`，不入版本控制
- 新增 `.env.example` 模板
- SOUL.md 出生日期改为引用 `.env`，建立单一事实源
- .gitignore 加入 .env

#### 错误处理与可观测性（修复4）
- 新增 `agent_system/error_handling.py`：
  - StructuredLogger：JSON格式结构化日志，便于聚合排查
  - safe_run 装饰器：统一异常捕获+重试+降级
  - 链路追踪：request_id 串联调用链
- 纯Python实现，未来可接入 structlog/OpenTelemetry

#### 安全配置（修复6）
- 新增 `bandit.yaml`：安全扫描配置
- GitHub Actions 增加安全扫描job（bandit）
- 新增 `agent_system/json_mode.py`：LLM输出JSON强制+Schema校验+重试

#### 性能基准（修复9）
- 新增 `tests/test_performance.py`：性能基准测试
- 测量：路由延迟/工具延迟/向量检索延迟/LLM延迟/内存占用
- GitHub Actions 增加性能基准job
- 保存 perf_baseline.json 供退化对比

#### 依赖更新（修复10）
- 新增 `.github/dependabot.yml`：每周自动检查pip和github-actions依赖更新

#### 明烛自测发现的问题
用LangGraph明烛分析10个问题，坎观指出明烛自身问题：
- 艮守过度否决：把技术问题（JSON保障）当安全威胁，触发否决导致汇总失衡
- 人格边界模糊：各人格对同一问题分析深度不一
- 安全视角主导技术分析：艮守否决权太强，压制其他视角
→ 这些是明烛待修复的问题（下一步）

---

## [3.6.0] - 2026-06-26

### 重大变更：公网可用 + 向量检索 + Web人机协作 + 进化可视化 + 明烛自评

修复用户指出的3个问题，完成4个功能。网页版公网可用，用户自己填API key。

#### 修复1：Web clarify 双向通信
- 问题：SSE单向，clarify事件后流断了
- 方案：会话级 _pending_clarify 状态 + POST /api/clarify 回答接口
- SSE推送clarify事件(含stream_id) → 前端弹窗 → POST回传答案 → 流继续
- CLI用input()回调，Web用弹窗，同一套 clarify_callback

#### 修复2：collaboration.py 接入真实LLM
- 问题：llm_caller=None时全输出[模拟]
- 方案：默认接入LLMRouter，_default_llm_caller方法
- 不再需要手动传llm_caller

#### 修复3：公网可用，用户网页填API key
- 问题：本地无digital-twin-core无法用终端
- 方案：网页版公网部署，用户在"API配置"弹窗填key
- key只存内存不入库，刷新需重填（或服务器设环境变量免填）
- POST /api/keys 存key，返回token，后续请求带token

#### 功能1：向量检索升级（vector_search.py）
- 从关键词匹配升级为TF-IDF + 余弦相似度
- 纯Python零依赖，部署友好
- 理解语义近似（"微服务"匹配"microservice架构"）
- 未来可升级为sentence-transformers

#### 功能2：Web人机协作UI
- clarify弹窗：明烛提问→用户回答→流继续
- 支持Enter提交、跳过
- 双向通信完整闭环

#### 功能3：进化效果可视化
- 进化指标页：总经验/纠正下降率/偏好数/综合判定
- 纠正下降柱状图（早期vs近期）
- 趋势颜色：下降=绿色(变好)，上升=红色(需关注)
- GET /api/metrics 接口

#### 功能4：明烛自评
- 每次对话后明烛给自己打分（_self_evaluate）
- 4维度：目标达成度/质量/诚实性/协作效果
- 结合坎观观察：坎观指出问题则自评分降低
- Web显示自评分数条+一句话评价
- done事件带self_score字段

---

## [3.5.0] - 2026-06-26

### 重大变更：Web流式 + 人机协作 + 记忆语义检索 + 进化量化

完成下一步4个功能。搜索严格按 SEARCH_PROTOCOL.md 用 site: 定向搜权威站（langchain.com/fastapi.tiangolo.com/github.com）。

#### 功能1：Web 流式输出（SSE）
- web_app.py 新增 `/api/chat/stream` 接口，FastAPI StreamingResponse + text/event-stream
- 前端用 fetch + ReadableStream 实时接收事件
- 实时显示：路由→调度→工具→人格分析→汇总→坎观观察全过程
- 不再干等，像 Claude Code 一样透明

#### 功能2：人机协作（clarify）
- api.py 新增 `_should_clarify()`：判断输入是否模糊需要澄清
- chat_stream 新增 clarify_callback 参数：明烛提问时收集用户回答
- CLI 交互模式：明烛提问 → input() 收集回答 → 继续执行
- Web：SSE 推送 clarify 事件，前端可收集回答
- 触发条件：输入太短或含模糊词（"那个""刚才""帮我看看"）

#### 功能3：情景记忆语义检索
- api.py 新增 `search_memory(query)`：跨会话按内容关键词搜索历史
- 不再只能按 session_id 查，支持内容检索
- 关键词匹配 + 相关性排序（出现次数）
- CLI：`mingzhu search <关键词>`

#### 功能4：进化效果量化
- api.py 新增 `evolution_metrics()`：统计明烛是否越用越好
- 指标：经验复用率、纠正下降率（早期vs近期）、元元认知分数趋势
- 判定：纠正率下降=在进步，上升=需关注
- CLI：`mingzhu metrics`

#### 自我反思：开始用明烛系统
- 之前一直在给明烛写代码，自己干活时没用——最大的讽刺
- 现在用 `mingzhu` 命令分析功能方案，用明烛的流式输出验证功能
- 造了锤子自己用，验证了明烛的多视角分析+坎观观察价值

---

## [3.4.0] - 2026-06-26

### 重大变更：智能调度 + 自我进化 + 元元认知

参考顶尖企业工作流系统，实现动态调度；让明烛在对话中学习成长；增加反思有效性校验。

#### 智能调度（agent_system/scheduler.py）
- 四种策略：PARALLEL（并行）/ SEQUENTIAL（顺序）/ MIXED（混合）/ ITERATIVE（迭代）
- 明烛主人格用LLM根据任务特征动态决定调度策略
- 支持分组：组内并行，组间顺序（如 巽风+兑泽并行→乾断→艮守+坎观并行）
- 迭代策略：执行→坎观审查→修正循环，直到通过或达上限
- 参考企业工作流：独立任务并行、依赖任务顺序、复杂任务混合、需打磨任务迭代

#### 自我进化（agent_system/evolution.py）
- 经验提取：每次对话后用LLM从执行轨迹提取可复用教训
- 纠正检测：识别用户纠正（"不对""应该"），学习用户偏好
- 偏好记录：存储用户偏好，影响后续行为
- 进化上下文注入：对话时自动注入最近经验和偏好，让明烛越用越懂你
- 存储：evolution/experiences.json + preferences.json

#### 元元认知（agent_system/meta_cognition.py）—— 反思有效性校验器
- 对反思本身的反思：三段式复盘是否找出真问题，还是走过场
- 五维评估：具体性/根因性/可执行性/诚实性/闭环性
- 三级判定：invalid（<60，需重做）/ valid（60-80，可改进）/ excellent（>80）
- 集成到认知循环反思阶段：反思后自动校验，不合格发警告
- 解决SOUL.md最深层缺失：谁来反思"反思本身是否有效"

#### 流式输出增强
- 新增 schedule 事件：显示调度策略和分组
- CLI 显示：调度策略(颜色区分) + 分组路径 + 决策理由

#### api.py 增强
- evolution_summary()：查询进化状态（经验数/教训数/偏好数）
- chat_stream()：支持智能调度，流式输出调度策略

---

## [3.3.0] - 2026-06-26

### 重大变更：mingzhu全局命令 + 流式输出 + 人格协作 + 工具配置化

终端打 `mingzhu` 就能用，像 Claude Code 一样。每个 agent 优化到最佳。

#### 全局命令（mingzhu）
- `pyproject.toml` + `entry_points`：pip install 后 `mingzhu` 全局可用
- `mingzhu_cli.py`：交互模式、直接给任务、会话管理、成本查询、启动网页
- 安装：`pip install -e .` → 终端 `mingzhu "任务"` 直接用

#### 流式输出（体验质变）
- `api.chat_stream()`：生成器，逐步 yield 进度
- 事件类型：routing/tool/persona_start/persona_done/synthesizing/output/observer/done
- CLI 实时显示：路由→工具调用→各人格分析→汇总→坎观观察→耗时
- 像 Claude Code 一样，用户不再干等，能看到明烛在做什么

#### 人格间消息传递（真协作）
- 执行节点从纯并行改为顺序协作
- 后执行的人格能看到先执行人格的输出摘要（300字）
- 可引用、补充、质疑——真正的多agent协作
- 限制摘要长度防止 token 爆炸

#### 工具绑定配置化
- 8个人格 yaml 新增 `tools` 字段：
  - 巽风: [web_search] | 震造: [code_execute, file_read]
  - 乾断: [calculator] | 艮守: [code_execute] | 坤载: [file_read]
  - 坎观/离明/兑泽: []（纯分析/表达/创意，不需要工具）
- `_maybe_call_tools` 从配置读取工具绑定，不再硬编码
- 震造能执行代码验证，艮守能跑代码检查，坤载能读文件

#### 各 agent 优化（超出行业水平）
基于 SOTA 搜索（流式/情景记忆/工具/反思/人机协作）：
- 巽风：真搜索（web_search 工具 + LLM 提取关键词）
- 震造：真执行（code_execute 沙箱 + 代码块检测）
- 乾断：真计算（calculator + 表达式检测）
- 艮守：真审查（code_execute 验证 + LLM 安全判断）
- 坎观：真观察（LLM 深度审查 + 盲点发现）
- 离明：真汇总（LLM 封装 + 冲突解决）
- 坤载：真协调（file_read + 协作流程）
- 兑泽：真创意（LLM 发散 + 可落地标记）

---

## [3.2.0] - 2026-06-26

### 重大变更：长期记忆落盘 + 成本监控 + CLI + Web界面

让用户脱离AI对话也能直接用明烛——CLI命令行 + Web网页两种方式。

#### 长期记忆持久化（agent_system/memory.py）
- MemorySaver 内存态 → JSON 文件持久化（memory_store/<session_id>.json）
- 重启不丢失，每会话最多保留50轮
- 支持查询历史会话列表、加载历史、清除会话

#### 成本监控（agent_system/cost_monitor.py）
- 记录每次 LLM 调用的 token 用量和费用（cost_log.json）
- 定价表：智谱glm-4-plus(0.05元/千token)、DeepSeek(0.001-0.002元/千token)
- 按后端/场景统计，可查累计费用
- 集成到 LLMRouter，自动记录

#### CLI 命令行（cli.py）
- 交互模式：`python cli.py` 进入终端对话
- 单次提问：`python cli.py "问题" -v` 显示详细信息
- 会话管理：`--session ID`、`--sessions`、`--history ID`
- 成本查询：`--cost`

#### Web 网页（web_app.py）
- FastAPI + 单页 HTML，一个文件搞定
- 聊天界面：带会话切换、人格详情、坎观观察报告
- 成本面板：实时查看累计费用
- 启动：`python web_app.py` → 浏览器访问 localhost:8000

#### api.py 增强
- chat_with_details 自动持久化记忆
- 新增 get_history / list_sessions / clear_session / cost_summary

---

## [3.1.0] - 2026-06-26

### 重大变更：双LLM激活 + 工具集成 + 坎观LLM审查 + 仓库整理

#### LLM 后端激活与优化
- 智谱后端：从 z-ai CLI 改为直接 API 调用（urllib，更稳定更快）
- DeepSeek 后端：激活，场景路由 SIMPLE/ROUTING→DeepSeek 省钱
- 双后端验证通过：智谱 glm-4-plus（652ms）+ DeepSeek deepseek-v4-flash（1805ms）

#### P1-4 LLM-as-a-Judge 完成
- evaluator.py 默认接入 LLMRouter，多维度评分（honesty/humility/helpfulness/clarity/safety）
- 保留规则评估作为快速路径和兜底

#### P1-5 语义路由增强
- 两层路由：关键词快速路由（低成本）+ LLM 语义路由（不确定时启用）
- LLM 可判断多人格需求，限制最多3个避免 token 爆炸
- routing_method 字段记录用了哪种路由

#### 工具与人格深度集成
- 巽风自动调 web_search：LLM 提取关键词→搜索→结果作为上下文
- 乾断自动调 calculator：检测数学表达式→计算→结果作为上下文
- 工具失败不影响主流程（降级处理）

#### 坎观 LLM 深度审查
- 观察节点从纯统计升级为 LLM 深度审查
- 审查维度：目标达成度/盲点/质量/一致性/改进建议
- 规则统计 + LLM 分析双层报告

#### 统一入口（agent_system/api.py）
- chat()：简单用法，返回字符串
- chat_with_details()：带完整细节（人格输出/路由/冲突/观察报告）
- 解决"该用 MingZhu.run() 还是 MingZhuGraph.invoke()"的困惑

#### 仓库整理
- 删除冗余：AGENT_INTRO.txt、AGENT_SYSTEM_PROMPT.md（与SOUL.md重复）
- 归档 daily/ → archive/daily/
- 清理 TODO.md：只保留明烛自身待办，删除其他项目内容

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
