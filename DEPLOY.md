# LangGraph Cloud 部署指南

## 前置条件

1. LangGraph Cloud 账号（https://langchain.com/cloud）
2. GitHub 仓库已推送（mingzhu-core）
3. `.env` 配置好 API key

## 部署步骤

### 1. 本地开发调试

#### LangGraph Studio（可视化调试）
```bash
pip install langgraph-cli
langgraph dev  # 启动Studio，浏览器打开 http://localhost:2024
```
Studio功能：
- 可视化查看8节点状态图
- 直接输入消息看状态流转
- 修改代码自动热重载

#### LangSmith（trace可观测性）
```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY="你的key"
export LANGCHAIN_PROJECT="mingzhu"
python web_app.py
```
去 https://app.langsmith.com → 选项目"mingzhu" → 看trace链路

### 2. 部署到 LangGraph Cloud

#### 方式A：GitHub集成（推荐）

1. 登录 https://langchain.com/cloud
2. New Project → 选择 GitHub 仓库 `WPW1225/mingzhu-core`
3. LangGraph Cloud 自动读取 `langgraph.json`
4. 配置环境变量：
   - `ZHIPU_API_KEY`
   - `DEEPSEEK_API_KEY`（可选）
   - `LANGCHAIN_API_KEY`（LangSmith trace）
5. Deploy → 每次 git push 自动部署

#### 方式B：CLI部署
```bash
pip install langgraph-cli
langgraph login
langgraph deploy --project mingzhu
langgraph api --project mingzhu  # 获取API地址
```

### 3. 调用部署后的API
```python
from langgraph_sdk import get_client
client = get_client(url="https://your-deployment.langgraph.app")
thread = await client.threads.create()
result = await client.runs.create(
    thread["thread_id"], "mingzhu",
    input={"user_input": "帮我分析JWT认证方案"},
)
```

### 4. 环境变量
`.env` 文件（不入版本控制）：
```
ZHIPU_API_KEY=your-zhipu-key
DEEPSEEK_API_KEY=your-deepseek-key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_PROJECT=mingzhu
```

## 架构说明

明烛 LangGraph 状态图（v5.1 企业级8节点）：
```
initiation（立项）→ planning（规划）
  → [memory_recall | knowledge_learn | direct]
  → execution（执行）→ review（审查）
  → [pass → retrospective | retry → execution]
  → retrospective（复盘）→ END
```

## 故障排查
- Studio无法加载图：检查 `langgraph.json` 路径
- 部署失败：检查依赖是否在 `pyproject.toml` 声明
- API key未生效：检查环境变量
- 节点报错：查看 LangSmith trace
