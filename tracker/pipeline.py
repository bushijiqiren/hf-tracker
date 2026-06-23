"""核心管道：采集 -> 归一化 -> 落盘。

M1 只跑到落盘。后续阶段会在 store 之前插入去重（M2 SQLite）、价值评分（M2），
之后接推送 Sink（M2）与 AI 报告（M3）——都挂在这条管道上，不改动数据源与存储。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .config import load_config
from .sources import build_sources
from .storage import JsonStorage


@dataclass
class RunSummary:
    source: str
    fetched: int = 0
    counts: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def run(config_path: str = "config.yaml") -> list[RunSummary]:
    config = load_config(config_path)
    storage = JsonStorage(config.get("data_dir", "data"))
    sources = build_sources(config)
    if not sources:
        print("⚠️  没有启用任何数据源，检查 config.yaml 的 sources.*.enabled")
        return []

    now = datetime.now(timezone.utc)
    summaries: list[RunSummary] = []
    for source in sources:
        lookback = getattr(source, "lookback_days", 1)
        since = now - timedelta(days=lookback)
        result = source.fetch(since)

        outcome = storage.write(source.name, result.items, day=now)
        summary = RunSummary(
            source=source.name,
            fetched=len(result.items),
            counts=outcome["counts"],
            errors=result.errors,
        )
        summaries.append(summary)

        detail = ", ".join(f"{k}={v}" for k, v in summary.counts.items()) or "无新增"
        print(f"✅ {source.name}: 抓到 {summary.fetched} 条 [{detail}]")
        for err in summary.errors:
            print(f"   ⚠️  {err}")
    return summaries
