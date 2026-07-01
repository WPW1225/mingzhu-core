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
    estimate_conversation_cost, get_agents_status,
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
    return JSONResponse(estimate_conversation_cost(req.message))


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
# 单页 HTML（从 templates/index.html 加载，便于维护）
# ============================================================

_TEMPLATE_DIR = Path(__file__).parent / "templates"

def _load_html_page() -> str:
    """从 templates/index.html 加载页面，加载失败时返回降级页面"""
    try:
        return (_TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")
    except Exception as e:
        return f"<html><body><h1>模板加载失败: {e}</h1></body></html>"

HTML_PAGE = _load_html_page()



if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("  明烛 Web 启动中...")
    print("  浏览器访问: http://localhost:8000")
    print("  Ctrl+C 退出")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
