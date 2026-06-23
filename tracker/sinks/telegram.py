"""Telegram Sink：通过 Bot API 发送摘要。

配置（config.yaml sinks.telegram）：
    bot_token: ${TELEGRAM_BOT_TOKEN}   找 @BotFather 创建 bot 拿到
    chat_id:   ${TELEGRAM_CHAT_ID}     你与 bot 的会话 id（或群 id）
"""

from __future__ import annotations

import json
import urllib.request

from ..models import Item
from .base import Sink, register_sink, render_digest


@register_sink("telegram")
class TelegramSink(Sink):
    def __init__(self, bot_token: str = "", chat_id: str = "", limit: int = 10, **opts):
        super().__init__(limit=limit, **opts)
        self.bot_token = bot_token
        self.chat_id = chat_id

    def emit(self, source: str, items: list[Item]) -> bool:
        if not self.bot_token or not self.chat_id:
            raise RuntimeError("telegram sink 缺少 bot_token / chat_id")
        _, body = render_digest(source, items, self.limit)
        payload = json.dumps(
            {"chat_id": self.chat_id, "text": body, "disable_web_page_preview": True}
        ).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
