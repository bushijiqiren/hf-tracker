"""推送 Sink 抽象、注册表与摘要文本渲染。

新增推送渠道 = 继承 `Sink` 实现 `emit()`，用 `@register_sink("名字")` 注册，
再在 config.yaml 的 sinks 下开开关。与数据源对称。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Item

_SINK_REGISTRY: dict[str, type["Sink"]] = {}


def register_sink(name: str):
    def _wrap(cls: type["Sink"]) -> type["Sink"]:
        if name in _SINK_REGISTRY:
            raise ValueError(f"Sink 名重复注册: {name}")
        cls.name = name
        _SINK_REGISTRY[name] = cls
        return cls

    return _wrap


def render_digest(source: str, items: list[Item], limit: int = 10) -> tuple[str, str]:
    """把有价值的条目渲染成 (标题, 正文) 纯文本摘要。

    按 score 倒序取前 limit 条。各 Sink 可在此基础上套自己的格式。
    """
    ranked = sorted(items, key=lambda i: i.score or 0, reverse=True)
    shown = ranked[:limit]
    title = f"[{source}] 新增 {len(items)} 条有价值更新"

    lines: list[str] = [title, ""]
    for i, it in enumerate(shown, 1):
        bits = []
        if it.metrics.get("likes"):
            bits.append(f"♥{it.metrics['likes']}")
        if it.metrics.get("downloads"):
            bits.append(f"↓{it.metrics['downloads']}")
        if it.summary:
            bits.append(it.summary)
        meta = f"  ({', '.join(bits)})" if bits else ""
        lines.append(f"{i}. [{it.type}] {it.title}  ·  score {it.score}{meta}")
        lines.append(f"   {it.url}")
    if len(items) > limit:
        lines.append("")
        lines.append(f"… 还有 {len(items) - limit} 条，详见 latest_digest.json")
    return title, "\n".join(lines)


class Sink(ABC):
    name: str = "base"

    def __init__(self, limit: int = 10, **options):
        self.limit = limit
        self.options = options

    @abstractmethod
    def emit(self, source: str, items: list[Item]) -> bool:
        """推送一批有价值的条目。返回是否成功。"""
        ...


def build_sinks(config: dict) -> list[Sink]:
    sinks: list[Sink] = []
    for name, opts in (config.get("sinks") or {}).items():
        opts = opts or {}
        if not opts.get("enabled", False):
            continue
        cls = _SINK_REGISTRY.get(name)
        if cls is None:
            raise ValueError(f"未知 Sink: {name}（已注册: {sorted(_SINK_REGISTRY)}）")
        sinks.append(cls(**{k: v for k, v in opts.items() if k != "enabled"}))
    return sinks
