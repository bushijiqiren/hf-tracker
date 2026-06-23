"""配置加载。读取 YAML，并对 ${ENV_VAR} 形式做环境变量展开。"""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _expand(value):
    if isinstance(value, str):
        return _ENV_PATTERN.sub(lambda m: os.environ.get(m.group(1), ""), value)
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


def load_config(path: str | Path = "config.yaml") -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"找不到配置文件: {path}（可从 config.example.yaml 复制）")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return _expand(raw)
