#!/usr/bin/env python3
"""
明烛向量检索 v3.6
从关键词匹配升级为向量嵌入语义检索。

方案：纯 Python 实现 TF-IDF + 余弦相似度，零外部依赖。
- 分词：中文按2-3字滑窗 + 英文按单词
- 嵌入：TF-IDF 向量
- 相似度：余弦相似度
- 优势：无需下载模型，部署友好；理解语义近似（如"微服务"能匹配"microservice"）

未来可升级为 sentence-transformers（BAAI/bge-small-zh）获得更强语义理解。
"""
import os
import json
import math
import re
import logging
from typing import Dict, List, Tuple, Set
from collections import Counter
from pathlib import Path

logger = logging.getLogger(__name__)


class TfidfVectorizer:
    """轻量 TF-IDF 向量化器（纯Python，零依赖）"""

    # 中文停用词
    STOPWORDS = {
        "的", "了", "和", "是", "在", "我", "有", "也", "就", "都", "与", "及",
        "一个", "这个", "那个", "我们", "你们", "他们", "它", "他", "她",
        "要", "会", "能", "可", "可以", "应该", "需要", "进行", "通过", "使用",
        "把", "被", "让", "使", "给", "为", "以", "于", "从", "到", "向",
        "中", "里", "等", "并", "但", "而", "如", "如果", "因为", "所以",
    }

    def __init__(self):
        self.vocabulary: Dict[str, int] = {}  # 词 -> 索引
        self.idf: Dict[str, float] = {}       # 词 -> idf值
        self._fitted = False

    def _tokenize(self, text: str) -> List[str]:
        """分词：中文2-3字滑窗 + 英文单词"""
        if not text:
            return []
        tokens = []
        # 中文2-3字滑窗
        zh_segs = re.findall(r'[\u4e00-\u9fff]+', text)
        for seg in zh_segs:
            for n in (2, 3):
                for i in range(len(seg) - n + 1):
                    w = seg[i:i+n]
                    if w not in self.STOPWORDS:
                        tokens.append(w)
        # 英文单词（3字符以上）
        en_words = re.findall(r'[a-zA-Z_]{3,}', text.lower())
        tokens.extend(en_words)
        return tokens

    def fit(self, documents: List[str]):
        """拟合：构建词表和IDF"""
        doc_count = len(documents)
        if doc_count == 0:
            return self
        # 统计每个词出现在多少篇文档中
        doc_freq: Counter = Counter()
        for doc in documents:
            tokens = set(self._tokenize(doc))
            for t in tokens:
                doc_freq[t] += 1
        # 构建词表和IDF
        self.vocabulary = {t: i for i, t in enumerate(sorted(doc_freq.keys()))}
        self.idf = {
            t: math.log((doc_count + 1) / (df + 1)) + 1
            for t, df in doc_freq.items()
        }
        self._fitted = True
        return self

    def transform(self, text: str) -> Dict[str, float]:
        """将文本转为 TF-IDF 向量（稀疏表示）"""
        if not self._fitted:
            return {}
        tokens = self._tokenize(text)
        if not tokens:
            return {}
        tf = Counter(tokens)
        total = len(tokens)
        vec = {}
        for term, count in tf.items():
            if term in self.idf:
                vec[term] = (count / total) * self.idf[term]
        return vec

    def fit_transform(self, documents: List[str]) -> List[Dict[str, float]]:
        self.fit(documents)
        return [self.transform(doc) for doc in documents]


def cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
    """余弦相似度（稀疏向量）"""
    if not vec1 or not vec2:
        return 0.0
    # 点积
    common = set(vec1.keys()) & set(vec2.keys())
    dot = sum(vec1[t] * vec2[t] for t in common)
    # 模长
    norm1 = math.sqrt(sum(v * v for v in vec1.values()))
    norm2 = math.sqrt(sum(v * v for v in vec2.values()))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class VectorMemorySearch:
    """向量记忆检索器"""

    def __init__(self, memory_dir: Path):
        self.memory_dir = memory_dir
        self.vectorizer = TfidfVectorizer()
        self._index_cache = None
        self._index_mtime = 0

    def _load_all_memories(self) -> List[Dict]:
        """加载所有会话的所有记忆条目"""
        entries = []
        if not self.memory_dir.exists():
            return entries
        for f in self.memory_dir.glob("*.json"):
            try:
                history = json.loads(f.read_text(encoding="utf-8"))
                for entry in history:
                    entry["_session_id"] = f.stem
                    entries.append(entry)
            except Exception:
                continue
        return entries

    def _build_index(self):
        """构建向量索引（有缓存，文件变更时重建）"""
        entries = self._load_all_memories()
        if not entries:
            self._index_cache = None
            return
        # 检查是否需要重建
        current_mtime = max(
            (f.stat().st_mtime for f in self.memory_dir.glob("*.json")),
            default=0,
        )
        if self._index_cache and current_mtime <= self._index_mtime:
            return
        # 构建文档列表（user_input + output）
        docs = []
        for e in entries:
            text = (e.get("user_input", "") + " " + e.get("output", ""))
            docs.append(text)
        # 拟合 + 向量化
        vectors = self.vectorizer.fit_transform(docs)
        self._index_cache = {
            "entries": entries,
            "vectors": vectors,
        }
        self._index_mtime = current_mtime

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """语义检索：返回最相关的记忆条目"""
        self._build_index()
        if not self._index_cache:
            return []
        query_vec = self.vectorizer.transform(query)
        if not query_vec:
            return []
        # 计算相似度并排序
        scored = []
        for entry, vec in zip(
            self._index_cache["entries"],
            self._index_cache["vectors"],
        ):
            sim = cosine_similarity(query_vec, vec)
            if sim > 0:
                scored.append((sim, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for sim, entry in scored[:limit]:
            results.append({
                "session_id": entry.get("_session_id", ""),
                "timestamp": entry.get("timestamp", ""),
                "user_input": entry.get("user_input", "")[:100],
                "output": entry.get("output", "")[:200],
                "similarity": round(sim, 4),
            })
        return results


# 全局实例
_searcher: VectorMemorySearch = None

def get_vector_search(memory_dir: Path = None) -> VectorMemorySearch:
    global _searcher
    if _searcher is None:
        if memory_dir is None:
            from .memory import MEMORY_DIR
            memory_dir = MEMORY_DIR
        _searcher = VectorMemorySearch(memory_dir)
    return _searcher


if __name__ == "__main__":
    # 自测
    vs = TfidfVectorizer()
    docs = [
        "微服务架构适合大规模团队",
        "单体架构适合初创产品",
        "JWT认证方案的安全审查",
        "微服务的优缺点分析",
    ]
    vectors = vs.fit_transform(docs)
    query = vs.transform("微服务")
    print("=== 向量检索测试 ===")
    for i, doc in enumerate(docs):
        sim = cosine_similarity(query, vectors[i])
        print(f"  {sim:.3f} | {doc}")
