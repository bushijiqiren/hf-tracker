"""核心管道：采集 -> 评分 -> 落盘 -> 去重 -> 过滤 -> 推送。

M3 会在推送前插入 AI 报告生成（读 latest_digest.json 产草稿），同样挂在这条线上。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import load_config
from .scoring import Scorer
from .sinks import build_sinks
from .sources import build_sources
from .state import StateStore
from .storage import JsonStorage


@dataclass
class RunSummary:
    source: str
    fetched: int = 0
    new: int = 0
    valuable: int = 0
    pushed: int = 0
    counts: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def run(config_path: str = "config.yaml") -> list[RunSummary]:
    config = load_config(config_path)
    data_dir = config.get("data_dir", "data")
    storage = JsonStorage(data_dir)
    state = StateStore(Path(data_dir) / "_state" / "seen.sqlite")
    scorer = Scorer(config.get("scoring"))
    sinks = build_sinks(config)
    sources = build_sources(config)

    if not sources:
        print("⚠️  没有启用任何数据源，检查 config.yaml 的 sources.*.enabled")
        return []

    now = datetime.now(timezone.utc)
    summaries: list[RunSummary] = []
    try:
        for source in sources:
            summaries.append(
                _run_source(source, now, state, scorer, sinks, storage)
            )
    finally:
        state.close()
    return summaries


def _run_source(source, now, state, scorer, sinks, storage) -> RunSummary:
    # 1) 增量水位线：上次成功运行之后；首次运行回看 lookback_days 天兜底
    lookback = getattr(source, "lookback_days", 1)
    since = state.get_watermark(source.name) or (now - timedelta(days=lookback))

    # 2) 采集 + 评分（评分写回每条 Item，随快照一起落盘）
    result = source.fetch(since)
    scorer.apply(result.items, now)

    # 3) 全量快照落盘（给 AI 看全貌）
    outcome = storage.write(source.name, result.items, day=now)
    summary = RunSummary(
        source=source.name,
        fetched=len(result.items),
        counts=outcome["counts"],
        errors=list(result.errors),
    )

    # 4) 去重：只保留首次见到的条目作为推送候选（同时记录所有条目）
    new_items = state.filter_new(result.items)
    summary.new = len(new_items)

    # 5) 价值过滤
    valuable = [it for it in new_items if scorer.passes(it)]
    summary.valuable = len(valuable)
    storage.write_digest(source.name, valuable, day=now)

    # 6) 推送（至少一个 sink 成功才记为已推送，避免漏推后无法补推）
    if valuable and sinks:
        any_ok = False
        for sink in sinks:
            try:
                if sink.emit(source.name, valuable):
                    any_ok = True
            except Exception as exc:
                summary.errors.append(f"sink {sink.name}: {exc!r}")
        if any_ok:
            state.mark_pushed(valuable)
            summary.pushed = len(valuable)

    # 7) 更新水位线
    state.set_watermark(source.name, now)

    detail = ", ".join(f"{k}={v}" for k, v in summary.counts.items()) or "无新增"
    print(
        f"✅ {source.name}: 抓 {summary.fetched} [{detail}] | "
        f"新增 {summary.new} | 有价值 {summary.valuable} | 已推 {summary.pushed}"
    )
    for err in summary.errors:
        print(f"   ⚠️  {err}")
    return summary
