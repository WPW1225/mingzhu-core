# 发布流程（RELEASE）

本文件定义明烛项目的版本发布规范，确保每次发布可追溯、可回滚、可验证。

---

## 语义化版本（Semantic Versioning）

版本号格式：`MAJOR.MINOR.PATCH`

| 版本类型 | 触发条件 | 示例 |
|----------|----------|------|
| **MAJOR** | 不兼容的架构变更（如人格体系重构、配置格式破坏性改动） | 2.0.0 → 3.0.0 |
| **MINOR** | 向下兼容的功能新增（如新增人格、新增配置段、新增测试套件） | 2.0.0 → 2.1.0 |
| **PATCH** | 向下兼容的问题修复（如修 bug、优化文案、补充测试用例） | 2.1.0 → 2.1.1 |

---

## 发布前检查清单（Release Checklist）

发布新版本前，必须逐项确认：

### 1. 代码完整性
- [ ] 所有新增/修改的代码已 commit 并 push 到 main 分支
- [ ] 本地工作区干净（`git status` 无未提交变更）
- [ ] 远程仓库与本地同步（`git ls-remote` 确认）

### 2. 测试全通过
- [ ] 运行 `python3 tests/run_all_tests.py`，结果为 `ALL PASS`
- [ ] 测试套件数量符合预期（当前：5 套件）
- [ ] 无 `--ignore` 跳过的测试（跳过即隐瞒）
- [ ] `tests/test_summary.json` 已更新

### 3. 配置一致性
- [ ] `config/soul_config.yaml` 语法正确（`python3 -c "import yaml; yaml.safe_load(open('config/soul_config.yaml'))"`)
- [ ] `config/red_lines.yaml` 语法正确
- [ ] `config/personas/*.yaml` 全部可加载
- [ ] `config/bazi_config.yaml` / `ziwei_config.yaml` 可加载

### 4. 文档同步
- [ ] `CHANGELOG.md` 已记录本次版本变更
- [ ] `PROJECT_LOG.md` 已记录本次元认知教训（如有）
- [ ] `README.md` 中的版本号、测试套件数已更新
- [ ] `CONTRIBUTING.md` 如有流程变更已同步

### 5. 认知循环闭环
- [ ] 本次发布经历了完整的"预见→执行→反思"三阶段
- [ ] 预见阶段的任务分析4问已回答
- [ ] 反思阶段的三段式复盘已完成并写入 PROJECT_LOG.md
- [ ] 执行驱动信号未被触发（或触发后已纠正）

---

## 发布步骤

### 1. 确定版本号
根据变更内容，按语义化版本规则确定新版本号。

### 2. 更新版本号
- `config/soul_config.yaml` → `meta.version`
- `README.md` → 版本徽章/说明
- `agent_system/__init__.py` → 模块 docstring 版本号

### 3. 更新 CHANGELOG.md
在文件顶部（`## [Unreleased]` 或最新版本下方）新增版本条目，包含：
- 重大变更摘要
- 分类变更详情（提示词工程 / 代码架构 / 评估测试 / 文档协作）
- 核心改进动机

### 4. 运行完整测试
```bash
python3 tests/run_all_tests.py
```
确认 `ALL PASS` 后继续。

### 5. 提交并打标签
```bash
git add -A
git commit -m "release: v2.1.0 - 元认知循环可执行化"
git tag -a v2.1.0 -m "v2.1.0: 认知循环结构化 + CognitiveCycle 类 + 认知循环测试"
git push origin main
git push origin v2.1.0
```

### 6. 验证远程同步
```bash
git ls-remote --tags origin | grep v2.1.0
```
确认标签已推送。

### 7. 创建 GitHub Release（可选）
在 GitHub 仓库页面创建 Release，关联刚推送的 tag，粘贴 CHANGELOG.md 中对应版本的内容作为 Release Notes。

---

## 回滚流程

如果发布后发现严重问题：

1. **快速回滚**：`git revert <release-commit>` → push
2. **标签回滚**：删除错误标签 `git tag -d vX.Y.Z && git push origin :refs/tags/vX.Y.Z`
3. **发补丁版本**：按 PATCH 流程发布修复版本
4. **记录教训**：在 `PROJECT_LOG.md` 记录回滚原因和教训

---

## 版本历史

| 版本 | 日期 | 核心变更 |
|------|------|----------|
| 1.0.0 | 2025-01-15 | 初始版本，6人格，散文式 SOUL.md |
| 2.0.0 | 2026-06-26 | 命理体系 + 配置结构化 + 8人格 + 评估测试 + CI/CD |
| 2.1.0 | 2026-06-26 | 元认知循环可执行化（cognitive_cycle 配置 + CognitiveCycle 类 + 测试） |
