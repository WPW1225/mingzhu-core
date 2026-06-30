#!/usr/bin/env python3
"""
明烛模块接入检查 v6.4
防止执行驱动遗留死代码——检查所有模块是否被调用。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_module_usage():
    """检查所有agent_system模块是否被引用"""
    import glob
    issues = []

    modules = []
    for f in glob.glob("agent_system/*.py"):
        name = os.path.basename(f).replace(".py", "")
        if name.startswith("__") or name == "studio_entry":
            continue
        modules.append((name, f))

    for name, f in modules:
        # 搜索其他文件是否import此模块
        count = 0
        for other_f in glob.glob("agent_system/*.py") + glob.glob("tests/*.py") + ["web_app.py", "mingzhu_cli.py"]:
            if other_f == f:
                continue
            try:
                content = open(other_f, encoding="utf-8").read()
                # 检查import语句（不只是文件名出现）
                if f"from .{name} import" in content or f"from agent_system.{name} import" in content or f"import {name}" in content:
                    count += 1
            except Exception:
                pass

        if count == 0:
            issues.append(f"  ❌ {name}: 零import（死代码）")

    return issues


def run_module_check():
    print("=" * 60)
    print("明烛模块接入检查 v6.4")
    print("=" * 60 + "\n")

    issues = check_module_usage()

    if not issues:
        print("✅ 所有模块都被充分引用")
    else:
        print(f"⚠️ 发现 {len(issues)} 个潜在问题:")
        for iss in issues:
            print(iss)

    return issues


if __name__ == "__main__":
    issues = run_module_check()
    sys.exit(1 if issues else 0)
