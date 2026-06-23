"""命令行入口：`hf-tracker run` 或 `python -m tracker run`。"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hf-tracker", description="新模型/项目追踪服务")
    parser.add_argument(
        "-c", "--config", default="config.yaml", help="配置文件路径（默认 config.yaml）"
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("run", help="跑一次采集、评分、过滤、推送")
    sub.add_parser("report", help="基于当日高价值条目用 DeepSeek 生成简报草稿")
    sub.add_parser("discuss", help="以当日 digest 为上下文，和 AI 多轮讨论（自动保存）")
    sub.add_parser("schedule", help="启动本地定时任务常驻进程")
    p_hist = sub.add_parser("history", help="检索/列出已保存的对话")
    p_hist.add_argument("query", nargs="?", help="检索关键词；省略则列出最近会话")

    args = parser.parse_args(argv)
    command = args.command or "run"

    if command == "run":
        from .pipeline import run

        run(args.config)
        return 0

    if command == "report":
        from .config import load_config
        from .report import generate_report

        generate_report(load_config(args.config))
        return 0

    if command == "discuss":
        from .config import load_config
        from .discuss import run_discuss

        run_discuss(load_config(args.config))
        return 0

    if command == "schedule":
        from .schedule import run_schedule

        run_schedule(args.config)
        return 0

    if command == "history":
        from .config import load_config
        from .conversations import load_index, search

        conv_dir = load_config(args.config).get("conversations_dir", "conversations")
        rows = search(conv_dir, args.query) if args.query else load_index(conv_dir)
        rows = sorted(rows, key=lambda r: r.get("started_at", ""), reverse=True)
        if not rows:
            print("（无匹配会话）" if args.query else "（暂无已保存会话）")
            return 0
        for r in rows[:30]:
            tags = ("  #" + " #".join(r["tags"])) if r.get("tags") else ""
            print(f"{r['date']}  {r['title']}  ({r['message_count']} 轮){tags}")
            print(f"   {r['path']}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
