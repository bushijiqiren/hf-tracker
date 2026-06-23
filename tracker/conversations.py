"""结构化保存人机对话，方便后续 AI 检索。

每个会话存为一个 JSON 文件：conversations/<日期>/<会话id>.json
再维护一个检索索引：conversations/index.jsonl（每行一个会话的元信息 + 标题/摘要）。

AI 检索时：先读 index.jsonl 找相关会话，再打开对应 JSON 看完整对话。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Conversation:
    """一次对话会话。每加一轮就落盘，避免中途崩溃丢记录。"""

    def __init__(self, base_dir: str | Path, source: str, meta: dict | None = None):
        self.base = Path(base_dir)
        started = _now()
        self.date = started.strftime("%Y-%m-%d")
        self.id = started.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
        self.source = source
        self.meta = meta or {}
        self.started_at = started.isoformat()
        self.ended_at: str | None = None
        self.title = ""
        self.summary = ""
        self.tags: list[str] = []
        self.turns: list[dict] = []
        self.path = self.base / self.date / f"{self.id}.json"

    def add(self, role: str, content: str) -> None:
        self.turns.append({"role": role, "content": content, "ts": _now().isoformat()})
        self._flush()

    def _record(self) -> dict:
        return {
            "id": self.id,
            "date": self.date,
            "source": self.source,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "title": self.title,
            "summary": self.summary,
            "tags": self.tags,
            "meta": self.meta,
            "turns": self.turns,
        }

    def _flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._record(), ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def finalize(self, title: str = "", summary: str = "", tags: list[str] | None = None) -> None:
        """会话结束：补标题/摘要/标签，落盘并写入检索索引。"""
        self.ended_at = _now().isoformat()
        self.title = title or (self.turns[0]["content"][:40] if self.turns else "（空会话）")
        self.summary = summary
        self.tags = tags or []
        self._flush()
        self._append_index()

    def _append_index(self) -> None:
        line = {
            "id": self.id,
            "date": self.date,
            "source": self.source,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "title": self.title,
            "summary": self.summary,
            "tags": self.tags,
            "message_count": len(self.turns),
            "path": str(self.path),
        }
        index = self.base / "index.jsonl"
        index.parent.mkdir(parents=True, exist_ok=True)
        with index.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")


def load_index(base_dir: str | Path) -> list[dict]:
    index = Path(base_dir) / "index.jsonl"
    if not index.exists():
        return []
    rows = []
    for line in index.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def search(base_dir: str | Path, query: str) -> list[dict]:
    """在所有会话正文里做大小写无关的子串检索，返回命中的会话元信息。"""
    q = query.lower()
    hits: list[dict] = []
    for row in load_index(base_dir):
        path = Path(row["path"])
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8").lower()
        if q in text:
            hits.append(row)
    return hits
