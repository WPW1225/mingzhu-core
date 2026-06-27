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
import time
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
    common = set(vec1.keys()) & set(vec2.keys())
    dot = sum(vec1[t] * vec2[t] for t in common)
    norm1 = math.sqrt(sum(v * v for v in vec1.values()))
    norm2 = math.sqrt(sum(v * v for v in vec2.values()))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def cosine_sim_dense(v1: List[float], v2: List[float]) -> float:
    """余弦相似度（稠密向量，用于embedding）"""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)


class ZhipuEmbedding:
    """智谱 embedding API 后端（v4.1新增）

    优势：零依赖、零模型下载、API调用
    需要：ZHIPU_API_KEY 环境变量
    """

    def __init__(self):
        self.api_key = os.environ.get("ZHIPU_API_KEY", "")
        self.api_base = "https://open.bigmodel.cn/api/paas/v4/embeddings"
        self.model = "embedding-3"
        self._cache = {}  # 简单缓存避免重复调用

    def is_available(self) -> bool:
        return bool(self.api_key)

    def embed(self, text: str) -> List[float]:
        if not self.is_available():
            return []
        if text in self._cache:
            return self._cache[text]
        try:
            import urllib.request
            payload = json.dumps({"model": self.model, "input": text[:500]}).encode("utf-8")
            req = urllib.request.Request(
                self.api_base, data=payload,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            vec = data.get("data", [{}])[0].get("embedding", [])
            self._cache[text] = vec
            return vec
        except Exception as e:
            logger.debug(f"智谱embedding失败: {e}")
            return []


class VectorMemorySearch:
    """向量记忆检索器（v5.1: ChromaDB持久化 + 智谱embedding + TF-IDF降级）"""

    def __init__(self, memory_dir: Path):
        self.memory_dir = memory_dir
        self.vectorizer = TfidfVectorizer()
        self.embedder = ZhipuEmbedding()
        self._index_cache = None
        self._index_mtime = 0
        self._embed_vectors = None
        # v5.1: ChromaDB持久化向量索引
        self._chroma = None
        self._init_chroma()

    def _init_chroma(self):
        """v5.1: 初始化ChromaDB（有则用，无则降级）"""
        try:
            import chromadb
            chroma_path = self.memory_dir.parent / "chroma_db"
            self._chroma = chromadb.PersistentClient(path=str(chroma_path))
            self._chroma_collection = self._chroma.get_or_create_collection("mingzhu_memories")
            logger.info("ChromaDB持久化向量索引已启用")
        except Exception as e:
            logger.debug(f"ChromaDB不可用，降级TF-IDF: {e}")
            self._chroma = None

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
        """语义检索：返回最相关的记忆条目

        v5.1: 优先ChromaDB持久化索引 → 智谱embedding → TF-IDF降级
        """
        # v5.1: 优先ChromaDB（持久化，无需重建索引）
        if self._chroma is not None:
            results = self._search_with_chroma(query, limit)
            if results:
                return results

        self._build_index()
        if not self._index_cache:
            return []

        # 智谱embedding检索
        if self.embedder.is_available():
            results = self._search_with_embedding(query, limit)
            if results:
                return results

        # TF-IDF检索
        query_vec = self.vectorizer.transform(query)
        if not query_vec:
            return []
        scored = []
        for entry, vec in zip(self._index_cache["entries"], self._index_cache["vectors"]):
            sim = cosine_similarity(query_vec, vec)
            if sim > 0:
                scored.append((sim, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return self._format_results(scored[:limit])

    def _search_with_chroma(self, query: str, limit: int) -> List[Dict]:
        """v5.1: ChromaDB持久化向量检索"""
        try:
            # ChromaDB自带embedding（默认all-MiniLM-L6-v2）
            results = self._chroma_collection.query(
                query_texts=[query],
                n_results=limit,
            )
            if not results.get("documents") or not results["documents"][0]:
                return []
            formatted = []
            ids = results.get("ids", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            documents = results["documents"][0]
            distances = results.get("distances", [[]])[0]
            for i, doc in enumerate(documents):
                meta = metadatas[i] if i < len(metadatas) else {}
                formatted.append({
                    "session_id": meta.get("session_id", ""),
                    "timestamp": meta.get("timestamp", ""),
                    "user_input": meta.get("user_input", "")[:100],
                    "output": doc[:200],
                    "similarity": round(1 - distances[i], 4) if i < len(distances) else 0,
                })
            return formatted
        except Exception as e:
            logger.debug(f"ChromaDB检索失败: {e}")
            return []

    def index_to_chroma(self, session_id: str, user_input: str, output: str, timestamp: str = ""):
        """v5.1: 将新记忆索引到ChromaDB（持久化）"""
        if self._chroma is None:
            return
        try:
            doc_id = f"{session_id}_{timestamp or int(time.time())}"
            self._chroma_collection.upsert(
                ids=[doc_id],
                documents=[output[:500]],
                metadatas=[{
                    "session_id": session_id,
                    "timestamp": timestamp,
                    "user_input": user_input[:200],
                }],
            )
        except Exception as e:
            logger.debug(f"ChromaDB索引失败: {e}")

    def _search_with_embedding(self, query: str, limit: int) -> List[Dict]:
        """用智谱embedding检索"""
        query_vec = self.embedder.embed(query)
        if not query_vec:
            return []
        # 懒构建embedding索引
        if self._embed_vectors is None:
            self._embed_vectors = []
            for e in self._index_cache["entries"]:
                text = e.get("user_input", "") + " " + e.get("output", "")
                self._embed_vectors.append(self.embedder.embed(text[:500]))
        # 计算相似度
        scored = []
        for entry, vec in zip(self._index_cache["entries"], self._embed_vectors):
            if vec:
                sim = cosine_sim_dense(query_vec, vec)
                if sim > 0.3:  # 阈值，过滤不相关
                    scored.append((sim, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return self._format_results(scored[:limit])

    def _format_results(self, scored: List) -> List[Dict]:
        """格式化结果"""
        results = []
        for sim, entry in scored:
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
