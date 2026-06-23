"""Console Sink：直接打印到终端，零配置，用于本地验证整条管道。"""

from __future__ import annotations

from ..models import Item
from .base import Sink, register_sink, render_digest


@register_sink("console")
class ConsoleSink(Sink):
    def emit(self, source: str, items: list[Item]) -> bool:
        _, body = render_digest(source, items, self.limit)
        print("\n" + "=" * 60)
        print(body)
        print("=" * 60 + "\n")
        return True
