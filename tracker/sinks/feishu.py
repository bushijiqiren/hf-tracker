"""飞书 / 钉钉 Sink：自定义机器人 Webhook 发送文本。

配置（config.yaml sinks.feishu）：
    webhook_url: ${FEISHU_WEBHOOK}   群里添加「自定义机器人」拿到的地址

飞书与钉钉自定义机器人的 text 消息体格式一致，同一个 Sink 通用——
把 webhook_url 换成钉钉的地址即可。
"""

from __future__ import annotations

import json
import urllib.request

from ..models import Item
from .base import Sink, register_sink, render_digest


@register_sink("feishu")
class FeishuSink(Sink):
    def __init__(self, webhook_url: str = "", limit: int = 10, **opts):
        super().__init__(limit=limit, **opts)
        self.webhook_url = webhook_url

    def emit(self, source: str, items: list[Item]) -> bool:
        if not self.webhook_url:
            raise RuntimeError("feishu sink 缺少 webhook_url")
        _, body = render_digest(source, items, self.limit)
        payload = json.dumps(
            {"msg_type": "text", "content": {"text": body}}
        ).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
