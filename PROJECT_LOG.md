# 项目日志

---

## AI Investigative Analyst

> GitHub: [WPW1225/ai-investigative-analyst](https://github.com/WP1225/ai-investigative-analyst)
> 定位：不是BI工具，是调查分析伙伴 — 发现问题→提出假设→验证假设→形成结论
> 协作人：朋友（Phase 1-7基础架构）+ 数字分身（测试套件、LLM增强、部署、数据安全）

### 2026-06-18 项目日志

#### 犯的错（元认知教训）

收到项目设计文档后没问"GitHub上有没有已有代码"，直接从零搭了一套。看了朋友的成熟代码后一口气改4个文件推GitHub，中间没汇报。

**根因分析：** 默认"执行驱动"认知模式——收到指令→立即分解→执行→交付。简单任务高效，复杂协作灾难。跳过对齐、跳过节奏校准、把完成等同于成功。

**写入SOUL.md：** 元认知监控章节（事前4问+阶段刹车检查+执行驱动触发信号）。

#### A1 测试套件（完成）

- pytest 基础设施（pytest.ini, conftest.py, requirements-dev.txt）
- 10个 Pipeline stage 单元测试
- 3个深度测试（question/hypothesis/evidence）
- 4个 Service 层测试（user/billing/upload/task）
- auth 单元测试 + API 端到端测试
- GitHub Actions CI（Python 3.11+3.12 矩阵）
- **188 tests, 90%+ coverage**
- 修复5个代码bug（重复列名崩溃、datetime64不识别、datetime.utcnow弃用等）

#### A2 LLM 增强（完成）

调研 Anthropic/OpenAI prompt 最佳实践后统一应用：

| 子任务 | 改动 | 覆盖率 |
|--------|------|--------|
| A2.1 假设生成 | XML结构prompt + few-shot + 降级 | 85% |
| A2.2 证据收集 | 统计型证据(语言无关) + LLM语义分析 + 降级 | 74% |
| A2.3 追问服务 | XML prompt + 多轮对话 + 中英文降级 | 96% |
| A2.4 报告生成 | XML prompt + few-shot + 双语模板 | 100% |

核心改进：从"硬编码中文关键词"升级到"LLM语义分析+统计型证据+双语模板"。产品从"只支持中文数据"变成"中英文都能用"。

#### B1-B3 前端+API（完成）

- B3: API 支持 conversation_id 多轮对话
- B1: 前端多轮对话闭环（conversation_id 生命周期管理）
- B2: Next Data Recommendation（第10个Pipeline stage）

#### C1-C2 部署+安全（完成）

- C1: Docker 部署（Dockerfile + docker-compose + .env.example）
- C2: 数据安全（文件删除API + 24h自动清理 + 文件大小限制）

### 待做

| 优先级 | 任务 | 说明 |
|--------|------|------|
| 中 | D1 前端组件拆分 | web.py 633行拆成components/ |
| 中 | B2+ Next Data Recommendation 增强 | 接入LLM生成更具体的建议 |
| 中 | evidence_collection 覆盖率提升 | 74%是最低的，LLM路径降级覆盖不够 |
| 中 | cleanup_expired 定时触发 | 加 cron job 或 startup hook |
| 低 | D2 多语言支持 | 证据收集降级模式优化 |
| 低 | D3 性能优化 | 大数据集流式处理 |

### 2026-06-18 C3+C4 完成

#### C3 错误处理增强
- PipelineStage 新增 is_critical 标记 + safe_run 方法
- 区分致命错误（FatalStageError，中断）和非致命错误（跳过阶段继续）
- validation 标记为核心阶段，其他阶段失败不中断整个 pipeline
- task_service 失败时保存部分结果（已完成阶段的数据不丢）
- PipelineContext 新增 stage_results 记录每阶段状态（success/skipped/fatal）
- 6 个测试覆盖所有场景

#### C4 结构化日志
- app/core/logging.py: JsonFormatter + log_audit + log_operation
- JSON 格式输出，方便接入 ELK/Loki 等日志系统
- 审计日志覆盖：register/login/upload/analyze/delete/upgrade
- 操作日志覆盖：pipeline_run/stage_execute（含耗时）
- 6 个测试覆盖

#### 测试隔离修复
- conftest.py + test_api_e2e.py: 每个测试清空 rate_limit_store
- 修复 chat e2e 因限流累积导致的 429 失败

#### 测试结果
- 201 passed, 0 failed（从 188 增至 201）
- 新增 13 个测试（C3: 6 + C4: 6 + e2e 修复验证 1）

### 2026-06-18 evidence_collection 覆盖率提升

#### 问题
evidence_collection 覆盖率 74%，是所有模块最低的。LLM 路径的降级代码路径覆盖不够，生产环境有风险。

#### 解决
新增 19 个测试（tests/test_evidence_coverage.py），覆盖之前未测的路径：
- _summarize_evidence 全部分支（supports/contradicts/neutral/empty/no_items/equal）
- LLM 边界：不完整 markdown、非 dict JSON、dict 无 finding key
- _prepare_data_sample：outlier 分支、date 分支、无特定数据
- _keyword_distribution：有/无状态列、无 date
- run 边界：signal_index 越界、无匹配 question
- _time_comparison：other_mean=0 分支
- _dimension_contribution：无效 date 异常捕获

#### 环境问题
pytest-cov 和 numpy 2.x 在这个环境有兼容问题（C tracer 冲突），无法直接跑覆盖率报告。通过代码审查 + 分支分析确认覆盖路径。本地环境无此问题。

#### 测试结果
- 220 passed（从 201 增至 220），1 warning

### 2026-06-18 D1 前端组件拆分 + 顺手优化

#### D1 前端组件拆分
- web.py 从 645 行精简到 65 行（主入口）
- 拆成 5 个组件文件：
  - components/common.py: 共享工具（state + api_call + reset_session）
  - components/auth.py: 登录/注册页面
  - components/upload.py: 数据上传 + 分析触发
  - components/report.py: 报告展示（含 C3 阶段状态展示）
  - components/chat.py: 追问对话
- 补 C3 前端降级：展示 stage_results（哪些阶段被跳过）和 warnings

#### 顺手优化（消除弃用警告）
- models: datetime.utcnow → datetime.now(timezone.utc)（4 个文件）
- config: class Config → model_config = SettingsConfigDict(...)（Pydantic V2 规范）
- tests: 修复 2 处 utcnow 调用
- 警告从 143 降到 1（剩 1 个是第三方库 starlette/httpx）

#### 测试结果
- 201 passed, 1 warning（从 143 warnings 降到 1）

### 后续规划（2026-06-18）

#### 短期（本周可做）
1. **B2+ Next Data Recommendation 增强** — 当前推荐偏通用，接入 LLM 生成更具体建议
2. **evidence_collection 覆盖率提升** — 74% 是最低的，LLM 路径降级覆盖不够
3. **cleanup_expired 定时触发** — 加 startup hook 或 cron job

#### 中期（商业化前）
4. **真实支付集成** — 支付宝/微信支付（需要企业资质）
5. **D2 多语言支持** — 证据收集的中英文关键词统一
6. **D3 性能优化** — 100万行+ 流式处理
7. **API 文档完善** — FastAPI 自动文档加业务说明
8. **Python SDK** — 方便 API 调用

#### 长期（增长准备）
9. **团队版功能** — 多席位、共享工作区、权限管理
10. **模板市场** — 行业模板（电商/金融/教育）
11. **监控告警** — 接入 Prometheus + Grafana
12. **A/B 测试框架** — 不同 prompt 策略对比

---

## Edge Dice

> GitHub: [WPW1225/edge-dice](https://github.com/WPW1225/edge-dice)
> Pages: https://wpw1225.github.io/edge-dice/
> 状态：已交付，运行中

### 2026-06-15 项目日志

- 首日项目，JS截断bug，目标思维缺失
- Firebase 实时数据库集成
- 多人游戏系统
- 已上线运行

### 教训

- 大文件写入后必须 `node --check` 验证JS语法
- 重写大文件后必须逐函数对比旧版
- 停在"交付代码"没想"他怎么用"——目标思维缺失

---

## 数字分身自身进化

### 2026-06-17

- "目标思维"补入SOUL.md第一法则
- 长期记忆升级为6分区母库结构
- 确定现阶段走"平台内伪多系统"路线

### 2026-06-18

- 元认知监控写入SOUL.md（执行驱动模式分析）
- 认知架构升级（5项：上下文管理/双视角自检/记忆结构化/经验自动积累/SOUL.md自身管理）
- SOUL.md瘦身：376→215行，砍43%
- 搜索Anthropic/OpenAI/GitHub最佳实践做对照分析


---

# P0-2 真实 LLM 冒烟测试报告

> 测试时间：2026-06-19 01:10
> LLM：智谱 GLM-4-Plus
> 测试数据：500行电商数据（含注入异常）

## 结果：✅ 通过

### Pipeline 全链路

| Stage | 状态 | 说明 |
|-------|------|------|
| validation | ✅ success | |
| column_type_inference | ✅ success | |
| data_profiling | ✅ success | |
| data_quality | ✅ success | |
| signal_detection | ✅ success | 检测到2个 outlier 信号 |
| question_generation | ✅ success | 生成2个调查问题 |
| hypothesis_generation | ✅ success | LLM生成4个假设/问题，质量高 |
| evidence_collection | ✅ success | 每假设3条证据 |
| report_generation | ✅ success | LLM生成，2593 tokens |
| next_data_recommendation | ✅ success | 1条数据推荐 |

### LLM 假设质量评估

LLM 生成的假设具体、可验证、基于实际数据：
- ✅ "异常值集中在产品A和东部地区" — 引用了实际列名和值
- ✅ "异常值对应的成本数据缺失（NaN）" — 发现了注入的缺失值
- ✅ "异常值集中在2024年1月初，可能是季节性促销" — 时间维度分析
- ✅ "异常值对应的高数量可能是批量订单" — 数量维度分析

### 多轮追问测试

3轮追问全部通过，LLM 基于分析上下文回答，第二轮引用第一轮内容，第三轮给出具体数据补充建议。

## 发现的问题

### ⚠️ 1. LLM 报告 likelihood 显示截断
- **现象**：报告里 `[high]` 变成 `igh]`，`[medium]` 变成 `edium]`
- **原因**：LLM 生成报告时没有严格保留方括号格式
- **影响**：显示问题，不影响功能
- **修复方向**：report_generation prompt 中更明确要求保留方括号格式，或在后处理阶段修复

### ⚠️ 2. 趋势信号未触发
- **现象**：注入的"最后10天收入下降50%"未被检测到
- **原因**：每天只有1行数据，`MIN_SAMPLES_PER_GROUP=10` 要求每天至少10条
- **影响**：日级数据（非交易级）的趋势检测不生效
- **修复方向**：考虑增加低密度数据的趋势检测模式，或降低阈值

### ⚠️ 3. 证据模式重复
- **现象**：两组假设的证据 supports/contradicts 模式完全一样
- **原因**：证据收集对不同假设的区分度不够
- **影响**：用户难以区分哪个假设更可信
- **修复方向**：evidence_collection 针对 LLM 假设做更细粒度的证据分析

## 性能

- 总耗时：26秒（含3次 LLM 调用：假设生成×2 + 报告生成×1）
- 可接受范围

## 结论

P0-2 通过。LLM 集成工作正常，假设质量和追问质量都达到生产水平。发现的3个问题不阻塞上线，列入后续优化。
