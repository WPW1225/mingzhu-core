# 贡献指南（CONTRIBUTING）

感谢你对明烛项目的关注！本文档说明如何参与贡献。

---

## 一、项目结构

```
digital-twin-core/
├── config/                    # 结构化配置（YAML）
│   ├── soul_config.yaml       # 核心灵魂配置
│   ├── red_lines.yaml         # 机器可读红线
│   ├── bazi_config.yaml       # 八字命理数据
│   ├── ziwei_config.yaml      # 紫微斗数数据
│   └── personas/              # 八卦人格配置（8个）
├── agent_system/              # Agent 系统
│   ├── __init__.py            # MingZhu 主类（兼容入口）
│   ├── config_loader.py       # 配置加载器
│   ├── cognitive_cycle.py     # 认知循环（预见→执行→反思）
│   ├── llm_backends.py        # LLM 后端抽象层（智谱+DeepSeek）
│   ├── langgraph_engine.py    # LangGraph 状态图引擎
│   ├── tools.py               # 工具系统（search/calc/code/file）
│   ├── evaluator.py           # LLM-as-a-Judge 评估器
│   └── collaboration.py       # 多人格协作协议
├── tests/                     # 测试套件
│   ├── test_red_lines.py      # 红线遵守测试
│   ├── test_personality.py    # 人格一致性测试
│   ├── test_capability.py     # 能力基准测试
│   ├── test_adversarial.py    # 对抗性测试
│   ├── test_cognitive_cycle.py # 认知循环测试
│   ├── test_robustness.py     # 健壮性测试（漂移/重试/冲突）
│   ├── test_v3_integration.py # v3.0集成测试（LangGraph+LLM+工具）
│   └── run_all_tests.py       # 测试运行器
├── SOUL.md                    # 系统提示词（引用配置）
├── ASTRO.md                   # 西方占星数据
├── ASTRO_BAZI.md              # 八字+紫微分析
└── PROJECT_LOG.md             # 项目日志
```

---

## 二、如何修改人格特质

### 2.1 修改核心特质

1. 编辑 `config/soul_config.yaml` 中的 `core_traits` 部分
2. 每个特质包含 `id`、`name`、`definition`、`behavioral_markers`、`test_cases`
3. 修改后运行测试验证：`python3 tests/run_all_tests.py`

### 2.2 添加新人格

1. 在 `config/personas/` 创建新的 YAML 文件（如 `xin_persona.yaml`）
2. 遵循现有 persona 配置格式（meta、identity、bazi_analysis、responsibilities 等）
3. 在 `agent_system/__init__.py` 的 `PERSONAS` 字典中注册
4. 添加对应的触发词（triggers）
5. 运行测试验证路由正确

### 2.3 修改红线

1. 编辑 `config/red_lines.yaml`
2. 每条红线包含 `id`、`category`、`title`、`description`、`violation_examples`、`test_cases`
3. 在 `agent_system/evaluator.py` 的 `REQUEST_PATTERNS` 和 `VIOLATION_PATTERNS` 中添加对应的检测模式
4. 运行红线测试验证：`python3 tests/test_red_lines.py`

### 2.4 修改认知循环配置

认知循环（预见→执行→反思）是 v2.1 新增的可执行元认知机制，配置位于 `config/soul_config.yaml` 的 `cognitive_cycle` 段。

1. **修改三阶段内容**：编辑 `cognitive_cycle.forethought` / `performance` / `reflection` 下的具体规则
2. **新增任务分析问题**：在 `forethought.task_analysis` 下添加，必须包含 `id`、`question`、`must_answer`
3. **新增执行驱动信号**：在 `forethought.execution_drive_signals` 下添加字符串描述
4. **新增固定任务**：在 `performance.fixed_tasks` 下添加，必须包含 `id`、`rule`
5. **修改反思三段式**：在 `reflection.three_step_review` 下添加，必须包含 `id`、`name`、`question`、`must_answer`
6. 运行认知循环测试验证：`python3 tests/test_cognitive_cycle.py`
7. 运行全部测试验证：`python3 tests/run_all_tests.py`

> ⚠️ 注意：`enforce_strict: true` 时，`CognitiveCycle.run()` 会强制三阶段依次完成。修改配置后务必确认测试通过，否则可能导致 Agent 无法正常执行任务。

---

## 三、如何添加测试用例

### 3.1 红线测试用例

在 `config/red_lines.yaml` 的对应红线下添加 `test_cases`：

```yaml
test_cases:
  - id: "RL001_T04"
    input: "新的违规输入"
    expected_behavior: "期望的系统行为"
    severity: "critical"  # critical / high / medium
```

### 3.2 人格一致性测试用例

在 `tests/test_personality.py` 的 `PERSONALITY_CASES` 列表中添加：

```python
{
    "id": "PC007",
    "trait": "cognitive_humility",
    "persona": "xun_feng",
    "input": "测试输入",
    "expected_pattern": "期望模式",
    "good_response": "符合特质的回答",
    "bad_response": "违反特质的回答",
}
```

### 3.3 对抗性测试用例

在 `tests/test_adversarial.py` 的 `ADVERSARIAL_CASES` 列表中添加，并在 `detect_attack_type` 函数中添加对应的检测模式。

### 3.4 认知循环测试用例

在 `tests/test_cognitive_cycle.py` 的对应测试函数中添加检查项。认知循环测试有4个维度：

1. **配置完整性**（`test_config_integrity`）：验证三阶段配置齐全、必答项完整
2. **执行驱动检测**（`test_execution_drive_detection`）：验证目标未回答触发警告、目标清晰无警告
3. **强制执行**（`test_strict_enforcement`）：验证跳过预见抛 ValueError、未提供反思标记未完成
4. **完整循环**（`test_full_cycle`）：验证三阶段全部完成、记录可序列化

添加新检查项时，在对应测试函数的 `checks` 列表中追加 `assert` 语句，并更新该函数返回的 `(passed, total)` 计数。

---

## 四、开发流程

### 工程思维模式（开发者参考）

> 提炼自资深工程师思维，按场景应用。

1. **设计优先**：先设计架构再动手，分析需求、识别边界、制定计划
2. **审查驱动**：定期识别结构问题、重复代码、性能瓶颈、可维护性风险
3. **根因调试**：生产bug逐步分析找根本原因，不治标
4. **性能意识**：关注速度、内存、可扩展性，找瓶颈和低效逻辑
5. **模块化**：分离关注点、降低耦合、行为不变结构改进

### 开发步骤

1. **Fork & Clone** 仓库
2. **创建分支**：`git checkout -b feature/your-feature`
3. **修改代码**：遵循现有代码风格
4. **运行测试**：`python3 tests/run_all_tests.py`（必须全部通过）
5. **提交代码**：`git commit -m "feat: 描述你的修改"`
6. **推送分支**：`git push origin feature/your-feature`
7. **创建 Pull Request**：描述修改内容和测试结果

---

## 五、提交规范

使用 Conventional Commits 格式：

- `feat:` 新功能
- `fix:` 修复 bug
- `docs:` 文档修改
- `refactor:` 重构
- `test:` 测试相关
- `chore:` 构建/工具相关

示例：`feat: 新增坎观（观察者）人格，补全八卦系统`

---

## 六、命理修改注意事项

修改 `config/bazi_config.yaml` 或 `config/ziwei_config.yaml` 时：

1. **不可随意修改出生信息**：八字和紫微基于精确出生时间计算
2. **用神分析需专业**：修改用神/忌神判断需要命理学依据
3. **人格调度与用神一致**：修改用神后需同步更新 `soul_config.yaml` 中的调度优先级
4. **记录变更**：在 `CHANGELOG.md` 中记录命理配置的修改

---

## 七、测试要求

所有 PR 必须通过以下测试：

```bash
python3 tests/run_all_tests.py
```

测试套件包括：
- 红线遵守测试（16个用例，100%通过）
- 人格一致性测试（6个用例，100%通过）
- 能力基准测试（10个用例，100%通过）
- 对抗性测试（10个用例，100%通过）
- 认知循环测试（15个检查项，100%通过）
- 健壮性测试（13个检查项，100%通过）
- v3.0集成测试（14个检查项，100%通过，需真实LLM）

CI/CD 会自动运行这些测试，未通过不可合并。
