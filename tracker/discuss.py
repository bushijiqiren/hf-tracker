"""人 + AI 多轮讨论：以当日 digest 为上下文，和 DeepSeek 就这些新内容对话。

用法：hf-tracker discuss
可以追问某条是什么、横向对比、让它挑选最值得试的、深挖某个方向等。
输入 exit / quit / :q 结束。
"""

from __future__ import annotations

import json
from pathlib import Path

from .llm import LLMClient
from .models import Item

_SYSTEM = (
    "你是用户的 AI 助手，正在和用户讨论今天 HuggingFace 上新增的模型/数据集/Space。"
    "下面 JSON 是经价值过滤的当日条目（含名称、类型、标签、链接、评分）。"
    "回答时基于这些资料，可结合你的知识做解读、对比、推荐；不确定就说不确定，不要编造。"
    "回答用中文，简洁有条理。\n\n当日条目：\n"
)


def _context(config: dict, source: str, limit: int) -> str:
    data_dir = Path(config.get("data_dir", "data"))
    path = data_dir / source / "latest_digest.json"
    if not path.exists():
        raise FileNotFoundError(f"找不到 digest：{path}（先跑一次 hf-tracker run）")
    digest = json.loads(path.read_text(encoding="utf-8"))
    items = [Item(**raw) for raw in digest.get("items", [])][:limit]
    compact = [
        {
            "type": it.type,
            "name": it.id,
            "url": it.url,
            "tags": it.tags[:8],
            "score": it.score,
        }
        for it in items
    ]
    return f"（日期 {digest.get('date')}，共 {len(items)} 条）\n" + json.dumps(
        compact, ensure_ascii=False
    )


def run_discuss(config: dict, source: str = "huggingface") -> None:
    discuss_cfg = config.get("discuss") or {}
    limit = int(discuss_cfg.get("context_items", 40))

    llm = LLMClient(config.get("llm"))
    messages = [{"role": "system", "content": _SYSTEM + _context(config, source, limit)}]

    print("💬 与 AI 讨论今日更新（输入 exit / quit / :q 结束）")
    print(f"   已载入 {source} 当日 digest 作为上下文。可以先问：'今天有什么值得关注的？'\n")

    while True:
        try:
            user_input = input("你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", ":q"}:
            break

        messages.append({"role": "user", "content": user_input})
        print("AI> ", end="", flush=True)
        reply_parts: list[str] = []
        for delta in llm.stream(messages):
            print(delta, end="", flush=True)
            reply_parts.append(delta)
        print("\n")
        messages.append({"role": "assistant", "content": "".join(reply_parts)})
