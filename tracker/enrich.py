"""内容增强：抓取 HuggingFace 条目的 model card(README) 摘录。

新建条目本身只有元数据，没有"它是什么"的描述。把卡片正文取来喂给 LLM，
才能生成有信息量的核心摘要。这一步只对高价值的少量条目做，控制网络与成本。
"""

from __future__ import annotations

import re
from pathlib import Path

from huggingface_hub import hf_hub_download

from .models import Item

# type -> hf_hub_download 的 repo_type
_REPO_TYPE = {"model": "model", "dataset": "dataset", "space": "space"}

_FRONTMATTER = re.compile(r"^---\n.*?\n---\n", re.DOTALL)


def fetch_card(item: Item, max_chars: int = 1500) -> str:
    """取 README.md 正文摘录；取不到返回空串（不报错）。"""
    try:
        path = hf_hub_download(
            repo_id=item.id,
            filename="README.md",
            repo_type=_REPO_TYPE.get(item.type, "model"),
        )
    except Exception:
        return ""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    text = _FRONTMATTER.sub("", text).strip()          # 去掉 YAML 头
    text = re.sub(r"\n{3,}", "\n\n", text)              # 压缩多余空行
    return text[:max_chars]


def enrich(items: list[Item], max_chars: int = 1500) -> list[dict]:
    """给每个条目附上卡片摘录，返回供构建 prompt 的紧凑结构。"""
    out: list[dict] = []
    for it in items:
        out.append(
            {
                "type": it.type,
                "id": it.id,
                "url": it.url,
                "tags": it.tags,
                "score": it.score,
                "metrics": it.metrics,
                "card": fetch_card(it, max_chars),
            }
        )
    return out
