#!/usr/bin/env python3
"""
明烛 LangGraph Studio 入口
此文件供 langgraph.json 指向，导出 graph 实例供 Studio 可视化调试。

langgraph.json:
  "graphs": { "mingzhu": "./agent_system/studio_entry.py:graph" }

Studio 会加载这个 graph，在可视化画布显示节点和边，支持：
- 直接输入消息看状态流转
- 修改代码后自动热重载
- 查看每个节点的输入输出
"""
import os
import sys

# 确保能导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_system.langgraph_engine import MingZhuGraph

# 导出 graph 实例供 Studio 使用
# Studio 会读取这个变量，在画布上显示状态图
graph = MingZhuGraph().graph

if __name__ == "__main__":
    # 本地测试
    print("=== 明烛 LangGraph Studio 入口 ===")
    print(f"graph 类型: {type(graph).__name__}")
    print(f"节点数: {len(graph.nodes)}")
    print("可用节点:", list(graph.nodes.keys()))
