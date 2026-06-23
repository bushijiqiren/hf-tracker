"""落盘：把归一化后的 Item 写入固定文件目录，供 AI 分析与历史归档。

目录结构（data_dir 默认 ./data）：
    data/<source>/<YYYY-MM-DD>/<type>s.json   当天某源某类型的全部条目
    data/<source>/<YYYY-MM-DD>/raw/...         预留：原始响应留底
    data/<source>/latest.json                  指向该源最新一批，AI 固定读这个入口
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import Item


def _dump(items: list[Item]) -> str:
    payload = [json.loads(it.model_dump_json()) for it in items]
    return json.dumps(payload, ensure_ascii=False, indent=2)


class JsonStorage:
    def __init__(self, data_dir: str | Path = "data"):
        self.data_dir = Path(data_dir)

    def write(self, source: str, items: list[Item], day: datetime | None = None) -> dict:
        """按类型分组写入当天目录，并刷新该源的 latest.json。

        返回写入概况：{type: 条数, ...} 以及生成的文件路径列表。
        """
        day = day or datetime.now(timezone.utc)
        date_str = day.strftime("%Y-%m-%d")
        day_dir = self.data_dir / source / date_str
        day_dir.mkdir(parents=True, exist_ok=True)

        by_type: dict[str, list[Item]] = {}
        for it in items:
            by_type.setdefault(it.type, []).append(it)

        written: dict[str, int] = {}
        files: list[str] = []
        for type_name, group in sorted(by_type.items()):
            path = day_dir / f"{type_name}s.json"
            path.write_text(_dump(group), encoding="utf-8")
            written[type_name] = len(group)
            files.append(str(path))

        latest = {
            "source": source,
            "date": date_str,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "counts": written,
            "items": [json.loads(it.model_dump_json()) for it in items],
        }
        latest_path = self.data_dir / source / "latest.json"
        latest_path.write_text(
            json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        files.append(str(latest_path))

        return {"counts": written, "files": files}
