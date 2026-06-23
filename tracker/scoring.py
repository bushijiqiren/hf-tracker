"""价值评分与过滤。

对每条 Item 打分，下游只推送 score >= threshold 的条目。权重与关键词在
config.yaml 的 scoring 段配置，跑一两周后按实际数据微调。

注意：HuggingFace 上刚新建的条目下载/点赞通常为 0，所以对"新条目"而言，
关键词命中与新鲜度才是主要区分信号——这正符合"只看我关注领域的新东西"。
"""

from __future__ import annotations

from datetime import datetime, timezone
from math import log1p

from .models import Item


class Scorer:
    def __init__(self, config: dict | None = None):
        config = config or {}
        weights = config.get("weights") or {}
        self.w_downloads = float(weights.get("downloads", 1.0))
        self.w_likes = float(weights.get("likes", 1.0))
        self.w_trending = float(weights.get("trending", 2.0))
        self.w_freshness = float(weights.get("freshness", 1.0))
        self.w_keyword = float(weights.get("keyword", 3.0))
        self.threshold = float(config.get("threshold", 0.0))
        self.freshness_hours = float(config.get("freshness_hours", 24))
        self.keywords = [k.lower() for k in (config.get("keywords") or [])]
        # 命中任一 blocklist 词的条目直接排除（公开发布场景下过滤 NSFW 等）
        self.blocklist = [b.lower() for b in (config.get("blocklist") or [])]

    @staticmethod
    def _haystack(item: Item) -> str:
        return " ".join([item.id, " ".join(item.tags), item.summary]).lower()

    def is_blocked(self, item: Item) -> bool:
        if not self.blocklist:
            return False
        hay = self._haystack(item)
        return any(b in hay for b in self.blocklist)

    def score(self, item: Item, now: datetime | None = None) -> float:
        now = now or datetime.now(timezone.utc)
        m = item.metrics
        s = 0.0
        s += self.w_downloads * log1p(m.get("downloads") or 0)
        s += self.w_likes * log1p(m.get("likes") or 0)
        s += self.w_trending * float(m.get("trending_score") or 0)

        # 新鲜度：刚建得 1.0，到 freshness_hours 前线性衰减到 0
        if item.created_at and self.freshness_hours > 0:
            age_h = (now - item.created_at).total_seconds() / 3600
            s += self.w_freshness * max(0.0, 1.0 - age_h / self.freshness_hours)

        # 关键词命中（id / 标签 / 摘要），每命中一个加一份
        if self.keywords:
            hay = self._haystack(item)
            hits = sum(1 for k in self.keywords if k in hay)
            s += self.w_keyword * hits

        return round(s, 4)

    def passes(self, item: Item) -> bool:
        if self.is_blocked(item):
            return False
        return (item.score if item.score is not None else 0.0) >= self.threshold

    def apply(self, items: list[Item], now: datetime | None = None) -> None:
        """就地给每条 Item 写入 score。"""
        now = now or datetime.now(timezone.utc)
        for it in items:
            it.score = self.score(it, now)
