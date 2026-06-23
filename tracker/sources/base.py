"""数据源抽象与注册表。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from ..models import FetchResult

# 名字 -> Source 子类。@register 写入，build_sources 按 config 取用。
_REGISTRY: dict[str, type["Source"]] = {}


def register(name: str):
    """把一个 Source 子类登记到全局注册表。"""

    def _wrap(cls: type["Source"]) -> type["Source"]:
        if name in _REGISTRY:
            raise ValueError(f"数据源名重复注册: {name}")
        cls.name = name
        _REGISTRY[name] = cls
        return cls

    return _wrap


class Source(ABC):
    """所有数据源的基类。

    子类只需实现 `fetch(since)`，返回归一化后的 `FetchResult`。
    `since` 是增量水位线——只需返回该时间点之后新建/有显著更新的条目。
    """

    name: str = "base"

    def __init__(self, **options):
        self.options = options

    @abstractmethod
    def fetch(self, since: datetime) -> FetchResult:
        ...


def build_sources(config: dict) -> list[Source]:
    """按配置实例化已启用的数据源。

    config 形如:
        sources:
          huggingface:
            enabled: true
            lookback_days: 1
            ...
    """
    sources: list[Source] = []
    for name, opts in (config.get("sources") or {}).items():
        opts = opts or {}
        if not opts.get("enabled", False):
            continue
        cls = _REGISTRY.get(name)
        if cls is None:
            raise ValueError(f"未知数据源: {name}（已注册: {sorted(_REGISTRY)}）")
        sources.append(cls(**{k: v for k, v in opts.items() if k != "enabled"}))
    return sources
