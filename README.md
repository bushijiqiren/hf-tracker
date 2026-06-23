# hf-tracker

可扩展的新模型 / 项目追踪服务。定时采集 HuggingFace 上的新模型、数据集、Space，
归一化后落盘到固定目录，供 AI 分析、生成报告。架构按插件设计，后续可扩展 GitHub
等数据源，以及 Telegram / 邮件 / 飞书推送和 V2EX / 即刻 / X 报告草稿。

## 数据流

```
数据源(Source) -> 归一化(Item) -> 落盘(data/) -> [评分/过滤] -> [推送/AI报告]
```

- **Source 插件**：`tracker/sources/`，决定"数据从哪来"
- **统一 schema**：`tracker/models.py` 的 `Item`，采集层与下游的稳定契约
- **存储**：`tracker/storage.py`，写 `data/<source>/<日期>/<类型>s.json` 与 `latest.json`

## 当前进度

- ✅ **M1** — 骨架 + HuggingFace 采集 + 归一化 + JSON 落盘
- ✅ **M2** — SQLite 去重/水位线 + 价值评分过滤 + 推送 Sink（console / Telegram / 邮件 / 飞书）
- ⬜ M3 — AI 报告生成（读 `latest_digest.json` → 各平台草稿）+ 推送审核
- ⬜ M4 — GitHub Actions 定时部署 + 数据 commit 回仓

## 工作机制（M2）

- **去重 / 水位线**：`tracker/state.py`，SQLite 存于 `data/_state/seen.sqlite`（不提交）。
  每次只抓上次运行之后的新增，已见过的不重复推送。
- **价值评分**：`tracker/scoring.py`，按 `config.yaml` 的 `scoring` 段打分，
  `score >= threshold` 才推送。新建条目下载/点赞多为 0，关键词命中与新鲜度是主要信号。
- **推送 Sink**：`tracker/sinks/`，`console`（零配置，本地验证用）、`telegram`、`email`、`feishu`。
  在 `config.yaml` 的 `sinks` 下开关；密钥用 `${ENV}` 从环境变量读。

有价值子集会另存到 `data/<source>/latest_digest.json`，供 M3 的 AI 报告聚焦分析。

## 扩展一个推送渠道

继承 `Sink` 实现 `emit(source, items)`，用 `@register_sink("名字")` 注册，
在 `tracker/sinks/__init__.py` 导入，再到 `config.yaml` 的 `sinks` 下开开关。

## 快速开始

需要 Python 3.11+（推荐用 [uv](https://docs.astral.sh/uv/)）。

```bash
cd hf-tracker
uv sync                       # 创建虚拟环境并安装依赖
cp config.example.yaml config.yaml   # 按需修改
uv run hf-tracker run         # 跑一次采集
```

不用 uv 也可以：

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e .
python -m tracker run
```

## 产出目录

```
data/
  huggingface/
    2026-06-23/
      models.json     datasets.json     spaces.json
    latest.json       # AI 固定读这个入口
```

`data/<source>/` 下的 JSON 会提交到 Git 形成历史时间线；`data/_state/` 与密钥不提交。

## 扩展一个新数据源

1. 在 `tracker/sources/` 新建文件，继承 `Source`，实现 `fetch(since)`，用 `@register("名字")` 注册
2. 在 `tracker/sources/__init__.py` 导入它
3. 在 `config.yaml` 的 `sources` 下加 `名字: { enabled: true, ... }`

核心管道与存储无需改动。
