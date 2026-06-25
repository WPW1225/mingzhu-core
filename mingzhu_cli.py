#!/usr/bin/env python3
"""
明烛 CLI 入口（mingzhu 全局命令）

安装后终端直接用：
    mingzhu                    # 交互模式
    mingzhu "帮我分析代码"       # 直接给任务
    mingzhu chat               # 对话模式（同上）
    mingzhu web                # 启动网页
    mingzhu sessions           # 查看会话
    mingzhu cost               # 查看成本
    mingzhu --help

环境变量：
    ZHIPU_API_KEY    智谱 API key
    DEEPSEEK_API_KEY DeepSeek API key（可选）
"""
import sys
import os

# 确保能导入 agent_system（开发模式 / 安装模式都兼容）
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from agent_system.api import (
    chat, chat_with_details, get_history,
    list_sessions, clear_session, cost_summary, chat_stream,
    search_memory, evolution_metrics,
)


def print_banner():
    print()
    print("  \033[38;5;214m███╗   ███╗██╗███╗   ███╗ █████╗\033[0m")
    print("  \033[38;5;214m████╗ ████║██║████╗ ████║██╔══██╗\033[0m")
    print("  \033[38;5;214m██╔████╔██║██║██╔████╔██║███████║\033[0m")
    print("  \033[38;5;214m██║╚██╔╝██║██║██║╚██╔╝██║██╔══██║\033[0m")
    print("  \033[38;5;214m██║ ╚═╝ ██║██║██║ ╚═╝ ██║██║  ██║\033[0m")
    print("  \033[38;5;214m╚═╝     ╚═╝╚═╝╚═╝     ╚═╝╚═╝  ╚═╝\033[0m")
    print("  \033[38;5;214m丁火烛照 · 照亮未知\033[0m")
    print()


def stream_response(question: str, session_id: str):
    """流式输出响应（像 Claude Code 一样实时显示进度）"""
    print(f"\033[38;5;244m思考中...\033[0m", end="", flush=True)

    # v3.5: 人机协作回调——明烛提问时，用 input() 收集用户回答
    def clarify_cb(q):
        try:
            return input(f"\033[38;5;214m  你的回答›\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            return ""

    for event in chat_stream(question, session_id=session_id, clarify_callback=clarify_cb):
        etype = event["type"]

        if etype == "routing":
            print(f"\r\033[38;5;244m路由: {','.join(event['personas'])}"
                  f" ({event['method']})          \033[0m")

        elif etype == "schedule":
            strat = event.get("strategy", "")
            strat_color = {"parallel": "32", "sequential": "33",
                           "mixed": "36", "iterative": "35"}.get(strat, "33")
            groups = event.get("groups", [])
            groups_str = " → ".join("+".join(g) for g in groups)
            print(f"\033[{strat_color}m  调度: {strat} | {groups_str}\033[0m")
            if event.get("reason"):
                print(f"\033[38;5;244m  理由: {event['reason'][:80]}\033[0m")

        elif etype == "tool":
            print(f"\033[38;5;39m  {event['info']}\033[0m")

        elif etype == "clarify":
            # v3.5: 人机协作——明烛提问，用户回答
            print(f"\n\033[38;5;214m  ❓ 明烛想确认：{event['question']}\033[0m")
            # clarify_callback 会在 chat_stream 内部处理，这里只显示

        elif etype == "persona_start":
            print(f"\033[38;5;214m  {event.get('icon','')} {event['name']} 分析中...\033[0m",
                  end="", flush=True)

        elif etype == "persona_done":
            conf = event.get("confidence", "")
            conf_color = {"高": "32", "中": "33", "低": "31"}.get(conf, "33")
            print(f"\r\033[38;5;214m  {event['name']}\033[0m "
                  f"[\033[{conf_color}m{conf}\033[0m] "
                  f"\033[38;5;244m{event['content'][:80]}...\033[0m")

        elif etype == "synthesizing":
            print(f"\033[38;5;244m  离明汇总中...\033[0m")

        elif etype == "output":
            print()
            print(f"\033[38;5;223m{'='*60}\033[0m")
            print(event["content"])
            print(f"\033[38;5;223m{'='*60}\033[0m")

        elif etype == "observer":
            if event["content"]:
                print(f"\n\033[38;5;61m坎观观察：\033[0m")
                print(f"\033[38;5;61m{event['content'][:400]}\033[0m")

        elif etype == "done":
            print(f"\n\033[38;5;244m[{event['latency_ms']}ms | {','.join(event['models']) or 'N/A'}]\033[0m")


def check_keys():
    """检查 API key 是否配置"""
    zhipu = os.environ.get("ZHIPU_API_KEY", "")
    deepseek = os.environ.get("DEEPSEEK_API_KEY", "")
    if not zhipu and not deepseek:
        print("\033[31m[!] 未检测到 API key，请先配置：\033[0m")
        print("    export ZHIPU_API_KEY='your-key'")
        print("    export DEEPSEEK_API_KEY='your-key'  # 可选")
        print()
        return False
    return True


def cmd_interactive(session_id: str):
    """交互模式（类似 claude code）"""
    if not check_keys():
        return

    print_banner()
    print(f"  \033[90m会话：{session_id} | 输入 /help 查看命令 | /quit 退出\033[0m")
    print("  " + "─" * 50)

    # 加载历史最近一轮
    try:
        hist = get_history(session_id)
        if hist:
            last = hist[-1]
            print(f"  \033[90m[上次对话 {last['timestamp']}]\033[0m")
            print(f"  \033[90m你：{last['user_input'][:60]}\033[0m")
            print(f"  \033[90m明烛：{last['output'][:60]}\033[0m")
            print("  " + "─" * 50)
    except Exception:
        pass

    print()
    while True:
        try:
            user_input = input("\033[38;5;214m你 ›\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  \033[90m明烛在场，随时回来。\033[0m\n")
            break

        if not user_input:
            continue

        # 命令
        if user_input in ("/quit", "/exit", "/q"):
            print("  \033[90m明烛在场，随时回来。\033[0m\n")
            break
        if user_input == "/help":
            print("  \033[90m命令：/help /quit /sessions /cost /clear /new <id> /web\033[0m")
            continue
        if user_input == "/sessions":
            for s in list_sessions():
                print(f"  \033[90m{s['session_id']}: {s['turns']}轮 | {s['last_input'][:40]} | {s['last_time']}\033[0m")
            continue
        if user_input == "/cost":
            c = cost_summary()
            print(f"  \033[90m总调用 {c['total_calls']}次 | ¥{c['total_cost']} | {c['total_tokens']}tokens\033[0m")
            for k, v in c.get("by_backend", {}).items():
                print(f"  \033[90m  {k}: {v['calls']}次 ¥{v['cost']}\033[0m")
            continue
        if user_input == "/clear":
            clear_session(session_id)
            print("  \033[90m已清除当前会话记忆。\033[0m")
            continue
        if user_input.startswith("/new "):
            session_id = user_input[5:].strip()
            print(f"  \033[90m切换到会话：{session_id}\033[0m")
            continue
        if user_input == "/web":
            print("  \033[90m启动网页...（Ctrl+C 退出后回到这里）\033[0m")
            os.system(f"{sys.executable} {os.path.join(_HERE, 'web_app.py')}")
            continue

        # 对话（流式输出）
        try:
            stream_response(user_input, session_id)
        except Exception as e:
            print(f"\033[31m[错误] {e}\033[0m")
        print()


def cmd_single(question: str, session_id: str, verbose: bool):
    """单次任务（流式输出）"""
    if not check_keys():
        return
    # 统一用流式输出，verbose 模式已包含在流式里
    stream_response(question, session_id)


def cmd_web():
    """启动网页"""
    if not check_keys():
        return
    os.system(f"{sys.executable} {os.path.join(_HERE, 'web_app.py')}")


def main():
    args = sys.argv[1:]

    if not args:
        cmd_interactive("default")
        return

    # 子命令
    if args[0] in ("chat", "i", "interactive"):
        sid = args[2] if len(args) > 2 and args[1] == "--session" else "default"
        cmd_interactive(sid)
        return
    if args[0] in ("web", "ui"):
        cmd_web()
        return
    if args[0] in ("sessions", "ls"):
        for s in list_sessions():
            print(f"  {s['session_id']}: {s['turns']}轮 | {s['last_input'][:50]} | {s['last_time']}")
        return
    if args[0] in ("cost", "$"):
        import json
        print(json.dumps(cost_summary(), ensure_ascii=False, indent=2))
        return
    if args[0] in ("search", "find") and len(args) > 1:
        query = " ".join(args[1:])
        results = search_memory(query)
        if not results:
            print(f"  \033[90m未找到含'{query}'的记忆\033[0m")
        else:
            for r in results:
                print(f"  \033[90m[{r['session_id']}] {r['timestamp']}\033[0m")
                print(f"    你：{r['user_input']}")
                print(f"    明烛：{r['output'][:150]}")
                print()
        return
    if args[0] in ("metrics", "evolution"):
        import json
        print(json.dumps(evolution_metrics(), ensure_ascii=False, indent=2))
        return
    if args[0] in ("history", "hist") and len(args) > 1:
        for i, h in enumerate(get_history(args[1]), 1):
            print(f"\n--- 第{i}轮 [{h['timestamp']}] ---")
            print(f"你：{h['user_input']}")
            print(f"明烛：{h['output'][:500]}")
        return

    # 帮助
    if args[0] in ("-h", "--help", "help"):
        print_banner()
        print("用法：")
        print("  mingzhu                    交互模式")
        print("  mingzhu \"任务描述\"          直接给任务")
        print("  mingzhu \"任务\" -v           带详情")
        print("  mingzhu \"任务\" -s work      指定会话")
        print("  mingzhu web                启动网页")
        print("  mingzhu sessions           查看会话")
        print("  mingzhu cost               查看成本")
        print("  mingzhu search <关键词>    跨会话搜索记忆")
        print("  mingzhu metrics            查看进化效果量化")
        print("  mingzhu history <id>       查看会话历史")
        print()
        print("环境变量：")
        print("  ZHIPU_API_KEY              智谱 API key（必需）")
        print("  DEEPSEEK_API_KEY           DeepSeek API key（可选，省钱）")
        return

    # 直接给任务（mingzhu "任务"）
    verbose = "-v" in args or "--verbose" in args
    session_id = "default"
    if "-s" in args:
        idx = args.index("-s")
        if idx + 1 < len(args):
            session_id = args[idx + 1]
    question = " ".join(a for a in args if not a.startswith("-") and a != session_id)
    if question:
        cmd_single(question, session_id, verbose)


if __name__ == "__main__":
    main()
