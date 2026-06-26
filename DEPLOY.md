# LangGraph Cloud 部署指南

## 前置条件

1. LangGraph Cloud 账号（https://langchain.com/cloud）
2. GitHub 仓库已推送（mingzhu-core）
3. `.env` 配置好 API key

## 部署步骤

### 1. 本地开发调试（LangGraph Studio）

```bash
# 安装 LangGraph CLI
pip install langgraph-cli

# 启动 Studio（可视化调试）
langgraph dev
# 浏览器打开 http://localhost:2024

# 或启动本地HTTP服务
langgraph serve --port 8000
```

Studio 功能：
- 可视化查看5阶段状态图（initiation→planning→execution→review→retrospective）
- 直接输入消息看状态流转
- 修改代码自动热重载
- 查看每个节点的输入输出

### 2. 部署到 LangGraph Cloud

#### 方式A：GitHub集成（推荐）

1. 登录 https://langchain.com/cloud
2. New Project → 选择 GitHub 仓库 `WPW1225/mingzhu-core`
3. LangGraph Cloud 自动读取 `langgraph.json`
4. 配置环境变量：
   - `ZHIPU_API_KEY`
   - `DEEPSEEK_API_KEY`（可选）
5. Deploy → 每次 git push 自动部署

#### 方式B：CLI部署

```bash
# 安装 CLI
pip install langgraph-cli

# 登录
langgraph login

# 部署
langgraph deploy --project mingzhu

# 获取API地址
langgraph api --project mingzhu
```

### 3. 调用部署后的API

```python
from langgraph_sdk import get_client

client = get_client(url="https://your-deployment.langgraph.app")

# 创建会话
thread = await client.threads.create()

# 发送消息
result = await client.runs.create(
    thread["thread_id"],
    "mingzhu",
    input={"user_input": "帮我分析JWT认证方案"},
)
```

### 4. 环境变量配置

`.env` 文件（不入版本控制）：
```
ZHIPU_API_KEY=your-zhipu-key
DEEPSEEK_API_KEY=your-deepseek-key
```

LangGraph Cloud 控制台也可配置环境变量，优先级高于 `.env`。

## 架构说明

明烛 LangGraph 状态图（v4.1 企业级5阶段）：

```
initiation（立项：CEO接收任务）
    ↓
planning（规划：C-level制定计划）
    ↓
execution（执行：部门并行/串行/讨论）
    ↓
review（审查：观察部+CSO）
    ↓ pass / ↑ retry
retrospective（复盘：CEO汇总+经验沉淀）
    ↓
END
```

## 故障排查

- **Studio 无法加载图**：检查 `langgraph.json` 路径是否正确
- **部署失败**：检查依赖是否在 `pyproject.toml` 声明
- **API key 未生效**：检查环境变量是否配置
- **节点报错**：查看 LangGraph Cloud 日志
