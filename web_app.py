#!/usr/bin/env python3
"""
明烛 Web 界面 v3.2
FastAPI + 单页 HTML，一个文件搞定。

启动：
    python web_app.py
然后浏览器访问：http://localhost:8000

功能：
- 聊天对话（带会话记忆）
- 查看人格调用详情
- 查看坎观观察报告
- 查看成本统计
- 历史会话管理
"""
import sys
import os
import json
import uuid
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional

from agent_system.api import (
    chat_with_details, get_history,
    list_sessions, clear_session, cost_summary, evolution_summary,
    chat_stream, search_memory, evolution_metrics,
    estimate_cost, get_agents_status,
)

app = FastAPI(title="明烛 Web", version="3.6")

# v3.6: 会话级 API key 存储（用户网页填，不入库）
_user_keys = {}
# v3.6: pending clarify 状态（双向通信）
_pending_clarify = {}


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    token: Optional[str] = None


class KeyRequest(BaseModel):
    zhipu_key: str = ""
    deepseek_key: str = ""


class ClarifyRequest(BaseModel):
    stream_id: str
    answer: str


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


@app.post("/api/keys")
async def set_keys(req: KeyRequest):
    """v3.6: 用户设置 API key（存内存，不入库）"""
    token = str(uuid.uuid4())[:8]
    _user_keys[token] = {"zhipu_key": req.zhipu_key, "deepseek_key": req.deepseek_key}
    return JSONResponse({"token": token, "ok": True})


@app.get("/api/keys/status")
async def keys_status():
    return JSONResponse({
        "env_zhipu": bool(os.environ.get("ZHIPU_API_KEY")),
        "env_deepseek": bool(os.environ.get("DEEPSEEK_API_KEY")),
    })


def _apply_user_keys(token: Optional[str]):
    if token and token in _user_keys:
        keys = _user_keys[token]
        if keys["zhipu_key"]:
            os.environ["ZHIPU_API_KEY"] = keys["zhipu_key"]
        if keys["deepseek_key"]:
            os.environ["DEEPSEEK_API_KEY"] = keys["deepseek_key"]


@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    _apply_user_keys(req.token)
    try:
        result = chat_with_details(req.message, session_id=req.session_id)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/chat/stream")
async def api_chat_stream(req: ChatRequest):
    """v3.6: SSE 流式 + clarify 双向通信"""
    _apply_user_keys(req.token)
    stream_id = str(uuid.uuid4())[:8]

    def clarify_callback(question: str) -> str:
        _pending_clarify[stream_id] = {"question": question, "answer": "", "answered": False}
        for _ in range(60):  # 最多等30秒
            time.sleep(0.5)
            if _pending_clarify[stream_id]["answered"]:
                answer = _pending_clarify[stream_id]["answer"]
                _pending_clarify.pop(stream_id, None)
                return answer
        _pending_clarify.pop(stream_id, None)
        return ""

    def event_generator():
        try:
            for event in chat_stream(req.message, session_id=req.session_id,
                                     clarify_callback=clarify_callback):
                if event.get("type") == "clarify":
                    event["stream_id"] = stream_id
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield "data: {\"type\":\"done\"}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type':'error','message':str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/clarify")
async def api_clarify(req: ClarifyRequest):
    """v3.6: 用户回传 clarify 答案"""
    if req.stream_id in _pending_clarify:
        _pending_clarify[req.stream_id]["answer"] = req.answer
        _pending_clarify[req.stream_id]["answered"] = True
        return JSONResponse({"ok": True})
    return JSONResponse({"ok": False, "error": "stream_id 不存在或已过期"}, status_code=404)


@app.get("/api/metrics")
async def api_metrics():
    """v3.6: 进化效果量化"""
    return JSONResponse(evolution_metrics())


@app.post("/api/search")
async def api_search(req: ChatRequest):
    """v3.6: 记忆语义检索"""
    results = search_memory(req.message)
    return JSONResponse(results)


# ============================================================
# v3.8: RESTful API（资源路径式）
# ============================================================

@app.get("/api/v1/sessions")
async def v1_list_sessions():
    """GET /api/v1/sessions - 列出所有会话"""
    return JSONResponse(list_sessions())


@app.get("/api/v1/sessions/{session_id}")
async def v1_get_session(session_id: str):
    """GET /api/v1/sessions/{id} - 获取某会话历史"""
    return JSONResponse(get_history(session_id))


@app.delete("/api/v1/sessions/{session_id}")
async def v1_delete_session(session_id: str):
    """DELETE /api/v1/sessions/{id} - 删除某会话"""
    ok = clear_session(session_id)
    return JSONResponse({"deleted": ok, "session_id": session_id})


@app.post("/api/v1/chat")
async def v1_chat(req: ChatRequest):
    """POST /api/v1/chat - 发送消息（非流式）"""
    _apply_user_keys(req.token)
    try:
        result = chat_with_details(req.message, session_id=req.session_id)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/v1/metrics")
async def v1_metrics():
    """GET /api/v1/metrics - 进化指标"""
    return JSONResponse(evolution_metrics())


@app.get("/api/v1/cost")
async def v1_cost():
    """GET /api/v1/cost - 成本统计"""
    return JSONResponse(cost_summary())


@app.post("/api/v1/search")
async def v1_search(query: str):
    """POST /api/v1/search?q=xxx - 记忆检索"""
    return JSONResponse(search_memory(query))


# v4.5: 成本预估 + agent状态
@app.post("/api/v1/estimate")
async def v1_estimate(req: ChatRequest):
    """POST /api/v1/estimate - 执行前成本预估"""
    return JSONResponse(estimate_cost(req.message))


@app.get("/api/v1/agents/status")
async def v1_agents_status():
    """GET /api/v1/agents/status - 所有agent状态"""
    return JSONResponse(get_agents_status())


@app.get("/api/sessions")
async def api_sessions():
    """列出所有会话"""
    return JSONResponse(list_sessions())


@app.get("/api/history/{session_id}")
async def api_history(session_id: str):
    """获取某会话历史"""
    return JSONResponse(get_history(session_id))


@app.delete("/api/session/{session_id}")
async def api_clear_session(session_id: str):
    """清除某会话"""
    ok = clear_session(session_id)
    return JSONResponse({"cleared": ok})


@app.get("/api/cost")
async def api_cost():
    """成本统计"""
    return JSONResponse(cost_summary())


# ============================================================
# 单页 HTML（内嵌，无需静态文件）
# ============================================================

HTML_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>明烛 · 丁火烛照</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
       background: #0f1117; color: #e4e4e7; height:100vh; display:flex; }
/* 侧边栏 */
.sidebar { width:240px; background:#181a20; border-right:1px solid #27272a; display:flex; flex-direction:column; }
.sidebar-header { padding:20px; border-bottom:1px solid #27272a; }
.sidebar-header h1 { font-size:18px; color:#f59e0b; }
.sidebar-header p { font-size:12px; color:#71717a; margin-top:4px; }
.sidebar-nav { flex:1; overflow-y:auto; padding:12px; }
.nav-item { padding:10px 12px; border-radius:8px; cursor:pointer; font-size:14px; margin-bottom:4px; display:flex; align-items:center; gap:8px; }
.nav-item:hover { background:#27272a; }
.nav-item.active { background:#3f3f46; }
.nav-icon { font-size:16px; }
.sidebar-footer { padding:12px; border-top:1px solid #27272a; font-size:12px; color:#71717a; }
/* 主区 */
.main { flex:1; display:flex; flex-direction:column; }
.topbar { padding:16px 24px; border-bottom:1px solid #27272a; display:flex; justify-content:space-between; align-items:center; }
.topbar h2 { font-size:16px; font-weight:500; }
.session-input { background:#27272a; border:1px solid #3f3f46; color:#e4e4e7; padding:6px 12px; border-radius:6px; font-size:13px; width:180px; }
.btn { background:#3f3f46; color:#e4e4e7; border:none; padding:6px 14px; border-radius:6px; cursor:pointer; font-size:13px; }
.btn:hover { background:#52525b; }
.btn-primary { background:#f59e0b; color:#000; }
.btn-primary:hover { background:#fbbf24; }
/* 聊天区 */
.chat-area { flex:1; overflow-y:auto; padding:24px; }
.message { max-width:760px; margin:0 auto 20px; }
.msg-role { font-size:12px; color:#71717a; margin-bottom:4px; display:flex; align-items:center; gap:6px; }
.msg-bubble { padding:14px 18px; border-radius:12px; font-size:14px; line-height:1.7; white-space:pre-wrap; }
.msg-user .msg-bubble { background:#27272a; margin-left:60px; }
.msg-mingzhu .msg-bubble { background:#1c1917; border:1px solid #3f3f46; margin-right:60px; }
.msg-meta { font-size:11px; color:#52525b; margin-top:6px; }
.msg-personas { margin-top:8px; }
.persona-tag { display:inline-block; background:#3f3f46; padding:2px 8px; border-radius:4px; font-size:11px; margin-right:4px; }
.msg-observer { margin-top:8px; padding:8px 12px; background:#181a20; border-left:3px solid #6366f1; font-size:12px; color:#a1a1aa; border-radius:0 6px 6px 0; }
/* 输入区 */
.input-area { padding:16px 24px; border-top:1px solid #27272a; }
.input-wrap { max-width:760px; margin:0 auto; display:flex; gap:12px; }
.input-box { flex:1; background:#27272a; border:1px solid #3f3f46; color:#e4e4e7; padding:12px 16px; border-radius:8px; font-size:14px; resize:none; height:48px; max-height:120px; }
.input-box:focus { outline:none; border-color:#f59e0b; }
.send-btn { background:#f59e0b; color:#000; border:none; padding:0 24px; border-radius:8px; cursor:pointer; font-size:14px; font-weight:500; }
.send-btn:hover { background:#fbbf24; }
.send-btn:disabled { background:#52525b; color:#71717a; cursor:not-allowed; }
/* 成本面板 */
.cost-panel { position:fixed; bottom:80px; right:24px; background:#181a20; border:1px solid #3f3f46; border-radius:8px; padding:12px 16px; font-size:12px; display:none; }
.cost-panel.show { display:block; }
.cost-total { font-size:18px; color:#f59e0b; font-weight:600; }
.typing { color:#71717a; font-style:italic; }
.modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.7); display:none; align-items:center; justify-content:center; z-index:200; }
.modal-overlay.show { display:flex; }
.modal { background:#181a20; border:1px solid #3f3f46; border-radius:12px; padding:24px; max-width:440px; width:90%; }
.modal h3 { font-size:16px; color:#f59e0b; margin-bottom:16px; }
.modal input { width:100%; background:#27272a; border:1px solid #3f3f46; color:#e4e4e7; padding:10px 12px; border-radius:6px; font-size:13px; margin-bottom:12px; }
.modal input:focus { outline:none; border-color:#f59e0b; }
.modal label { font-size:12px; color:#71717a; display:block; margin-bottom:4px; }
.modal-actions { display:flex; gap:8px; justify-content:flex-end; margin-top:16px; }
.clarify-modal { border-color:#f59e0b; }
.clarify-question { font-size:14px; color:#e4e4e7; margin-bottom:12px; line-height:1.6; }
.self-score { margin-top:8px; padding:8px 12px; background:#1a1a2e; border-left:3px solid #f59e0b; font-size:12px; border-radius:0 6px 6px 0; }
.self-score-bar { height:6px; background:#27272a; border-radius:3px; margin-top:4px; overflow:hidden; }
.self-score-fill { height:100%; background:linear-gradient(90deg,#ef4444,#f59e0b,#22c55e); border-radius:3px; }
.metrics-page { padding:24px; max-width:800px; margin:0 auto; display:none; }
.metrics-page.show { display:block; }
.metric-card { background:#181a20; border:1px solid #3f3f46; border-radius:8px; padding:16px; margin-bottom:12px; }
.metric-card h4 { font-size:13px; color:#71717a; margin-bottom:8px; }
.metric-value { font-size:28px; color:#f59e0b; font-weight:600; }
.metric-trend { font-size:12px; margin-top:4px; }
.trend-up { color:#22c55e; }
.trend-down { color:#ef4444; }
.chart-bar { display:flex; align-items:end; gap:4px; height:80px; margin-top:12px; }
.bar { flex:1; background:#f59e0b; border-radius:2px 2px 0 0; min-height:4px; transition:height 0.3s; }
.stream-step { font-size:12px; color:#a1a1aa; padding:2px 0 2px 8px; border-left:2px solid #3f3f46; margin:2px 0; }
.stream-output { font-size:14px; line-height:1.7; white-space:pre-wrap; margin-top:8px; }
</style>
</head>
<body>
<div class="sidebar">
  <div class="sidebar-header">
    <h1>🕯 明烛</h1>
    <p>丁火烛照，照亮未知</p>
  </div>
  <div class="sidebar-nav">
    <div class="nav-item active" onclick="showChat()"><span class="nav-icon">💬</span> 对话</div>
    <div class="nav-item" onclick="showSessions()"><span class="nav-icon">📋</span> 历史会话</div>
    <div class="nav-item" onclick="showMetrics()"><span class="nav-icon">📈</span> 进化指标</div>
    <div class="nav-item" onclick="showAgents()"><span class="nav-icon">🤖</span> Agent状态</div>
    <div class="nav-item" onclick="showCost()"><span class="nav-icon">💰</span> 成本统计</div>
    <div class="nav-item" onclick="showKeyModal()"><span class="nav-icon">🔑</span> API配置</div>
    <div class="nav-item" onclick="newSession()"><span class="nav-icon">✨</span> 新会话</div>
  </div>
  <div class="sidebar-footer">
    v3.6 · LangGraph + 双LLM<br>智谱GLM + DeepSeek
  </div>
</div>

<div class="main">
  <div class="topbar">
    <h2 id="view-title">对话</h2>
    <div>
      <span style="font-size:12px;color:#71717a;margin-right:8px;">会话ID:</span>
      <input class="session-input" id="session-id" value="default" onchange="changeSession()">
    </div>
  </div>

  <div class="chat-area" id="chat-area">
    <div class="message">
      <div class="msg-bubble" style="background:#1c1917;border:1px solid #3f3f46;text-align:center;color:#71717a;">
        明烛已就绪。输入你的问题开始对话。<br><br>
        <span style="font-size:12px;">支持多轮记忆 · 工具调用 · 坎观审查 · 人机协作 · 自我进化</span>
      </div>
    </div>
  </div>

  <div class="metrics-page" id="metrics-page">
    <h2 style="color:#f59e0b;margin-bottom:16px;">📈 进化效果量化</h2>
    <div id="metrics-content">加载中...</div>
  </div>

  <div class="metrics-page" id="agents-page">
    <h2 style="color:#f59e0b;margin-bottom:16px;">🤖 Agent状态</h2>
    <div id="agents-content">加载中...</div>
  </div>

  <div class="input-area">
    <div id="cost-estimate" style="max-width:760px;margin:0 auto 8px;font-size:12px;color:#a1a1aa;background:#1c1917;padding:6px 12px;border-radius:6px;display:none;"></div>
    <div class="input-wrap">
      <textarea class="input-box" id="input" placeholder="输入消息...（Enter发送，Shift+Enter换行）" 
                onkeydown="handleKey(event)" oninput="autoResize(this);estimateCost()"></textarea>
      <button class="send-btn" id="send-btn" onclick="send()">发送</button>
    </div>
  </div>
</div>

<div class="cost-panel" id="cost-panel"></div>

<!-- v3.6: API key 配置弹窗 -->
<div class="modal-overlay" id="key-modal">
  <div class="modal">
    <h3>🔑 API Key 配置</h3>
    <p style="font-size:12px;color:#71717a;margin-bottom:16px;">key 只存在内存中，不入库，刷新后需重新填写。或服务器设环境变量可免填。</p>
    <label>智谱 API Key（必需）</label>
    <input id="zhipu-key-input" placeholder="7cabdd25... 或留空用环境变量">
    <label>DeepSeek API Key（可选，省钱）</label>
    <input id="deepseek-key-input" placeholder="sk-... 或留空">
    <div class="modal-actions">
      <button class="send-btn" onclick="saveKeys()">保存</button>
    </div>
  </div>
</div>

<!-- v3.6: clarify 弹窗 -->
<div class="modal-overlay" id="clarify-modal">
  <div class="modal clarify-modal">
    <h3>❓ 明烛想确认</h3>
    <div class="clarify-question" id="clarify-question"></div>
    <input id="clarify-answer" placeholder="输入你的回答..." onkeydown="if(event.key==='Enter')submitClarify()">
    <div class="modal-actions">
      <button class="send-btn" onclick="submitClarify()">回答</button>
      <button class="send-btn" style="background:#52525b;" onclick="skipClarify()">跳过</button>
    </div>
  </div>
</div>

<script>
let sessionId = 'default';
let sending = false;
let userToken = null;
let pendingClarifyStreamId = null;

// v3.6: API key 管理
async function saveKeys() {
  const zhipu = document.getElementById('zhipu-key-input').value.trim();
  const deepseek = document.getElementById('deepseek-key-input').value.trim();
  const resp = await fetch('/api/keys', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({zhipu_key:zhipu, deepseek_key:deepseek})
  });
  const data = await resp.json();
  userToken = data.token;
  document.getElementById('key-modal').classList.remove('show');
  if (zhipu) addMessage('mingzhu', '✅ API Key 已配置，可以开始对话了');
}
function showKeyModal() { document.getElementById('key-modal').classList.add('show'); }

// v3.6: clarify 双向通信
function showClarify(question, streamId) {
  pendingClarifyStreamId = streamId;
  document.getElementById('clarify-question').textContent = question;
  document.getElementById('clarify-answer').value = '';
  document.getElementById('clarify-modal').classList.add('show');
  document.getElementById('clarify-answer').focus();
}
async function submitClarify() {
  const answer = document.getElementById('clarify-answer').value.trim();
  if (pendingClarifyStreamId) {
    await fetch('/api/clarify', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({stream_id:pendingClarifyStreamId, answer:answer})
    });
  }
  document.getElementById('clarify-modal').classList.remove('show');
  pendingClarifyStreamId = null;
}
async function skipClarify() {
  if (pendingClarifyStreamId) {
    await fetch('/api/clarify', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({stream_id:pendingClarifyStreamId, answer:''})
    });
  }
  document.getElementById('clarify-modal').classList.remove('show');
  pendingClarifyStreamId = null;
}

// v3.6: 进化指标页
async function showMetrics() {
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  event.target.closest('.nav-item').classList.add('active');
  document.getElementById('view-title').textContent = '进化指标';
  document.getElementById('chat-area').style.display = 'none';
  document.querySelector('.input-area').style.display = 'none';
  document.getElementById('metrics-page').classList.add('show');
  const resp = await fetch('/api/metrics');
  const data = await resp.json();
  renderMetrics(data);
}
function renderMetrics(data) {
  const c = document.getElementById('metrics-content');
  if (data.status === 'no_data') {
    c.innerHTML = '<div class="metric-card"><p>'+data.message+'</p></div>';
    return;
  }
  const trendClass = data.correction_trend.includes('下降') ? 'trend-up' : 'trend-down';
  c.innerHTML = `
    <div class="metric-card">
      <h4>总经验数</h4>
      <div class="metric-value">${data.total_experiences}</div>
      <div class="metric-trend">可复用教训：${data.reusable_lessons}（复用率${data.reuse_rate*100}%）</div>
    </div>
    <div class="metric-card">
      <h4>纠正下降率（是否越用越好）</h4>
      <div class="metric-value">${(data.recent_correction_rate*100).toFixed(0)}%</div>
      <div class="metric-trend ${trendClass}">早期${(data.early_correction_rate*100).toFixed(0)}% → 近期${(data.recent_correction_rate*100).toFixed(0)}% · ${data.correction_trend}</div>
      <div class="chart-bar">
        <div class="bar" style="height:${data.early_correction_rate*100}%;background:#ef4444;" title="早期"></div>
        <div class="bar" style="height:${data.recent_correction_rate*100}%;background:#22c55e;" title="近期"></div>
      </div>
    </div>
    <div class="metric-card">
      <h4>学到的偏好</h4>
      <div class="metric-value">${data.preferences_learned}</div>
      <div class="metric-trend">元元认知均分：${data.avg_meta_cognition_score}</div>
    </div>
    <div class="metric-card">
      <h4>综合判定</h4>
      <div class="metric-value" style="font-size:18px;">${data.verdict}</div>
    </div>`;
}
function showChat() {
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  event.target.closest('.nav-item').classList.add('active');
  document.getElementById('view-title').textContent = '对话';
  document.getElementById('chat-area').style.display = 'block';
  document.querySelector('.input-area').style.display = 'block';
  document.getElementById('metrics-page').classList.remove('show');
  document.getElementById('agents-page').classList.remove('show');
}

// v4.5: Agent状态页
async function showAgents() {
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  event.target.closest('.nav-item').classList.add('active');
  document.getElementById('view-title').textContent = 'Agent状态';
  document.getElementById('chat-area').style.display = 'none';
  document.querySelector('.input-area').style.display = 'none';
  document.getElementById('metrics-page').classList.remove('show');
  document.getElementById('agents-page').classList.add('show');
  const resp = await fetch('/api/v1/agents/status');
  const data = await resp.json();
  renderAgents(data);
}
function renderAgents(data) {
  const wt = data.wu_cang || {};
  const jm = data.jia_jue || {};
  const evo = data.evolution || {};
  const cost = data.cost || {};
  const personas = data.personas || [];
  const ceo = data.ceo || {};
  const meta = data.meta_cognition || {};
  const ls = data.langsmith || {};

  // 8个执行人格卡片
  let personasHtml = personas.map(p =>
    `<span class="persona-tag" title="${p.element}">${p.icon} ${p.name}</span>`
  ).join('');

  document.getElementById('agents-content').innerHTML = `
    <div class="metric-card"><h4>👑 ${ceo.role}</h4>
      <div style="font-size:13px;">
        5阶段: ${ceo.phases?.join(' → ') || '-'}<br>
        策略: ${ceo.strategies?.join(' / ') || '-'}
      </div>
    </div>
    <div class="metric-card"><h4>🎯 8个执行人格（MoE）</h4>
      <div style="margin-top:8px;">${personasHtml || '加载中'}</div>
    </div>
    <div class="metric-card"><h4>🏔️ 戊藏·记忆官</h4>
      <div>会话: ${wt.total_sessions||0} | 记忆: ${wt.total_memories||0} | 遗忘阈值: ${wt.forget_threshold||50}</div>
    </div>
    <div class="metric-card"><h4>🌳 甲觉·学习官</h4>
      <div>知识: ${jm.total_knowledge||0} 条</div>
      <div style="font-size:12px;color:#71717a;margin-top:4px;">主题: ${(jm.topics||[]).join(', ')||'无'}</div>
    </div>
    <div class="metric-card"><h4>🧬 进化系统</h4>
      <div>经验: ${evo.total_experiences||0} | 纠正率: ${(evo.recent_correction_rate*100||0).toFixed(0)}% | ${evo.correction_trend||'-'}</div>
    </div>
    <div class="metric-card"><h4>🪞 元元认知</h4>
      <div>${meta.available ? '已启用' : '未启用'} | 维度: ${(meta.dimensions||[]).join('/')}</div>
    </div>
    <div class="metric-card"><h4>💰 成本</h4>
      <div>调用: ${cost.total_calls||0}次 | 费用: ¥${cost.total_cost||0} | token: ${cost.total_tokens||0}</div>
    </div>
    <div class="metric-card"><h4>📊 LangSmith</h4>
      <div>${ls.enabled ? '✅ 已启用' : '❌ 未配置'} | 项目: ${ls.project||'-'}
      ${ls.enabled ? `<br><a href="${ls.url}" target="_blank" style="color:#f59e0b;">→ 打开LangSmith</a>` : ''}</div>
    </div>`;
}

// v4.5: 成本预估（输入时实时显示）
async function estimateCost() {
  const input = document.getElementById('input');
  const msg = input.value.trim();
  const est = document.getElementById('cost-estimate');
  if (msg.length < 5) { est.style.display='none'; return; }
  const resp = await fetch('/api/v1/estimate', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({message:msg, session_id:sessionId})
  });
  const data = await resp.json();
  est.style.display = 'block';
  est.innerHTML = `📊 预估: ${data.strategy}策略 | ${data.estimated_personas}人格 | ~${data.estimated_tokens}tokens | ¥${data.estimated_cost_yuan}${data.warning?' ⚠️ '+data.warning:''}`;
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
}
function autoResize(el) { el.style.height='48px'; el.style.height=Math.min(el.scrollHeight,120)+'px'; }

async function send() {
  if (sending) return;
  const input = document.getElementById('input');
  const msg = input.value.trim();
  if (!msg) return;
  input.value=''; input.style.height='48px';
  
  addMessage('user', msg);
  sending = true;
  document.getElementById('send-btn').disabled = true;
  
  // v3.5: SSE 流式输出
  const typingEl = addMessage('mingzhu', '<div class="stream-progress">明烛思考中...</div>', true);
  const bubbleEl = typingEl.querySelector('.msg-bubble');
  let progressHtml = '';
  let finalOutput = '';
  let metaHtml = '';
  
  try {
    const resp = await fetch('/api/chat/stream', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message:msg, session_id:sessionId, token:userToken})
    });
    
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, {stream:true});
      const lines = buffer.split('\\n');
      buffer = lines.pop();
      
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const event = JSON.parse(line.slice(6));
          if (event.type === 'routing') {
            progressHtml += `<div class="stream-step">📍 路由: ${event.personas.join(',')} (${event.method})</div>`;
          } else if (event.type === 'schedule') {
            progressHtml += `<div class="stream-step">⚙️ 调度: ${event.strategy}</div>`;
          } else if (event.type === 'tool') {
            progressHtml += `<div class="stream-step">🔧 ${event.info}</div>`;
          } else if (event.type === 'clarify') {
            // v3.6: 人机协作——弹窗收集回答
            showClarify(event.question, event.stream_id);
          } else if (event.type === 'persona_done') {
            const conf = event.confidence || '';
            progressHtml += `<div class="stream-step">✦ ${event.name} [${conf}] ${event.content.substring(0,60)}...</div>`;
          } else if (event.type === 'synthesizing') {
            progressHtml += `<div class="stream-step">📝 离明汇总中...</div>`;
          } else if (event.type === 'output') {
            finalOutput = event.content;
          } else if (event.type === 'observer') {
            if (event.content) metaHtml += `<div class="msg-observer">👁 坎观：${event.content.substring(0,300)}</div>`;
          } else if (event.type === 'done') {
            if (event.latency_ms) metaHtml = `<div class="msg-meta">${event.latency_ms}ms${event.models?' · '+event.models.join(','):''}</div>` + metaHtml;
            // v3.6: 自评显示
            if (event.self_score && event.self_score.overall) {
              const s = event.self_score;
              metaHtml += `<div class="self-score">🪞 明烛自评：${s.overall}分 · ${s.one_line}<div class="self-score-bar"><div class="self-score-fill" style="width:${s.overall}%"></div></div></div>`;
            }
          }
          // 更新显示
          bubbleEl.innerHTML = progressHtml + (finalOutput ? '<hr style="border-color:#3f3f46"><div class="stream-output">'+finalOutput+'</div>' : '') + metaHtml;
          document.getElementById('chat-area').scrollTop = 999999;
        } catch(e) {}
      }
    }
    if (!finalOutput) bubbleEl.innerHTML = '[无输出]';
  } catch(e) {
    bubbleEl.innerHTML = '[网络错误] '+e.message;
  }
  sending = false;
  document.getElementById('send-btn').disabled = false;
  document.getElementById('chat-area').scrollTop = 999999;
}

function addMessage(role, content, isTemp=false) {
  const area = document.getElementById('chat-area');
  const div = document.createElement('div');
  div.className = 'message msg-'+role;
  div.innerHTML = `<div class="msg-role">${role==='user'?'你':'🕯 明烛'}</div>
                   <div class="msg-bubble">${content}</div>`;
  area.appendChild(div);
  area.scrollTop = 999999;
  return div;
}

function changeSession() {
  sessionId = document.getElementById('session-id').value || 'default';
  document.getElementById('chat-area').innerHTML = '';
  addMessage('mingzhu', `已切换到会话 <b>${sessionId}</b>。输入问题开始对话。`);
}

function newSession() {
  sessionId = 'session-' + Date.now().toString(36);
  document.getElementById('session-id').value = sessionId;
  document.getElementById('chat-area').innerHTML = '';
  addMessage('mingzhu', `新会话 <b>${sessionId}</b> 已创建。`);
}

function showChat() {
  document.getElementById('view-title').textContent = '对话';
  document.getElementById('cost-panel').classList.remove('show');
}

async function showSessions() {
  document.getElementById('view-title').textContent = '历史会话';
  const area = document.getElementById('chat-area');
  area.innerHTML = '';
  try {
    const resp = await fetch('/api/sessions');
    const sessions = await resp.json();
    if (!sessions.length) {
      addMessage('mingzhu', '暂无历史会话。');
      return;
    }
    sessions.forEach(s => {
      const div = document.createElement('div');
      div.className = 'message';
      div.innerHTML = `<div class="msg-bubble" style="cursor:pointer" onclick="loadSession('${s.session_id}')">
        <b>${s.session_id}</b> · ${s.turns}轮<br>
        <span style="color:#71717a;font-size:12px;">最后：${s.last_input} | ${s.last_time}</span>
      </div>`;
      area.appendChild(div);
    });
  } catch(e) { addMessage('mingzhu','[错误] '+e.message); }
}

function loadSession(sid) {
  sessionId = sid;
  document.getElementById('session-id').value = sid;
  document.getElementById('view-title').textContent = '对话';
  loadHistory();
}

async function loadHistory() {
  const area = document.getElementById('chat-area');
  area.innerHTML = '';
  try {
    const resp = await fetch('/api/history/'+sessionId);
    const hist = await resp.json();
    if (!hist.length) { addMessage('mingzhu','该会话无历史记录。'); return; }
    hist.forEach(h => {
      addMessage('user', h.user_input);
      addMessage('mingzhu', h.output);
    });
  } catch(e) { addMessage('mingzhu','[错误] '+e.message); }
}

async function showCost() {
  const panel = document.getElementById('cost-panel');
  try {
    const resp = await fetch('/api/cost');
    const data = await resp.json();
    let html = `<div class="cost-total">¥${data.total_cost}</div>`;
    html += `<div style="color:#71717a;margin-top:4px;">${data.total_calls}次调用 · ${data.total_tokens}tokens</div>`;
    if (data.by_backend) {
      html += '<div style="margin-top:8px;border-top:1px solid #3f3f46;padding-top:8px;">';
      for (const [k,v] of Object.entries(data.by_backend)) {
        html += `<div>${k}: ${v.calls}次 ¥${v.cost}</div>`;
      }
      html += '</div>';
    }
    panel.innerHTML = html;
    panel.classList.toggle('show');
  } catch(e) { panel.innerHTML='[错误] '+e.message; panel.classList.add('show'); }
}
</script>
</body>
</html>"""


if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("  明烛 Web 启动中...")
    print("  浏览器访问: http://localhost:8000")
    print("  Ctrl+C 退出")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
