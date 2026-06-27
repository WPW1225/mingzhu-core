#!/usr/bin/env python3
"""
明烛 JSON Mode 强制输出 v3.7
解决"LLM输出缺乏保障"问题：强制JSON格式 + Schema校验 + 失败重试。
"""
import json
import re
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def extract_json(text: str) -> Optional[Dict]:
    """从LLM输出中提取JSON（容错：markdown代码块、前后文字、嵌套）"""
    if not text:
        return None
    text = re.sub(r'```(?:json)?\s*', '', text).replace('```', '')
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # 提取嵌套JSON
    start = text.find('{')
    if start >= 0:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '{': depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i+1])
                    except json.JSONDecodeError:
                        pass
    return None


def force_json_output(prompt: str, router, schema: Dict = None,
                      max_retries: int = 2, scene=None) -> Dict:
    """强制LLM输出JSON，失败重试，返回dict"""
    from .llm_backends import Scene
    if scene is None:
        scene = Scene.JUDGE
    schema_hint = ""
    if schema:
        fields = ", ".join(f'"{k}": <{v}>' for k, v in schema.items())
        schema_hint = f"\n必须返回JSON：{{{fields}}}"
    full_prompt = prompt + schema_hint + "\n只返回JSON，不要其他文字。"
    resp = None
    for attempt in range(max_retries + 1):
        resp = router.generate(full_prompt, scene=scene)
        if not resp.ok:
            continue
        result = extract_json(resp.content)
        if result is not None:
            if schema:
                missing = [k for k in schema if k not in result]
                if missing:
                    full_prompt = f"缺少字段{missing}，重新返回完整JSON。\n" + prompt + schema_hint
                    continue
            return result
        full_prompt = f"上次不是有效JSON，只返回JSON。\n" + prompt + schema_hint
    return {"_error": "JSON解析失败", "_raw": resp.content[:200] if resp else ""}


if __name__ == "__main__":
    for t in ['{"a":1}', '```json\n{"a":1}\n```', '结果{"a":1,"b":{"c":2}}完', '非json']:
        print(f"{t[:25]:25s} → {extract_json(t)}")
