"""推送 Sink 插件。导入各实现以触发注册。"""

from .base import Sink, build_sinks, register_sink, render_digest
from .console import ConsoleSink
from .email import EmailSink
from .feishu import FeishuSink
from .telegram import TelegramSink

__all__ = [
    "Sink",
    "register_sink",
    "build_sinks",
    "render_digest",
    "ConsoleSink",
    "TelegramSink",
    "EmailSink",
    "FeishuSink",
]
