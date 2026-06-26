#!/usr/bin/env python3
"""
明烛 CLI 命令行工具
终端直接和明烛对话，无需网页或AI平台。

用法：
    python cli.py                    # 进入交互模式
    python cli.py "帮我分析代码"      # 单次提问
    python cli.py --session work     # 指定会话ID
    python cli.py --history work     # 查看某会话历史
    python cli.py --sessions         # 列出所有会话
    python cli.py --cost             # 查看成本统计
"""
import sys
import os
import argparse

# 确保能导入 agent_system
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_system.api import (
    chat, chat_with_details, get_history,
    list_sessions, clear_session, cost_summary,
)


def cmd_single(question: str, session_id: str, verbose: bool):
    """单次提问"""
    if verbose:
        result = chat_with_details(question, session_id=session_id)
        print(f"\n{'='*60}")
        print(f"明烛：{result['output']}")
        print(f"{'='*60}")
        print(f"路由：{result['routing_method']} | 人格：{[p['name'] for p in result['personas']]}")
        print(f"模型：{result['models']} | 耗时：{result['latency_ms']}ms")
        if result['conflicts']:
            print(f"冲突：{result['conflicts']}")
        if result['observer']:
            print(f"\n坎观观察：{result['observer'][:300]}")
    else:
        reply = chat(question, session_id=session_id)
        print(reply)


def cmd_interactive(session_id: str):
    """交互模式"""
    print("=" * 60)
    print("  明烛 CLI · 丁火烛照，照亮未知")
    print(f"  会话ID：{session_id}（输入 /help 查看命令，/quit 退出）")
    print("=" * 60)
    print()

    # 加载历史最近一轮作为上下文提示
    history = get_history(session_id)
    if history:
        print(f"  [已恢复 {len(history)} 轮历史记忆]")
        last = history[-1]
        print(f"  上次对话：{last['user_input'][:40]}...")
        print()

    while True:
        try:
            user_input = input("你 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            break

        if not user_input:
            continue

        # 命令
        if user_input == "/quit" or user_input == "/exit":
            print("再见。")
            break
        elif user_input == "/help":
            print("命令：/quit退出 /clear清记忆 /history看历史 /cost看花费 /sessions列会话 /new新会话")
            continue
        elif user_input == "/clear":
            clear_session(session_id)
            print(f"[已清除会话 {session_id} 的记忆]")
            continue
        elif user_input == "/history":
            hist = get_history(session_id)
            for i, h in enumerate(hist, 1):
                print(f"  {i}. [{h['timestamp']}] 你：{h['user_input'][:50]}")
                print(f"     明烛：{h['output'][:50]}...")
            continue
        elif user_input == "/cost":
            print(cost_summary())
            continue
        elif user_input == "/sessions":
            for s in list_sessions():
                print(f"  {s['session_id']}: {s['turns']}轮，最后：{s['last_input']}")
            continue
        elif user_input.startswith("/new "):
            session_id = user_input[5:].strip() or "default"
            print(f"[切换到会话 {session_id}]")
            continue

        # 正常对话
        print("\n明烛 > ", end="", flush=True)
        try:
            result = chat_with_details(user_input, session_id=session_id)
            print(result["output"])
            # 简短元信息
            personas = [p["name"] for p in result["personas"]]
            print(f"\n  [{'+'.join(personas)}] {result['latency_ms']}ms", end="")
            if result["models"]:
                print(f" | {','.join(result['models'])}", end="")
            print("\n")
        except Exception as e:
            print(f"\n[错误] {e}\n")


def main():
    parser = argparse.ArgumentParser(description="明烛 CLI - 数字分身命令行工具")
    parser.add_argument("question", nargs="?", help="单次提问（不填则进入交互模式）")
    parser.add_argument("--session", "-s", default="default", help="会话ID（默认default）")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")
    parser.add_argument("--history", help="查看某会话历史")
    parser.add_argument("--sessions", action="store_true", help="列出所有会话")
    parser.add_argument("--cost", action="store_true", help="查看成本统计")
    args = parser.parse_args()

    if args.sessions:
        for s in list_sessions():
            print(f"  {s['session_id']}: {s['turns']}轮 | 最后：{s['last_input']} | {s['last_time']}")
        return
    if args.cost:
        import json
        print(json.dumps(cost_summary(), ensure_ascii=False, indent=2))
        return
    if args.history:
        hist = get_history(args.history)
        for i, h in enumerate(hist, 1):
            print(f"\n--- 第{i}轮 [{h['timestamp']}] ---")
            print(f"你：{h['user_input']}")
            print(f"明烛：{h['output'][:500]}")
        return

    if args.question:
        cmd_single(args.question, args.session, args.verbose)
    else:
        cmd_interactive(args.session)


if __name__ == "__main__":
    main()
