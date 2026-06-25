# 搜索协议（SEARCH_PROTOCOL）

> 明烛在需要联网获取资料时，必须遵循本协议。核心原则：**先判领域 → 找业内权威站 → 站内搜 → 交叉验证**。避免在通用搜索引擎里漫无目的检索，导致结果质量参差、信息过时。

---

## 一、三步搜索法

### 第一步：判断领域

收到搜索需求时，先问自己："这属于什么领域？" 常见领域映射：

| 领域关键词 | 领域判定 | 权威站点 |
|------------|----------|----------|
| benchmark、评测、agent、LLM、模型能力 | AI/ML 学术与工程 | arXiv、Papers with Code、Hugging Face、GitHub(THUDM/OpenAI/Confident-AI) |
| 论文、研究、算法、state-of-the-art | 学术研究 | arXiv、Semantic Scholar、Google Scholar、DBLP |
| 框架、库、API、代码实现 | 软件工程 | GitHub、官方文档站、Stack Overflow、MDN |
| 漏洞、CVE、安全 | 网络安全 | NVD、CVE.org、厂商安全公告、Exploit-DB |
| 医学、药物、疾病 | 医学健康 | PubMed、Cochrane、WHO、国家卫健委 |
| 法律、法规、判例 | 法律 | 中国裁判文书网、北大法宝、Westlaw |
| 产品、市场、竞品 | 商业 | 行业报告站、Statista、Crunchbase |
| 新闻、时事 | 资讯 | 通讯社(新华社/路透)、官方发布 |

### 第二步：找业内权威站

确定领域后，**优先在该领域的权威站点内搜索**，而不是直接通用搜索。方法：

- **站内搜索语法**：`site:arxiv.org AgentBench` / `site:github.com agent benchmark`
- **官方文档优先**：框架/库的问题先查官方文档，再查社区
- **一手资料优先**：论文看 arXiv 原文，不看二手解读；代码看 GitHub 仓库 README，不看转载

### 第三步：交叉验证

重要结论必须**至少2个独立来源**印证，避免单一来源偏差。特别是：
- 数据/指标：找原始论文或官方榜单，不采信博客转述
- 代码用法：查官方文档 + 实际跑通，不盲信 AI 生成
- 时效性：标注信息日期，优先近1年内的资料

---

## 二、AI/Agent 领域专用站点清单

明烛作为 AI agent 项目，搜索 AI/agent 相关资料时优先使用以下站点：

### 评测基准（Benchmark）
| 站点 | 用途 | 地址 |
|------|------|------|
| Papers with Code | 查 SOTA 和 benchmark 排行榜 | paperswithcode.com |
| Hugging Face Leaderboards | 模型能力榜单 | huggingface.co/spaces |
| AgentBench (THUDM) | agent 8环境评测 | github.com/THUDM/AgentBench |
| SWE-bench | 软件工程任务评测 | github.com/princeton-nlp/SWE-bench |
| WebArena | 真实网页交互评测 | webarena.dev |
| ToolBench / API-Bank | 工具调用评测 | github.com/OpenBMB/ToolBench |
| GAIA | 通用agent助手评测 | huggingface.co/gaia-benchmark |
| MT-Bench / AlpacaEval | 多轮对话评测 | github.com/lm-sys/FastChat |

### 学术论文
| 站点 | 用途 |
|------|------|
| arXiv | 预印本，AI论文首选 |
| Semantic Scholar | 语义搜索+引用图谱 |
| Google Scholar | 综合学术搜索 |
| DBLP | 计算机科学文献库 |

### 代码与框架
| 站点 | 用途 |
|------|------|
| GitHub | 仓库源码、README、Issues |
| LangChain/LlamaIndex/AutoGen 官方文档 | agent 框架用法 |
| OpenAI/Anthropic/Z.ai 官方文档 | 模型 API |

### 失败模式与安全
| 站点 | 用途 |
|------|------|
| Confident-AI Blog | agent 评测方法论 |
| OWASP LLM Top 10 | LLM 安全风险 |
| garak | LLM 漏洞扫描工具 |

---

## 三、搜索质量自检清单

每次搜索后，问自己：

- [ ] 我判断了领域吗？还是直接通用搜了？
- [ ] 我用了站内搜索（site:）吗？还是只看通用结果？
- [ ] 重要结论有2个以上来源吗？
- [ ] 我标注了信息的时效性吗（是否过时）？
- [ ] 我区分了一手资料（论文/官方）和二手解读（博客）吗？

如果任何一项为"否"，重新搜索。

---

## 四、反模式（禁止）

1. **❌ 直接通用搜索就开干**：不判领域，关键词丢进搜索引擎，拿到什么用什么
2. **❌ 只看中文二手博客**：AI 领域一手资料多为英文，二手解读常有偏差
3. **❌ 不看日期**：用了3年前的过时方案还以为是最佳实践
4. **❌ 单一来源**：只看一篇文章就下结论
5. **❌ 不验证代码**：AI 生成的代码片段不跑就写进项目

---

## 五、本协议的元认知意义

搜索协议本身是"预见"阶段的延伸——在动手搜之前先想清楚"去哪搜、怎么搜"，避免"搜到什么用什么"的执行驱动。这与 `cognitive_cycle` 的 `forethought.task_analysis.info_sufficiency`（信息充分性检查）直接对应：信息不够时，按本协议系统化获取，而非随机检索。
