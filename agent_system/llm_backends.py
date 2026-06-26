#!/usr/bin/env python3
"""
明烛 LLM 后端抽象层 v3.0
支持多 LLM 后端，按场景路由到最合适的模型。

设计原则：
- 双后端：智谱（GLM，默认可用）+ DeepSeek（更便宜，待激活）
- 场景路由：简单任务用 DeepSeek 省钱，复杂推理用 GLM，安全审查用 GLM
- 统一接口：所有后端实现相同的 generate() 方法，上层无感切换
- 安全：API key 只从环境变量读，绝不硬编码

使用方式：
    from agent_system.llm_backends import LLMRouter
    router = LLMRouter()
    result = router.generate("分析这段代码", scene="analysis")
"""
import os
import json
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class Scene(str, Enum):
    """LLM 调用场景，决定路由到哪个后端"""
    SIMPLE = "simple"          # 简单问答、格式化 → DeepSeek（省钱）
    ANALYSIS = "analysis"      # 深度分析、推理 → GLM（质量优先）
    SAFETY = "safety"          # 安全审查、红线检查 → GLM（可靠性优先）
    CREATIVE = "creative"      # 创意生成 → GLM
    JUDGE = "judge"            # LLM-as-a-Judge 评估 → GLM（评估要准）
    ROUTING = "routing"        # 语义路由判断 → DeepSeek（简单分类，省钱）
    DEFAULT = "default"        # 默认 → GLM


@dataclass
class LLMResponse:
    """统一 LLM 响应结构"""
    content: str                       # 生成内容
    model: str = ""                    # 实际使用的模型
    backend: str = ""                  # 后端名称（zhipu/deepseek）
    scene: str = ""                    # 调用场景
    usage: Dict[str, int] = field(default_factory=dict)  # token 用量
    latency_ms: float = 0.0            # 延迟（毫秒）
    error: Optional[str] = None        # 错误信息（成功时为 None）

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.content)


class ZhipuBackend:
    """智谱清言后端（直接 API 调用，OpenAI 兼容格式）

    激活方式：设置环境变量 ZHIPU_API_KEY
    未设置时降级到 z-ai CLI（兼容旧环境）
    """

    name = "zhipu"
    default_model = "glm-4-plus"
    api_base = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    def __init__(self):
        self.api_key = os.environ.get("ZHIPU_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, system_prompt: str = "",
                 temperature: float = 0.3, max_tokens: int = 1500,
                 model: str = None) -> LLMResponse:
        import time as _time
        import urllib.request

        start = _time.time()
        model = model or self.default_model

        # 优先用直接 API 调用（更快更稳定）
        if self.is_available():
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = json.dumps({
                "model": model, "messages": messages,
                "temperature": temperature, "max_tokens": max_tokens,
            }).encode("utf-8")

            try:
                req = urllib.request.Request(
                    self.api_base,
                    data=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                with urllib.request.urlopen(req, timeout=60) as resp_raw:
                    data = json.loads(resp_raw.read().decode("utf-8"))
                latency = (_time.time() - start) * 1000

                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = data.get("usage", {})
                return LLMResponse(
                    content=content, model=data.get("model", model),
                    backend=self.name, usage=usage, latency_ms=latency,
                )
            except Exception as e:
                latency = (_time.time() - start) * 1000
                return LLMResponse(content="", model=model, backend=self.name,
                                 latency_ms=latency, error=f"智谱API异常: {e}")

        # 降级：z-ai CLI（兼容无 key 环境）
        return self._generate_via_cli(prompt, system_prompt, temperature, max_tokens, model, start)

    def _generate_via_cli(self, prompt, system_prompt, temperature, max_tokens, model, start):
        import subprocess
        import time as _time
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"[系统指令]\n{system_prompt}\n\n[用户输入]\n{prompt}"
        try:
            result = subprocess.run(
                ["z-ai", "chat", "-p", full_prompt],
                capture_output=True, text=True, timeout=60,
            )
            latency = (_time.time() - start) * 1000
            if result.returncode != 0:
                return LLMResponse(content="", model=model, backend=self.name,
                                 latency_ms=latency, error=f"z-ai CLI 失败: {result.stderr[:200]}")
            output = result.stdout
            idx = output.find('{')
            if idx < 0:
                return LLMResponse(content=output.strip(), model=model,
                                 backend=self.name, latency_ms=latency)
            data = json.loads(output[idx:])
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return LLMResponse(content=content, model=data.get("model", model),
                             backend=self.name, usage=data.get("usage", {}),
                             latency_ms=latency)
        except subprocess.TimeoutExpired:
            return LLMResponse(content="", model=model, backend=self.name,
                             error="z-ai CLI 超时（60s）")
        except Exception as e:
            return LLMResponse(content="", model=model, backend=self.name,
                             error=f"智谱CLI异常: {e}")


class DeepSeekBackend:
    """DeepSeek 后端（OpenAI 兼容格式，更便宜）

    激活方式：设置环境变量 DEEPSEEK_API_KEY
    未设置时 is_available() 返回 False，路由器会降级到智谱。
    """

    name = "deepseek"
    default_model = "deepseek-chat"
    api_base = "https://api.deepseek.com/v1/chat/completions"

    def __init__(self):
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, system_prompt: str = "",
                 temperature: float = 0.3, max_tokens: int = 1500,
                 model: str = None) -> LLMResponse:
        import time as _time
        import urllib.request

        start = _time.time()
        model = model or self.default_model

        if not self.is_available():
            return LLMResponse(content="", model=model, backend=self.name,
                             error="DEEPSEEK_API_KEY 未设置")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = json.dumps({
            "model": model, "messages": messages,
            "temperature": temperature, "max_tokens": max_tokens,
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                self.api_base,
                data=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=60) as resp_raw:
                data = json.loads(resp_raw.read().decode("utf-8"))
            latency = (_time.time() - start) * 1000

            if "error" in data:
                return LLMResponse(content="", model=model, backend=self.name,
                                 latency_ms=latency,
                                 error=data["error"].get("message", "DeepSeek API 错误"))

            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})
            return LLMResponse(content=content, model=data.get("model", model),
                             backend=self.name, usage=usage, latency_ms=latency)
        except Exception as e:
            return LLMResponse(content="", model=model, backend=self.name,
                             error=f"DeepSeek后端异常: {e}")


class LLMRouter:
    """LLM 路由器：按场景选择后端

    场景路由策略（成本优化）：
    - SIMPLE / ROUTING → DeepSeek（省钱，简单任务不需要强模型）
    - ANALYSIS / SAFETY / CREATIVE / JUDGE / DEFAULT → 智谱 GLM（质量优先）

    降级策略：
    - DeepSeek 不可用（key 未设）→ 降级到智谱
    - 智谱失败 → 返回 error，上层走 fallback
    """

    # 场景 → 首选后端
    SCENE_ROUTING = {
        Scene.SIMPLE: "deepseek",
        Scene.ROUTING: "deepseek",
        Scene.ANALYSIS: "zhipu",
        Scene.SAFETY: "zhipu",
        Scene.CREATIVE: "zhipu",
        Scene.JUDGE: "zhipu",
        Scene.DEFAULT: "zhipu",
    }

    def __init__(self):
        self.zhipu = ZhipuBackend()
        self.deepseek = DeepSeekBackend()
        self._call_log = []  # 调用日志，便于审计

    def get_backend(self, scene: Scene) -> str:
        """根据场景获取首选后端，考虑可用性降级"""
        preferred = self.SCENE_ROUTING.get(scene, "zhipu")
        if preferred == "deepseek" and not self.deepseek.is_available():
            logger.info("DeepSeek 不可用，场景 %s 降级到智谱", scene.value)
            return "zhipu"
        return preferred

    def generate(self, prompt: str, scene: Scene = Scene.DEFAULT,
                 system_prompt: str = "", temperature: float = 0.3,
                 max_tokens: int = 1500) -> LLMResponse:
        """按场景路由生成"""
        backend_name = self.get_backend(scene)
        backend = self.deepseek if backend_name == "deepseek" else self.zhipu

        resp = backend.generate(
            prompt=prompt, system_prompt=system_prompt,
            temperature=temperature, max_tokens=max_tokens,
        )
        resp.scene = scene.value

        # 记录调用日志
        self._call_log.append({
            "scene": scene.value,
            "backend": backend_name,
            "model": resp.model,
            "ok": resp.ok,
            "latency_ms": round(resp.latency_ms, 1),
            "tokens": resp.usage.get("total_tokens", 0),
            "error": resp.error,
        })

        # v3.2: 成本监控（记录到文件，可查询累计费用）
        try:
            from .cost_monitor import get_monitor
            get_monitor().record(
                backend=backend_name, model=resp.model, scene=scene.value,
                usage=resp.usage, latency_ms=resp.latency_ms, ok=resp.ok,
            )
        except Exception:
            pass  # 成本监控失败不影响主流程

        if not resp.ok:
            logger.warning("LLM 调用失败 scene=%s backend=%s: %s",
                          scene.value, backend_name, resp.error)
        return resp

    def get_call_log(self) -> list:
        """获取调用日志（审计用）"""
        return self._call_log.copy()

    def status(self) -> Dict[str, Any]:
        """返回后端状态摘要"""
        return {
            "zhipu": {
                "available": self.zhipu.is_available(),
                "model": self.zhipu.default_model,
                "note": "已激活（直接API）" if self.zhipu.is_available() else "设置 ZHIPU_API_KEY 或降级用 z-ai CLI",
            },
            "deepseek": {
                "available": self.deepseek.is_available(),
                "model": self.deepseek.default_model,
                "note": "已激活" if self.deepseek.is_available() else "设置 DEEPSEEK_API_KEY 环境变量以激活",
            },
            "total_calls": len(self._call_log),
        }


# 全局路由器实例（懒加载）
_router: Optional[LLMRouter] = None

def get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router


if __name__ == "__main__":
    router = get_router()
    print("=== 后端状态 ===")
    print(json.dumps(router.status(), ensure_ascii=False, indent=2))

    print("\n=== 测试智谱（默认场景）===")
    resp = router.generate("用一句话说明什么是认知谦逊", scene=Scene.DEFAULT)
    print(f"  backend={resp.backend} model={resp.model} ok={resp.ok}")
    print(f"  content: {resp.content[:100]}")
    if resp.error:
        print(f"  error: {resp.error}")

    print("\n=== 测试 DeepSeek（简单场景，可能降级）===")
    resp = router.generate("1+1等于几", scene=Scene.SIMPLE)
    print(f"  backend={resp.backend} model={resp.model} ok={resp.ok}")
    print(f"  content: {resp.content[:100]}")
    if resp.error:
        print(f"  error: {resp.error}")

    print("\n=== 调用日志 ===")
    for log in router.get_call_log():
        print(f"  {log}")
