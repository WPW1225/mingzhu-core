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
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

from agent_system.api import (
    chat_with_details, get_history,
    list_sessions, clear_session, cost_summary,
)

app = FastAPI(title="明烛 Web", version="3.2")


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    """对话接口"""
    try:
        result = chat_with_details(req.message, session_id=req.session_id)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


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
    <div class="nav-item" onclick="showCost()"><span class="nav-icon">💰</span> 成本统计</div>
    <div class="nav-item" onclick="newSession()"><span class="nav-icon">✨</span> 新会话</div>
  </div>
  <div class="sidebar-footer">
    v3.2 · LangGraph + 双LLM<br>智谱GLM + DeepSeek
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
        <span style="font-size:12px;">支持多轮记忆 · 工具调用 · 坎观审查 · 成本监控</span>
      </div>
    </div>
  </div>

  <div class="input-area">
    <div class="input-wrap">
      <textarea class="input-box" id="input" placeholder="输入消息...（Enter发送，Shift+Enter换行）" 
                onkeydown="handleKey(event)" oninput="autoResize(this)"></textarea>
      <button class="send-btn" id="send-btn" onclick="send()">发送</button>
    </div>
  </div>
</div>

<div class="cost-panel" id="cost-panel"></div>

<script>
let sessionId = 'default';
let sending = false;

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
  
  const typingEl = addMessage('mingzhu', '<span class="typing">明烛思考中...</span>', true);
  
  try {
    const resp = await fetch('/api/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message:msg, session_id:sessionId})
    });
    const data = await resp.json();
    typingEl.querySelector('.msg-bubble').innerHTML = data.error ? '[错误] '+data.error : data.output;
    
    if (!data.error) {
      let meta = '';
      if (data.personas && data.personas.length) {
        meta = '<div class="msg-personas">' + data.personas.map(p=>
          `<span class="persona-tag">${p.icon||''} ${p.name}·${p.confidence||''}</span>`).join('') + '</div>';
      }
      meta += `<div class="msg-meta">${data.latency_ms||0}ms`;
      if (data.models && data.models.length) meta += ` · ${data.models.join(',')}`;
      if (data.conflicts && data.conflicts.length) meta += ` · ⚠️${data.conflicts.length}冲突`;
      if (data.vetoed) meta += ` · 🛑否决`;
      meta += '</div>';
      if (data.observer) meta += `<div class="msg-observer">👁 坎观：${data.observer.substring(0,300)}</div>`;
      typingEl.insertAdjacentHTML('beforeend', meta);
    }
  } catch(e) {
    typingEl.querySelector('.msg-bubble').innerHTML = '[网络错误] '+e.message;
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
