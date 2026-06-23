"""本地定时任务：常驻进程，按每日时间点或固定间隔自动跑采集（可选接简报）。

配置（config.yaml schedule）：
    times: ["09:00", "21:00"]   # 每天这些时间点跑（本地时区，优先）
    # interval_minutes: 360     # 或：每隔多少分钟跑一次（与 times 二选一）
    run_report: false           # 每次跑完 run 后是否接着生成简报
    run_at_start: true          # 启动时先立刻跑一次

云端定时建议用 GitHub Actions（见 .github/workflows/track.yml），cron 触发 `hf-tracker run`。
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta

from .config import load_config


def _next_run(times: list[str], now: datetime) -> datetime:
    candidates = []
    for t in times:
        hh, mm = (int(x) for x in t.split(":"))
        dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if dt <= now:
            dt += timedelta(days=1)
        candidates.append(dt)
    return min(candidates)


def _sleep_until(target: datetime) -> None:
    print(f"⏰ 下次运行：{target:%Y-%m-%d %H:%M}（Ctrl-C 退出）")
    while True:
        remaining = (target - datetime.now()).total_seconds()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 30))  # 分段睡，保证 Ctrl-C 及时响应


def _cycle(config_path: str, run_report: bool) -> None:
    from .pipeline import run

    print(f"\n▶️  {datetime.now():%Y-%m-%d %H:%M:%S} 开始采集")
    run(config_path)
    if run_report:
        try:
            from .report import generate_report

            generate_report(load_config(config_path))
        except Exception as exc:
            print(f"   ⚠️  简报生成失败：{exc!r}")


def run_schedule(config_path: str = "config.yaml") -> None:
    sched = load_config(config_path).get("schedule") or {}
    times = sched.get("times") or []
    interval = sched.get("interval_minutes")
    run_report = bool(sched.get("run_report", False))

    if not times and not interval:
        raise RuntimeError("schedule 需配置 times 或 interval_minutes（见 config.example.yaml）")

    mode = f"每天 {', '.join(times)}" if times else f"每 {interval} 分钟"
    print(f"🗓️  定时任务启动：{mode}" + ("，跑完生成简报" if run_report else ""))

    if sched.get("run_at_start", True):
        _cycle(config_path, run_report)

    try:
        while True:
            if times:
                _sleep_until(_next_run(times, datetime.now()))
            else:
                _sleep_until(datetime.now() + timedelta(minutes=interval))
            _cycle(config_path, run_report)
    except KeyboardInterrupt:
        print("\n👋 定时任务已停止")
