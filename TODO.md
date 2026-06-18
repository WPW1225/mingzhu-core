# AI Investigative Analyst — 完整 TODO

> 最后更新：2026-06-19
> 当前状态：188 tests, 90%+ coverage, 10 Pipeline stages, Docker 部署, CI/CD
> 协作：朋友（基础架构+C3+C4+D1）+ 数字分身（A1测试+A2 LLM增强+B1-B3+C1-C2）

---

## 已完成 ✅

### 工程层

| 阶段 | 内容 | 产出 |
|------|------|------|
| Phase 1-7 | 基础架构 | FastAPI+SQLAlchemy+Pipeline+认证+计费 |
| A1 | 测试套件 | 188 tests, 90% coverage, CI, 修5个bug |
| A2.1-A2.4 | LLM 增强 | 假设/证据/追问/报告全部 LLM 化 |
| B1-B3 | 前端+API | 多轮对话全链路 |
| B2 | Next Data Recommendation | 第10个 Pipeline stage |
| C1 | Docker 部署 | 双容器编排 |
| C2 | 数据安全 | 文件删除+自动清理+大小限制 |
| C3 | 错误处理 | 致命/非致命分级+部分结果返回 |
| C4 | 结构化日志 | JSON审计+操作日志 |
| D1 | 前端组件拆分 | web.py→components/ 5个文件 |

---

## 待做

### 🔴 P0 — 上线前必须完成

#### 工程侧

**1. evidence_collection 降级路径测试**（朋友在做）
- LLM 不可用时的规则路径完全没测过
- 生产环境最大风险点

**2. 端到端冒烟测试（真实 LLM）**
- 当前所有 LLM 测试都是 mock，没跑过真实 API
- 需要配置 `AIA_LLM_API_KEY` 跑一次完整流程
- 验证 LLM 返回的 JSON 解析、假设质量、报告质量

**3. 部署验证**
- Docker compose up 能跑通
- 前端能上传文件、看到报告、追问
- 后端健康检查通过

**4. 安全加固**
- JWT secret 不能用默认值（当前 `change-this-in-production`）
- 上传文件类型校验（不只是后缀，要校验文件头）
- SQL 注入防护确认（SQLAlchemy ORM 已防，但检查动态查询）

### 🟡 P1 — 商业化准备

#### 产品侧

**5. Landing Page**
- 独立首页：产品定位、核心价值、Demo 截图/GIF、CTA
- SaaS 行业平均转化率 3.8%，好的 landing page 能到 4-10%
- 当前 Streamlit 前端直接是登录页，没有产品介绍
- 技术方案：静态 HTML landing page + Streamlit 应用分离

**6. Demo 模式**
- 不注册也能体验：预置数据集 + 预跑结果
- 用户上传前先看到"这个工具能做什么"
- 降低注册门槛 → 提高转化
- 技术方案：预置 demo 数据 + 公开只读 task_id

**7. 定价策略评审**
- 当前：免费3次/月、专业版99/月、团队版399/月
- 对标：Power BI Pro $10/月、Tableau Creator $15/月
- 我们的差异化是"调查分析"不是"可视化"——可以定价更高
- 建议：免费5次（降低试用门槛）、专业版49/月（低于BI工具但功能不同）、团队版199/月
- 需要他确认定价策略

**8. 产品文案**
- 首页文案：一句话说清"这不是又一个BI工具"
- 功能页：调查链路可视化（信号→问题→假设→证据→结论）
- 对比页：vs Tableau/Power BI 的差异
- 技术方案：静态页面 + SEO 优化

#### 增长侧

**9. 分析结果分享**
- 用户能生成分享链接（只读）
- 每次分享 = 一次免费曝光
- 技术方案：公开只读 API + 短链

**10. 用户反馈闭环**
- 分析完成后："这个分析对你有帮助吗？"
- 收集反馈 → 优化 prompt → 提升质量
- 技术方案：feedback API + 存储到 DB

### 🟢 P2 — 体验优化

**11. 前端字段对齐**
- Next Data Recommendation 的 `data_type` vs 前端 `type` 字段名不一致
- generated_by 标记在假设/证据上也展示

**12. Pipeline is_critical 标记完善**
- column_type_inference 应该标记为 critical（后续全依赖它）
- 检查每个 stage 的 critical 属性

**13. 报告导出**
- PDF/Markdown 格式导出
- 方便用户保存和分享分析结果

**14. 大数据集性能**
- 当前 10万行 2.68s，百万行未测
- 流式处理 or 分块加载

**15. API 文档完善**
- FastAPI 自动文档加业务说明
- response model + examples

### 🔵 P3 — 长期方向

**16. Python SDK**
- 封装 API 调用，方便集成到用户工作流

**17. 多数据源接入**
- 数据库直连（MySQL/PostgreSQL）
- API 数据源（Google Analytics / Stripe / etc）
- 当前只支持 CSV/Excel 上传

**18. 定时分析**
- 定时跑分析，监控数据变化
- 新信号自动通知

**19. 团队协作**
- 共享分析结果
- 成员权限管理
- 评论和标注

**20. 行业模板**
- 电商/金融/SaaS 等行业的预置分析模板
- 降低用户使用门槛

---

## 关键路径判断

```
当前 → P0(2,3,4) → P1(5,6,7,8) → 上线
                         ↓
                    P1(9,10) → 增长
                         ↓
                    P2(11-15) → 优化
                         ↓
                    P3(16-20) → 扩展
```

**判断逻辑：**
- P0 是技术门槛——不完成不能上线
- P1 是商业化门槛——不完成上线了也没人用
- P2 是体验门槛——影响留存但不影响首次使用
- P3 是增长引擎——长期价值

**建议起步顺序：**
1. 朋友做 evidence_collection 降级测试（P0-1）
2. 我做真实 LLM 冒烟测试（P0-2）
3. 我做 Docker 部署验证（P0-3）
4. 我做 Landing Page + Demo 模式（P1-5,6）
5. 他确认定价策略后我更新（P1-7）
6. 上线

---

## 数字分身自身 TODO

### 高优先级
- [ ] 认知架构验证——5项升级在实际任务中是否生效
- [ ] 记忆结构化标签落地

### 中优先级
- [ ] PROFILE.md 待采集——机械工程方向、学习方式、幽默感、口头禅、关键经历
- [ ] 伪多系统架构——cron+heartbeat+多渠道落地

### 低优先级
- [ ] IDENTITY.md 完善——头像、名字
- [ ] USER.md 持续更新
