"""Email Sink：通过 SMTP 发送摘要邮件（stdlib smtplib）。

配置（config.yaml sinks.email）：
    smtp_host / smtp_port      如 smtp.qq.com / 465
    use_ssl: true              465 用 SSL；587 用 STARTTLS 时设 false
    username / password        password 多为「授权码」，放环境变量
    from_addr / to_addrs       发件人 / 收件人列表
"""

from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

from ..models import Item
from .base import Sink, register_sink, render_digest


@register_sink("email")
class EmailSink(Sink):
    def __init__(
        self,
        smtp_host: str = "",
        smtp_port: int = 465,
        use_ssl: bool = True,
        username: str = "",
        password: str = "",
        from_addr: str = "",
        to_addrs: list[str] | None = None,
        limit: int = 20,
        **opts,
    ):
        super().__init__(limit=limit, **opts)
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.use_ssl = use_ssl
        self.username = username
        self.password = password
        self.from_addr = from_addr or username
        self.to_addrs = to_addrs or []

    def emit(self, source: str, items: list[Item]) -> bool:
        if not self.smtp_host or not self.to_addrs:
            raise RuntimeError("email sink 缺少 smtp_host / to_addrs")
        title, body = render_digest(source, items, self.limit)
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = title
        msg["From"] = formataddr(("hf-tracker", self.from_addr))
        msg["To"] = ", ".join(self.to_addrs)

        if self.use_ssl:
            server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=20)
        else:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=20)
            server.starttls()
        try:
            if self.username:
                server.login(self.username, self.password)
            server.sendmail(self.from_addr, self.to_addrs, msg.as_string())
        finally:
            server.quit()
        return True
