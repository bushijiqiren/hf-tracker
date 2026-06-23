"""HuggingFace 数据源：抓取最近新建的模型 / 数据集 / Space。

用官方 `huggingface_hub` SDK，按 createdAt 倒序拉取，再用 `since` 水位线过滤出
新条目。后续可在 config 里加 trending、关键词等更多检索策略。
"""

from __future__ import annotations

from datetime import datetime, timezone

from huggingface_hub import HfApi

from ..models import FetchResult, Item
from .base import Source, register

# HF 实体类型 -> (列表方法名, 网页 URL 前缀)
_KINDS = {
    "model": ("list_models", "https://huggingface.co/"),
    "dataset": ("list_datasets", "https://huggingface.co/datasets/"),
    "space": ("list_spaces", "https://huggingface.co/spaces/"),
}


def _as_utc(dt) -> datetime | None:
    if not isinstance(dt, datetime):
        return None
    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@register("huggingface")
class HuggingFaceSource(Source):
    """选项（config.yaml 里 sources.huggingface 下配置）：

    kinds:         要抓的类型列表，默认 ["model", "dataset", "space"]
    lookback_days: 抓取窗口兜底（首次运行 / 无水位线时回看几天），默认 1
    limit_per_kind: 每种类型每次最多拉多少条，默认 200
    """

    def __init__(
        self,
        kinds: list[str] | None = None,
        lookback_days: int = 1,
        limit_per_kind: int = 200,
        **options,
    ):
        super().__init__(**options)
        self.kinds = kinds or ["model", "dataset", "space"]
        self.lookback_days = lookback_days
        self.limit_per_kind = limit_per_kind
        self.api = HfApi()

    def fetch(self, since: datetime) -> FetchResult:
        result = FetchResult(source=self.name)
        for kind in self.kinds:
            try:
                result.items.extend(self._fetch_kind(kind, since))
            except Exception as exc:  # 单个类型失败不拖垮整次抓取
                result.errors.append(f"{kind}: {exc!r}")
        return result

    def _fetch_kind(self, kind: str, since: datetime) -> list[Item]:
        method_name, url_prefix = _KINDS[kind]
        list_fn = getattr(self.api, method_name)
        # sort="created_at" 默认按新建时间倒序（最新在前）；full=True 让返回对象
        # 带上 created_at / downloads / likes / tags 等字段。
        infos = list_fn(
            sort="created_at",
            limit=self.limit_per_kind,
            full=True,
        )

        items: list[Item] = []
        for info in infos:
            created = _as_utc(getattr(info, "created_at", None))
            # 有 createdAt 就按水位线过滤；拿不到时间的保留，交给下游去重。
            if created is not None and created < since:
                break  # 已按 createdAt 倒序，遇到旧的即可停
            items.append(self._to_item(kind, url_prefix, info, created))
        return items

    @staticmethod
    def _to_item(kind: str, url_prefix: str, info, created: datetime | None) -> Item:
        repo_id = getattr(info, "id", "") or ""
        author = getattr(info, "author", "") or (repo_id.split("/")[0] if "/" in repo_id else "")
        metrics = {
            "downloads": getattr(info, "downloads", None),
            "likes": getattr(info, "likes", None),
            "trending_score": getattr(info, "trending_score", None),
        }
        metrics = {k: v for k, v in metrics.items() if v is not None}

        return Item(
            source="huggingface",
            type=kind,
            id=repo_id,
            title=repo_id,
            url=url_prefix + repo_id,
            author=author,
            created_at=created,
            updated_at=_as_utc(getattr(info, "last_modified", None)),
            metrics=metrics,
            tags=list(getattr(info, "tags", None) or []),
            summary=(getattr(info, "pipeline_tag", None) or ""),
        )
