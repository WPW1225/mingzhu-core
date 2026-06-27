#!/usr/bin/env python3
"""
明烛占星服务 v3.8
将 ASTRO.md 硬编码数据封装为独立服务，便于扩展和替换。

设计：
- AstroService 类：统一占星数据访问接口
- 数据从 ASTRO.md 提取为结构化配置
- 未来可替换为 pyswisseph 实时计算或其他占星API
- 解耦：其他模块通过此服务访问占星数据，不直接读 ASTRO.md
"""
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

ASTRO_FILE = Path(__file__).parent.parent / "master_profile" / "ASTRO.md"


@dataclass
class AstroData:
    """占星数据结构"""
    birth_date: str = ""
    birth_place: str = ""
    sun_sign: str = ""        # 太阳星座
    moon_sign: str = ""       # 月亮星座
    ascendant: str = ""       # 上升星座
    chinese_zodiac: str = ""  # 生肖
    raw_text: str = ""        # 原始ASTRO.md内容


class AstroService:
    """占星服务（封装数据访问，未来可替换为实时计算）"""

    _instance = None
    _data: Optional[AstroData] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._data is None:
            self._load()

    def _load(self):
        """加载占星数据（从ASTRO.md提取，未来可改为API/pyswisseph）"""
        # 优先从环境变量读（隐私保护）
        import os
        birth_date = os.environ.get("MZ_BIRTH_DATE", "")
        birth_place = os.environ.get("MZ_BIRTH_PLACE", "")
        sun = os.environ.get("MZ_SUN_SIGN", "")
        moon = os.environ.get("MZ_MOON_SIGN", "")
        asc = os.environ.get("MZ_ASCENDANT", "")

        raw = ""
        if ASTRO_FILE.exists():
            raw = ASTRO_FILE.read_text(encoding="utf-8")
            # 从ASTRO.md提取（如果环境变量没设）
            if not sun:
                import re
                m = re.search(r'☉.*?太阳.*?(\d+°\d+\'?\s*\S+)', raw)
                if m: sun = m.group(1)
            if not moon:
                import re
                m = re.search(r'☽.*?月亮.*?(\d+°\d+\'?\s*\S+)', raw)
                if m: moon = m.group(1)

        self._data = AstroData(
            birth_date=birth_date or "见.env",
            birth_place=birth_place or "见.env",
            sun_sign=sun or "摩羯座",
            moon_sign=moon or "处女座",
            ascendant=asc or "双子座",
            chinese_zodiac="马",
            raw_text=raw[:500],  # 只缓存摘要
        )
        logger.info("占星数据已加载")

    def get_data(self) -> AstroData:
        return self._data

    def get_summary(self) -> Dict:
        """获取占星摘要（非敏感）"""
        d = self._data
        return {
            "sun_sign": d.sun_sign,
            "moon_sign": d.moon_sign,
            "ascendant": d.ascendant,
            "chinese_zodiac": d.chinese_zodiac,
        }

    def reload(self):
        """重新加载（配置变更后）"""
        self._data = None
        self._load()


# 全局实例
_astro_service: Optional[AstroService] = None

def get_astro() -> AstroService:
    global _astro_service
    if _astro_service is None:
        _astro_service = AstroService()
    return _astro_service


if __name__ == "__main__":
    astro = get_astro()
    print("=== 占星数据 ===")
    print(json.dumps(astro.get_summary(), ensure_ascii=False, indent=2))
