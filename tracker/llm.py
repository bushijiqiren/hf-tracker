"""LLM 客户端：默认 DeepSeek（OpenAI 兼容接口）。

provider 通过 config.llm.base_url + model 切换，换成别家 OpenAI 兼容服务只改 config。
配置（config.yaml llm）：
    base_url: https://api.deepseek.com
    model:    deepseek-chat       # 或 deepseek-reasoner（R1，更强推理）
    api_key:  ${DEEPSEEK_API_KEY}
"""

from __future__ import annotations

import os
from collections.abc import Iterator


class LLMClient:
    def __init__(self, config: dict | None = None):
        config = config or {}
        self.model = config.get("model", "deepseek-chat")
        self.temperature = float(config.get("temperature", 0.7))
        api_key = config.get("api_key") or os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "缺少 DeepSeek API key：在环境变量设 DEEPSEEK_API_KEY，"
                "或在 config.yaml 的 llm.api_key 直接填 key"
            )
        if "${" in api_key:
            raise RuntimeError(
                "llm.api_key 仍是未解析的 ${...} 形式。${NAME} 是环境变量引用——"
                "要么直接填 key（api_key: sk-xxx），要么写 api_key: ${DEEPSEEK_API_KEY} "
                "并 export DEEPSEEK_API_KEY=sk-xxx。别把 key 本身放进 ${} 里。"
            )
        from openai import OpenAI

        self.client = OpenAI(
            api_key=api_key,
            base_url=config.get("base_url", "https://api.deepseek.com"),
        )

    def chat(self, messages: list[dict], temperature: float | None = None) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature if temperature is None else temperature,
        )
        return resp.choices[0].message.content or ""

    def stream(self, messages: list[dict], temperature: float | None = None) -> Iterator[str]:
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature if temperature is None else temperature,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
