# AI Investigative Analyst — 完整 TODO

> 最后更新：2026-06-19
> 当前状态：188 tests, 90%+ coverage, 10 Pipeline stages, Docker 部署, CI/CD

---

## 已完成 ✅

| 阶段 | 内容 | 产出 |
|------|------|------|
| Phase 1-7 | 朋友搭建基础架构 | FastAPI+SQLAlchemy+9 stages+认证+计费 |
| A1 | 测试套件 | 188 tests, 90% coverage, CI, 修5个bug |
| A2.1 | 假设生成 LLM 化 | XML prompt+few-shot+降级, 85% |
| A2.2 | 证据收集 LLM 化 | 统计型证据+LLM语义分析+降级, 74% |
| A2.3 | 追问服务 LLM 化 | XML prompt+多轮对话+中英文降级, 96% |
| A2.4 | 报告生成 LLM 化 | XML prompt+few-shot+双语模板, 100% |
| B1 | 前端多轮对话 | conversation_id 生命周期管理 |
| B2 | Next Data Recommendation | 第10个 Pipeline stage, 97% |
| B3 | API conversation_id | ChatRequest 支持 conversation_id |
| C1 | Docker 部署 | Dockerfile+docker-compose+.env.example |
| C2 | 数据安全 | 文件删除API+24h自动清理+大小限制 |
| C3 | 错误处理增强 | 致命/非致命错误分类+部分结果返回 (朋友完成) |
| C4 | 结构化日志 | JSON格式审计日志+操作日志 (朋友完成) |
| D1 | 前端组件拆分 | web.py→components/ 5个文件 (朋友完成) |

---

## 待做（按优先级排序）

### 🔴 高优先级 — 风险点

#### 1. evidence_collection 覆盖率提升（当前 74%，全项目最低）
- **风险**：LLM 降级路径（规则模式）未被测试覆盖，生产环境 LLM 不可用时走降级路径，完全没验证过
- **具体未覆盖**：`_evidence_for_distribution`、`_evidence_for_concentration` 详细逻辑、LLM prompt 构建+解析降级
- **目标**：85%+
- **做法**：补统计型证据的多维度测试 + LLM 降级路径测试

#### 2. cleanup_expired 定时触发
- **风险**：`cleanup_expired` 方法写了但没有触发机制，文件永远不会被清理
- **做法**：FastAPI startup hook 或 cron job 定时调用

### 🟡 中优先级 — 功能完善

#### 3. 前端展示 Next Data Recommendation
- 后端 B2 已完成，前端 components/report.py 有展示但字段未对齐（`type` vs `data_type`）
- 对齐字段名，确保推荐正确展示

#### 4. 前端展示 generated_by 标记
- LLM 生成 vs 模板生成在 UI 上区分（报告已有 caption，但假设/证据没有标记）

#### 5. Pipeline stage is_critical 标记完善
- C3 错误处理框架已就位，但只有 validation 标记了 `is_critical=True`
- 需确认：column_type_inference 是否也应该 critical（后续全依赖它）

#### 6. API 文档完善
- FastAPI 自动生成文档已有，但缺业务说明
- 加 description + response model + examples

### 🟢 低优先级 — 体验优化

#### 7. 大数据集性能优化
- 当前 10 万行 2.68s，百万行未测
- 流式处理 or 分块加载

#### 8. 多语言证据收集降级
- evidence_collection 降级模式仍有中文关键词依赖
- LLM 可用时无此问题，但降级时英文数据证据偏少

#### 9. Python SDK
- 封装 API 调用为 SDK，方便集成

#### 10. 前端导出报告
- 支持导出 PDF/Markdown 格式报告

#### 11. 多租户团队功能
- 团队版支持共享分析结果+成员权限管理

---

## 数字分身自身 TODO

### 高优先级
- [ ] 认知架构验证——5项升级在实际任务中是否生效
- [ ] 记忆结构化标签落地——给现有记忆加标签

### 中优先级
- [ ] PROFILE.md 待采集——机械工程方向、学习方式、幽默感、口头禅、关键经历
- [ ] 伪多系统架构——cron+heartbeat+多渠道落地

### 低优先级
- [ ] IDENTITY.md 完善——头像、名字
- [ ] USER.md 持续更新
