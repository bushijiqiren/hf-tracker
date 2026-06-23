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
    sub.add_parser("run", help="跑一次采集并落盘")

    args = parser.parse_args(argv)
    command = args.command or "run"

    if command == "run":
        from .pipeline import run

        run(args.config)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
