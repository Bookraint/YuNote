# 小宇笔记助手（YuNote）

导入音频或视频 → **语音转录** → **AI 总结**，笔记保存在本地 `AppData/notes/`（每条约含转录文本、总结 Markdown 与元数据）。

## 功能概览

- **转录**：多种引擎可选（如剪映/B 接口、ElevenLabs Scribe、Whisper API、本地 WhisperCpp / FasterWhisper 等），支持长音频分块与并发、限流等设置。
- **总结**：使用 OpenAI 兼容的 LLM 将转录整理为笔记（场景模板、分块大小、Map 并发与 RPM 等可在设置中调整）。
- **笔记**：历史列表、转录原文与总结展示、导出 Markdown / 文本 / Word。

## 环境要求

- **Python** 3.10+（推荐使用 [uv](https://docs.astral.sh/uv/) 管理依赖）
- **ffmpeg**：源文件非可直接识别的 WAV、或带视频轨时需转码（例如 macOS：`brew install ffmpeg`）

## 运行

```bash
uv sync
uv run python main.py
```

首次运行会在 `AppData/` 下生成配置与笔记目录；转录依赖、模型等按所选引擎在应用内或文档说明准备。

## 配置说明

在应用 **设置** 中配置 **LLM**（服务商、Base URL、模型）、**转录引擎**与语言、**总结**相关选项等。无需编辑配置文件即可日常使用。

## 开发

```bash
uv sync
uv run python main.py
uv run pyright
uv run ruff check .
```

## 目录结构（节选）

```
YuNote/
├── app/                 # 应用代码（界面、ASR、总结、笔记等）
├── resource/            # 资源（提示词、翻译等）
├── AppData/             # 运行时数据（设置、笔记、日志、模型缓存等，默认本地）
├── main.py
└── pyproject.toml
```
