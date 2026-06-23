"""AI 简报生成：把高价值条目 + 卡片摘录交给 DeepSeek，产出一份已综述的中文简报。

解决"信息太散"：不是罗列链接，而是先给每条生成一句话核心摘要，再综述、
最后产出 V2EX / 即刻 / Twitter 三个平台的差异化草稿（草稿供你审核后手动发布）。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .enrich import enrich
from .llm import LLMClient
from .models import Item

_SYSTEM = (
    "你是一名中文科技内容编辑，擅长把零散的 AI 模型/项目动态梳理成有信息量、"
    "可读性强的简报。只基于提供的资料，不编造不存在的功能或数据；信息不足时如实说明。"
)

_INSTRUCTION = """下面是今天 HuggingFace 上新增的、经价值过滤的条目（含 model card 摘录）。
请产出一份中文 Markdown 简报，包含以下小节：

## 本期概览
2-4 句话，综述今天值得注意的趋势或亮点（按主题归纳，不要逐条复述）。

## 值得关注
挑选其中最有价值的若干条，每条一行：
- **名称** — 一句话核心摘要（它是什么、有何亮点）。标签/类型可点缀。链接附后。

## 平台草稿
为以下三个平台分别写一版，风格差异化：
### V2EX（长帖，分享向，可分点，克制不浮夸）
### 即刻（中等，口语化，有观点）
### Twitter/X（≤280 字符，精炼，可带 1-2 个话题标签）

资料如下（JSON）：
"""


def _build_context(enriched: list[dict]) -> str:
    compact = []
    for e in enriched:
        compact.append(
            {
                "type": e["type"],
                "name": e["id"],
                "url": e["url"],
                "tags": e["tags"][:8],
                "card": (e["card"][:1200] if e["card"] else ""),
            }
        )
    return json.dumps(compact, ensure_ascii=False, indent=2)


def generate_report(
    config: dict,
    digest_path: str | None = None,
    source: str = "huggingface",
) -> str:
    data_dir = Path(config.get("data_dir", "data"))
    report_cfg = config.get("report") or {}
    top_n = int(report_cfg.get("top_n", 15))
    max_chars = int(report_cfg.get("card_max_chars", 1500))

    path = Path(digest_path) if digest_path else data_dir / source / "latest_digest.json"
    if not path.exists():
        raise FileNotFoundError(f"找不到 digest：{path}（先跑一次 hf-tracker run）")
    digest = json.loads(path.read_text(encoding="utf-8"))

    items = [Item(**raw) for raw in digest.get("items", [])][:top_n]
    if not items:
        raise RuntimeError("digest 里没有有价值的条目，调低 scoring.threshold 再试")

    print(f"📖 抓取 {len(items)} 条的 model card 并综述…")
    enriched = enrich(items, max_chars=max_chars)

    llm = LLMClient(config.get("llm"))
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": _INSTRUCTION + _build_context(enriched)},
    ]
    body = llm.chat(messages)

    date_str = digest.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    header = f"# {source} 简报 · {date_str}\n\n> 由 DeepSeek 基于当日高价值条目生成，发布前请人工核对。\n\n"
    content = header + body

    reports_dir = Path(config.get("reports_dir", "reports"))
    out_dir = reports_dir / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{source}.md"
    out_path.write_text(content, encoding="utf-8")
    (reports_dir / "latest.md").write_text(content, encoding="utf-8")

    print(f"✅ 简报已生成：{out_path}")
    return str(out_path)
