"""数据源插件。

新增一个数据源 = 继承 `Source` 实现 `fetch()`，并用 `@register` 注册名字，
再在 config.yaml 的 sources 里打开开关即可。核心管道无需改动。
"""

from .base import Source, build_sources, register
from .huggingface import HuggingFaceSource

__all__ = ["Source", "register", "build_sources", "HuggingFaceSource"]
