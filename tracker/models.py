"""统一数据 schema。

所有数据源（HuggingFace、后续的 GitHub 等）抓到的内容都归一化成 `Item`。
这是采集层与下游（存储 / 评分 / 推送 / 报告）之间的稳定契约——
下游只认 `Item`，不关心数据来自哪个源。
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Item(BaseModel):
    """归一化后的单条追踪项。"""

    source: str = Field(description='数据源名，如 "huggingface" / "github"')
    type: str = Field(description='条目类型，如 "model" / "dataset" / "space" / "repo"')
    id: str = Field(description="源内唯一 ID，配合 source 全局唯一，用于去重")
    title: str
    url: str
    author: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metrics: dict = Field(default_factory=dict, description="下载量、点赞、stars 等，各源自定")
    tags: list[str] = Field(default_factory=list)
    summary: str = ""
    raw: dict = Field(default_factory=dict, description="原始响应留底，归档用，不丢信息")

    fetched_at: datetime = Field(default_factory=_utcnow)
    score: float | None = Field(default=None, description="价值评分，M2 评分阶段填充")

    @property
    def uid(self) -> str:
        """全局唯一键，去重用。"""
        return f"{self.source}:{self.type}:{self.id}"


class FetchResult(BaseModel):
    """一次数据源抓取的结果。"""

    source: str
    items: list[Item] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=_utcnow)
    errors: list[str] = Field(default_factory=list)
