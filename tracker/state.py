"""运行时状态：SQLite 去重 + 水位线 + 推送记录。

放在 <data_dir>/_state/seen.sqlite（已 .gitignore，不进版本库）。

职责：
- 去重：判断哪些 uid 是首次见到（push 候选），并记录所有抓到的条目。
- 水位线：记录每个源上次成功运行的时间，下次只抓该时间之后的新增。
- 推送记录：标记哪些条目已推送，避免重复打扰。
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import Item


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class StateStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS seen (
                uid          TEXT PRIMARY KEY,
                source       TEXT NOT NULL,
                type         TEXT NOT NULL,
                item_id      TEXT NOT NULL,
                first_seen   TEXT NOT NULL,
                last_seen    TEXT NOT NULL,
                last_metrics TEXT,
                last_score   REAL,
                pushed_at    TEXT
            );
            CREATE TABLE IF NOT EXISTS watermark (
                source       TEXT PRIMARY KEY,
                last_run_at  TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    # --- 去重 ---------------------------------------------------------------
    def filter_new(self, items: list[Item]) -> list[Item]:
        """记录所有 items；返回其中首次见到的（push 候选）。

        已存在的条目只更新 last_seen / 最新指标 / 最新评分。
        """
        new_items: list[Item] = []
        now = _now_iso()
        for it in items:
            row = self.conn.execute(
                "SELECT uid FROM seen WHERE uid = ?", (it.uid,)
            ).fetchone()
            metrics = json.dumps(it.metrics, ensure_ascii=False)
            if row is None:
                self.conn.execute(
                    "INSERT INTO seen (uid, source, type, item_id, first_seen, "
                    "last_seen, last_metrics, last_score) VALUES (?,?,?,?,?,?,?,?)",
                    (it.uid, it.source, it.type, it.id, now, now, metrics, it.score),
                )
                new_items.append(it)
            else:
                self.conn.execute(
                    "UPDATE seen SET last_seen=?, last_metrics=?, last_score=? WHERE uid=?",
                    (now, metrics, it.score, it.uid),
                )
        self.conn.commit()
        return new_items

    def mark_pushed(self, items: list[Item]) -> None:
        now = _now_iso()
        self.conn.executemany(
            "UPDATE seen SET pushed_at=? WHERE uid=?",
            [(now, it.uid) for it in items],
        )
        self.conn.commit()

    # --- 水位线 -------------------------------------------------------------
    def get_watermark(self, source: str) -> datetime | None:
        row = self.conn.execute(
            "SELECT last_run_at FROM watermark WHERE source = ?", (source,)
        ).fetchone()
        if row is None:
            return None
        return datetime.fromisoformat(row["last_run_at"])

    def set_watermark(self, source: str, when: datetime) -> None:
        self.conn.execute(
            "INSERT INTO watermark (source, last_run_at) VALUES (?, ?) "
            "ON CONFLICT(source) DO UPDATE SET last_run_at=excluded.last_run_at",
            (source, when.isoformat()),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
