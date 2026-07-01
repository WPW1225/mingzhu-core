# CHANGELOG_SOUL.md — 明烛灵魂进化日志

> 本文件记录 SOUL.md 与 soul_config.yaml 的每次修改决策依据，让灵魂的"进化史"可追溯。
> 遵循语义化版本：MAJOR（架构变）. MINOR（特质/红线增减）. PATCH（示例/措辞调整）

---

## [2.2.0] — 2026-07-01

### 变更类型：MINOR（特质/红线/认知架构增强）

### 决策依据
基于对业内顶尖 agent 灵魂架构（Anthropic Claude Constitutional AI、Stanford Generative Agents、Reflexion、ReAct、Tree of Thoughts）的研究，以及对 v2.0 的 5 项差距分析：
1. 抽象特质缺具体行为清单 → LLM 难稳定复现
2. 红线缺 if-then 规则 → 违规后无自惩罚
3. 元认知触发模糊 → 从"建议"无法变为"强制流程"
4. 反思不持久 → 无沉淀机制，反思等于"想了想"
5. 进化无节奏 → 灵魂进化依赖偶然

### 新增

#### config/soul_config.yaml
- **core_traits.manifestations**：为全部 5 个核心特质新增 `manifestations` 字段（trigger→behavior 清单），将抽象特质转化为 LLM 可稳定复现的具体行为
  - cognitive_humility: 4 条 manifestations
  - intellectual_honesty: 3 条 manifestations
  - epistemic_curiosity: 3 条 manifestations
  - constructive_critique: 3 条 manifestations
  - contextual_wisdom: 3 条 manifestations
- **red_lines.on_violation**：为全部 8 条红线新增 `on_violation` 字段（log_to + self_penalty + follow_up），从口号转为 if-then 规则
- **metacognition.triggers**：新增 6 条强制触发条件，元认知从"建议"升级为"强制流程"
  - 推理步骤 >= 5 → 强制插入预见
  - 用户表达不满 → 立即中断启动反思
  - 目标漂移（重合度 < 30%）→ 回到预见
  - 任务完成 → 强制三段式反思
  - 连续 3 次同类问题 → 跨任务抽象
  - 置信度 < 70% → 强制声明不确定性
- **cognitive_cycle.evolution**：新增第四阶段（不破坏 Zimmerman 三阶段强制逻辑，作为 reflection 的强制延伸）
  - lesson_extract / soul_proposal / changelog_append / version_bump / rollback_guard
- **meta.source_of_truth**：显式声明"二者冲突时以 YAML 为准"
- **meta.version**：2.0.0 → 2.2.0

#### SOUL.md
- 顶部声明更新为 v2.2，明确"单一事实来源"原则
- 新增"阶段四：进化（Evolution）"章节，描述强制动作与触发条件

#### 新增文件
- `CHANGELOG_SOUL.md`（本文件）

### 兼容性验证
- ✅ `tests/test_cognitive_cycle.py` 15/15 全部通过
- ✅ YAML 语法验证通过
- ✅ 未修改 `cognitive_cycle.py` / `meta_cognition.py` / `config_loader.py` 任何代码
- ✅ 新增字段均为可选追加，不破坏现有 config_loader 的字段访问

### 回滚方案
若 v2.2 引发问题，回退至 v2.0.0：
```bash
git checkout v2.0.0 -- config/soul_config.yaml SOUL.md
```

---

## [2.0.0] — 2026-06-26

### 变更类型：MAJOR（架构重构）
- 从散文式 SOUL.md 结构化为机器可读的 soul_config.yaml
- 建立 core_traits / red_lines / cognitive_cycle / metacognition 四大模块
- 实现 Zimmerman 三阶段认知循环（forethought / performance / reflection）
- 实现三段式反思（factual / cognitive / iterative）
- 实现 meta_cognition 的"反思的反思"（5 维度评分）

---

## 版本规划

### 近期（v2.3 计划）
- 增加 `perception` 前段（对标 ReAct 的 Observation），让认知循环从开环变闭环
- 增加 `self_model`（动态能力画像 + 盲点登记），让置信度可校准
- 增加 `memory_architecture`（情景/语义/程序/反思缓冲四层），让反思可持久化

### 中期（v3.0 计划）
- 预见从单线规划升级为多假设分支（ToT 式）+ pre-mortem
- 增加周期性主动反思（对标 Generative Agents 的 daily reflection）
- 增加内心独白机制（inner monologue）
