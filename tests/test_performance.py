#!/usr/bin/env python3
"""
明烛性能基准测试 v3.7
测量响应延迟、资源消耗，感知退化。
运行：python tests/test_performance.py
"""
import sys, os, time, json, statistics, tracemalloc
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def benchmark(name, func, runs=3):
    latencies = []
    for _ in range(runs):
        start = time.time()
        try:
            func()
        except Exception as e:
            return {"name": name, "error": str(e)[:50]}
        latencies.append((time.time() - start) * 1000)
    return {"name": name, "runs": runs, "avg_ms": round(statistics.mean(latencies), 1),
            "min_ms": round(min(latencies), 1), "max_ms": round(max(latencies), 1)}


def test_performance():
    print("=" * 60 + "\n明烛性能基准测试 v3.7\n" + "=" * 60 + "\n")
    results = []
    from agent_system import MingZhu
    mz = MingZhu(llm_client=None)
    results.append(benchmark("路由(无LLM)", lambda: mz.route("帮我分析代码")))
    from agent_system.cognitive_cycle import CognitiveCycle
    cycle = CognitiveCycle()
    results.append(benchmark("目标漂移检测", lambda: cycle.detect_goal_drift("测试目标", "测试输出")))
    from agent_system.tools import get_registry
    reg = get_registry()
    results.append(benchmark("calculator工具", lambda: reg.call("calculator", expression="2**10+3*4")))
    from agent_system.vector_search import TfidfVectorizer
    vs = TfidfVectorizer()
    vs.fit_transform(["微服务架构", "单体架构", "JWT认证", "代码审查"] * 10)
    results.append(benchmark("向量检索(40文档)", lambda: vs.transform("微服务")))
    if os.environ.get("ZHIPU_API_KEY"):
        from agent_system.llm_backends import get_router, Scene
        router = get_router()
        results.append(benchmark("智谱LLM调用", lambda: router.generate("回复OK", scene=Scene.SIMPLE, max_tokens=5)))
    tracemalloc.start()
    _ = MingZhu(llm_client=None)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    results.append({"name": "内存占用(峰值)", "value_mb": round(peak / 1024 / 1024, 2)})
    print(f"{'基准项':25s} {'avg':>8s} {'min':>8s} {'max':>8s}")
    print("-" * 55)
    for r in results:
        if "error" in r:
            print(f"{r['name']:25s} ERROR: {r['error']}")
        elif "avg_ms" in r:
            print(f"{r['name']:25s} {r['avg_ms']:>7.1f}ms {r['min_ms']:>7.1f}ms {r['max_ms']:>7.1f}ms")
        else:
            print(f"{r['name']:25s} {r.get('value_mb','?'):>7}MB")
    output = os.path.join(os.path.dirname(__file__), "perf_baseline.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump({"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "results": results}, f, ensure_ascii=False, indent=2)
    print(f"\n基准已保存：{output}")


if __name__ == "__main__":
    test_performance()
