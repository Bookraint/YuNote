# YuNote · 技术架构方案

> **一句话定位**：导入音频 → ASR 转录 → LLM 智能总结 → 结构化笔记管理与导出。面向会议、课程、访谈等场景的 AI 笔记工具。

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术栈](#2-技术栈)
3. [目录结构](#3-目录结构)
4. [核心数据实体](#4-核心数据实体)
5. [核心模块设计](#5-核心模块设计)
6. [数据流](#6-数据流)
7. [配置设计](#7-配置设计)
8. [UI 界面规划](#8-ui-界面规划)
9. [与-SmartVideo-的代码复用说明](#9-与-smartvideo-的代码复用说明)
10. [开发路线图](#10-开发路线图)

---

## 1. 项目概述

### 痛点

开会、听课时信息量大，边听边记容易分心、遗漏；事后回放费时，关键信息难以提取。最常见的应对方式是先录音，再整理——但整理本身依然耗时。

### 解决方案

```
导入音频文件（mp3 / wav / m4a / ...）
          ↓
    ASR 转录（逐字稿）
          ↓
    LLM 智能总结（结构化 Markdown 笔记）
          ↓
    笔记查看 / 编辑 / 导出
```

### 核心功能

| 功能 | 说明 |
|------|------|
| 导入音频 | 支持 mp3 / wav / m4a / aac / ogg / flac，拖拽或文件选择器 |
| ASR 转录 | 多引擎支持：FasterWhisper（本地）/ Whisper API（云端）/ 必剪 ASR |
| 智能总结 | 基于场景（会议 / 课程 / 访谈 / 通用）生成结构化 Markdown 笔记 |
| 笔记管理 | 历史列表、搜索、打标签、全文编辑 |
| 导出 | 导出为 Markdown / TXT / Word（.docx） |

### 独立性原则

**YuNote 是一个完全独立的桌面应用**，有自己的依赖环境、配置文件、数据目录，不依赖 SmartVideo 的任何运行时资源。用户只需安装 YuNote 即可使用全部功能。

---

## 2. 技术栈

| 层次 | 选型 | 说明 |
|------|------|------|
| UI 框架 | PyQt5 + PyQt-Fluent-Widgets | Fluent Design 风格，与 SmartVideo 视觉一致 |
| 音频处理 | `pydub` + `ffmpeg` | 格式检测、转换为 Whisper 所需的 16kHz WAV |
| ASR 转录 | FasterWhisper / Whisper API / 必剪 | 代码从 SmartVideo 复制后独立维护 |
| LLM 客户端 | OpenAI 兼容接口（`openai` SDK） | 支持 OpenAI / DeepSeek / Ollama / Gemini 等 |
| 配置持久化 | `qfluentwidgets.QConfig` + JSON | 独立的 `AppData/settings.json` |
| 笔记存储 | 本地目录 + JSON + Markdown 文件 | 每条笔记一个子目录，用户可直接访问 |
| 导出 | `python-docx`（Word）/ 内置（MD / TXT） | 无需 Office |
| 依赖管理 | `uv` + `pyproject.toml` | 独立的 `.venv`，与 SmartVideo 完全隔离 |
| Python 版本 | `>=3.10, <3.13` | 与 SmartVideo 一致，便于开发 |

---

## 3. 目录结构

```
YuNote/
├── main.py                        # 入口：初始化 Qt / DPI / 日志 / 配置 / 主窗口
├── pyproject.toml                 # 依赖声明与构建配置
├── uv.lock                        # 依赖锁文件
├── README.md
│
├── AppData/                       # 运行期数据（.gitignore）
│   ├── settings.json              # 用户配置持久化（QConfig 写入）
│   ├── notes/                     # 笔记库（每条笔记一个子目录）
│   │   └── {note_id}/
│   │       ├── meta.json          # 元信息：标题、场景、时间、标签、时长、模型等
│   │       ├── transcript.txt     # ASR 转录原文
│   │       └── summary.md         # LLM 生成的结构化总结
│   ├── logs/
│   │   └── llm_requests.jsonl     # LLM 请求日志（JSONL 格式，便于追溯）
│   └── models/                    # 本地 Whisper 模型缓存（FasterWhisper 使用）
│
├── work-dir/                      # 音频预处理中间产物（.gitignore）
│
├── resource/
│   ├── assets/
│   │   ├── logo.png
│   │   └── qss/
│   │       ├── dark/style.qss
│   │       └── light/style.qss
│   ├── prompts/                   # LLM Prompt 模板（Markdown，支持用户自定义）
│   │   ├── summary_meeting.md     # 会议总结
│   │   ├── summary_lecture.md     # 课程笔记
│   │   ├── summary_interview.md   # 访谈记录
│   │   └── summary_general.md     # 通用总结
│   └── translations/
│       └── YuNote_zh_CN.qm
│
└── app/
    ├── config.py                  # 静态路径常量、版本号、APP_NAME
    │
    ├── common/
    │   ├── config.py              # QConfig 子类：所有用户配置项 + cfg 单例
    │   └── signal_bus.py          # 全局 PyQt 信号总线（signalBus 单例）
    │
    ├── core/
    │   ├── entities.py            # 数据实体：Task / Note / Config 等所有 dataclass
    │   ├── task_factory.py        # 任务工厂：根据 cfg 组装 TranscribeTask / SummaryTask
    │   ├── constant.py            # 枚举常量、InfoBar 时长魔法数等
    │   │
    │   ├── asr/                   # 转录模块（代码来源：SmartVideo，独立维护）
    │   │   ├── __init__.py
    │   │   ├── base.py            # BaseASR 抽象基类
    │   │   ├── faster_whisper.py  # 本地 FasterWhisper 引擎
    │   │   ├── whisper_api.py     # 云端 Whisper API 引擎
    │   │   ├── bcut.py            # 必剪 ASR（中文友好）
    │   │   ├── chunked_asr.py     # 长音频分块转录（30min+ 会议必需）
    │   │   └── transcribe.py      # 统一转录入口，按配置选引擎
    │   │
    │   ├── llm/                   # LLM 客户端（代码来源：SmartVideo，独立维护）
    │   │   ├── __init__.py
    │   │   ├── client.py          # OpenAI 兼容 HTTP 客户端，含重试逻辑
    │   │   ├── context.py         # 对话上下文管理
    │   │   └── request_logger.py  # 请求写入 llm_requests.jsonl
    │   │
    │   ├── summary/               # 总结模块（YuNote 核心新增）
    │   │   ├── __init__.py
    │   │   ├── base.py            # BaseSummarizer 抽象基类
    │   │   ├── summarizer.py      # 主逻辑：Map-Reduce 两阶段总结
    │   │   ├── chunker.py         # 长文本分块策略（按句子边界切割）
    │   │   └── post_process.py    # 输出后处理：Markdown 格式标准化
    │   │
    │   ├── notes/                 # 笔记持久化与导出
    │   │   ├── __init__.py
    │   │   ├── note_manager.py    # CRUD：创建、查询、更新、删除笔记
    │   │   └── exporter.py        # 导出：Markdown / TXT / docx
    │   │
    │   └── utils/
    │       ├── logger.py          # 日志初始化（同 SmartVideo 模式）
    │       ├── audio_utils.py     # 音频时长检测、格式转换（→16kHz WAV）
    │       └── platform_utils.py  # 平台差异（可用转录模型过滤等）
    │
    ├── thread/                    # QThread 后台任务（避免阻塞 UI）
    │   ├── transcribe_thread.py   # 转录线程：推送进度信号
    │   ├── summary_thread.py      # 总结线程：推送进度信号
    │   └── version_checker_thread.py
    │
    └── view/                      # UI 界面层
        ├── main_window.py         # FluentWindow 主窗口 + 侧边导航
        ├── home_interface.py      # 首页：音频导入 + 流程配置 + 进度展示
        ├── note_interface.py      # 笔记详情：转录原文 + AI 总结双栏 + 编辑
        ├── history_interface.py   # 历史列表：搜索 / 场景筛选 / 管理
        ├── setting_interface.py   # 设置：LLM / 转录 / 总结 / 笔记 / 界面
        └── llm_logs_interface.py  # LLM 请求日志查看
```

---

## 4. 核心数据实体

```python
# app/core/entities.py

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional


# ──────────────── 枚举 ────────────────

class NoteSceneEnum(Enum):
    """笔记场景：决定使用哪套 Prompt 模板"""
    MEETING   = "会议"
    LECTURE   = "课程"
    INTERVIEW = "访谈"
    GENERAL   = "通用"


class TaskStatusEnum(Enum):
    PENDING  = "等待中"
    RUNNING  = "处理中"
    DONE     = "已完成"
    FAILED   = "失败"


class TranscribeModelEnum(Enum):
    FASTER_WHISPER = "faster_whisper"
    WHISPER_API    = "whisper_api"
    BCUT           = "bcut"


class LLMServiceEnum(Enum):
    OPENAI        = "OpenAI"
    DEEPSEEK      = "DeepSeek"
    SILICON_CLOUD = "SiliconCloud"
    OLLAMA        = "Ollama"
    LM_STUDIO     = "LmStudio"
    GEMINI        = "Gemini"
    CHATGLM       = "ChatGLM"


# ──────────────── 配置对象 ────────────────

@dataclass
class TranscribeConfig:
    transcribe_model: TranscribeModelEnum = TranscribeModelEnum.FASTER_WHISPER
    language: str = "auto"
    # FasterWhisper
    faster_whisper_model: str = "base"
    faster_whisper_device: str = "cuda"
    faster_whisper_vad_filter: bool = True
    faster_whisper_prompt: str = ""
    # Whisper API
    whisper_api_key: str = ""
    whisper_api_base: str = ""
    whisper_api_model: str = ""
    whisper_api_prompt: str = ""


@dataclass
class SummaryConfig:
    scene: NoteSceneEnum = NoteSceneEnum.GENERAL
    llm_service: LLMServiceEnum = LLMServiceEnum.OPENAI
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    custom_prompt: str = ""     # 用户追加指令，拼接在模板末尾
    chunk_size: int = 4000      # 分块字符数（应对超长转录文本）


# ──────────────── 任务对象 ────────────────

@dataclass
class TranscribeTask:
    task_id: str
    queued_at: datetime
    audio_path: str                 # 用户导入的原始音频（或转换后的 WAV）
    output_transcript_path: str     # 转录文本输出路径
    config: TranscribeConfig
    need_next_task: bool = True     # 完成后自动触发总结
    status: TaskStatusEnum = TaskStatusEnum.PENDING


@dataclass
class SummaryTask:
    task_id: str
    queued_at: datetime
    transcript_path: str            # 转录文本输入
    output_summary_path: str        # Markdown 总结输出路径
    config: SummaryConfig
    status: TaskStatusEnum = TaskStatusEnum.PENDING


# ──────────────── 笔记对象 ────────────────

@dataclass
class Note:
    """
    一条笔记的完整元数据。
    持久化到 AppData/notes/{note_id}/meta.json。
    文本内容（转录、总结）存为同目录下的独立文件。
    """
    note_id: str
    title: str
    created_at: datetime
    scene: NoteSceneEnum = NoteSceneEnum.GENERAL
    tags: list[str] = field(default_factory=list)
    transcript_path: Optional[str] = None   # 相对于 AppData/notes/{note_id}/
    summary_path: Optional[str] = None
    source_audio_name: str = ""             # 原始文件名（仅记录，不保存音频）
    duration_seconds: float = 0.0
    transcribe_model: str = ""
    llm_model: str = ""
```

---

## 5. 核心模块设计

### 5.1 音频预处理 `app/core/utils/audio_utils.py`

用户导入的音频格式五花八门，需在转录前统一处理：

```
导入文件
    │
    ├─ 检测格式（pydub / ffprobe）
    ├─ 读取时长（用于 UI 展示和进度预估）
    └─ 若非 16kHz 单声道 WAV
          → pydub 转换 → work-dir/{note_id}/audio.wav
              （Whisper 原生格式，避免转录时二次解码损耗）
```

- 转换后的 WAV 文件存入 `work-dir/`（临时目录），处理完成后可清理，**不占用笔记存储空间**。
- 原始音频文件路径**只记录文件名**（`source_audio_name`），YuNote 不复制或保留用户原始文件。

### 5.2 转录模块 `app/core/asr/`

支持三套引擎，用户在设置页按需选择：

| 引擎 | 优势 | 适用场景 |
|------|------|---------|
| FasterWhisper（本地） | 离线、数据不出境、GPU 加速 | 隐私敏感 / 无网络 |
| Whisper API（云端） | 无需下载模型、即用即走 | 快速体验 |
| 必剪 ASR | 中文识别率高、免费额度 | 中文会议 / 课程 |

**长音频处理**：会议录音通常 30min+，`chunked_asr.py` 将音频切为带重叠的 30s 片段分别转录后按时间戳合并，解决单次请求超时或内存溢出问题。

### 5.3 总结模块 `app/core/summary/`（核心新增）

#### Map-Reduce 两阶段总结

1 小时会议转录约 10,000+ 字，超出多数模型的单次上下文限制。采用两阶段策略：

```
转录原文（可能 10,000+ 字）
        │
        ▼  chunker.py
  按句子边界分块（每块 ~3000-4000 字，块间 200 字重叠保留上下文）
        │
        ▼  阶段一 Map（并发，每块独立请求）
  [块摘要 1]  [块摘要 2]  ...  [块摘要 N]
        │
        ▼  阶段二 Reduce（单次请求，汇总所有块摘要）
  最终结构化总结
        │
        ▼  post_process.py
  Markdown 格式标准化 → summary.md
```

> 若转录文本较短（< chunk_size），直接跳过 Map，单次完成。

#### Prompt 模板设计

模板文件存于 `resource/prompts/`，使用 `{{transcript}}` 占位符注入文本内容：

**`summary_meeting.md`**（会议场景）输出结构：
```markdown
# 会议总结
## 基本信息
- 时间：（从内容推断）
- 主要参与者：（从内容推断）

## 核心议题
## 关键决策
## 待办事项（含负责人）
## 其他要点
```

**`summary_lecture.md`**（课程场景）输出结构：
```markdown
# 课程笔记
## 课程主题
## 核心概念
## 知识点梳理
## 重难点提炼
## 课后思考
```

**`summary_interview.md`**（访谈场景）输出结构：
```markdown
# 访谈记录
## 受访者背景
## 核心观点
## 关键引述
## 延伸问题
```

`custom_prompt` 配置项的内容会拼接在模板末尾，供用户追加个性化要求（如：「请用英文输出」、「额外列出所有数字和数据」）。

### 5.4 笔记管理 `app/core/notes/`

```python
class NoteManager:
    def create_note(title, scene, source_audio_name, duration) -> Note
    def get_note(note_id) -> Note
    def list_notes(scene=None, search_query=None, tags=None) -> list[Note]
    def update_note(note_id, **kwargs) -> Note
    def delete_note(note_id) -> None          # 删除整个 notes/{note_id}/ 目录
    def save_transcript(note_id, text) -> Path
    def save_summary(note_id, markdown) -> Path
    def get_transcript(note_id) -> str
    def get_summary(note_id) -> str
```

**存储结构**：每条笔记是 `AppData/notes/{note_id}/` 下的自包含目录，元数据 JSON + 纯文本文件，用户可直接用任意编辑器打开。

```python
class NoteExporter:
    def to_markdown(note_id, dest_dir) -> Path  # 复制 summary.md
    def to_txt(note_id, dest_dir) -> Path        # 去除 Markdown 标记
    def to_docx(note_id, dest_dir) -> Path       # python-docx 转换，保留标题层级
```

### 5.5 任务工厂 `app/core/task_factory.py`

根据当前 `cfg` 配置快照组装任务对象，与 SmartVideo 相同的工厂模式：

```python
class TaskFactory:

    @staticmethod
    def create_transcribe_task(
        audio_path: str,
        note_id: str,
        need_next_task: bool = True,
    ) -> TranscribeTask:
        """从 cfg 读取转录配置，绑定输出路径到笔记目录"""

    @staticmethod
    def create_summary_task(
        transcript_path: str,
        note_id: str,
        scene: NoteSceneEnum,
    ) -> SummaryTask:
        """从 cfg 读取 LLM 配置，绑定 Prompt 模板路径"""

    @staticmethod
    def create_pipeline(
        audio_path: str,
        scene: NoteSceneEnum,
    ) -> tuple[TranscribeTask, SummaryTask]:
        """创建完整流水线任务对（转录 → 总结）"""
```

---

## 6. 数据流

### 完整流程：音频导入 → 笔记生成

```
用户选择音频文件（拖拽 / 文件选择器）
            │
            ▼
  HomeInterface 展示文件信息（名称、时长、格式）
  用户选择场景 [会议 / 课程 / 访谈 / 通用]
  用户点击「开始处理」
            │
            ▼
  NoteManager.create_note()          ← 立即创建笔记条目（状态：处理中）
  audio_utils.py 格式检测
  若非 16kHz WAV → pydub 转换 → work-dir/{note_id}/audio.wav
            │
            ▼
  TranscribeThread
  ├─ 进度信号 → UI 进度条（0% → 50%）
  ├─ chunked_asr 分块转录
  └─ NoteManager.save_transcript()   → AppData/notes/{note_id}/transcript.txt
            │
            ▼
  SummaryThread
  ├─ 进度信号 → UI 进度条（50% → 100%）
  ├─ chunker 分块
  ├─ Map 阶段（并发 LLM 请求）
  ├─ Reduce 阶段（汇总）
  └─ NoteManager.save_summary()      → AppData/notes/{note_id}/summary.md
            │
            ▼
  NoteManager.update_note(status=DONE)
  work-dir/{note_id}/ 清理（可选）
            │
            ▼
  signalBus.note_ready.emit(note_id)
  UI 自动跳转 NoteInterface 展示结果
```

### 信号流（`signal_bus.py`）

```python
class SignalBus(QObject):
    # 处理进度（0.0 ~ 1.0）
    transcribe_progress = pyqtSignal(str, float)   # (note_id, progress)
    summary_progress    = pyqtSignal(str, float)   # (note_id, progress)

    # 阶段状态文字（显示在进度条下方）
    transcribe_status   = pyqtSignal(str, str)     # (note_id, message)
    summary_status      = pyqtSignal(str, str)     # (note_id, message)

    # 完成 / 失败
    note_ready  = pyqtSignal(str)       # (note_id)
    task_failed = pyqtSignal(str, str)  # (note_id, error_message)
```

---

## 7. 配置设计

`app/common/config.py` 中 `Config(QConfig)` 的完整配置项，持久化到独立的 `AppData/settings.json`：

```python
class Config(QConfig):

    # ── LLM 配置 ──────────────────────────────────────────────
    llm_service = OptionsConfigItem(
        "LLM", "LLMService", LLMServiceEnum.OPENAI,
        OptionsValidator(LLMServiceEnum), EnumSerializer(LLMServiceEnum),
    )
    # OpenAI
    openai_api_key  = ConfigItem("LLM", "OpenAI_API_Key", "")
    openai_api_base = ConfigItem("LLM", "OpenAI_API_Base", "https://api.openai.com/v1")
    openai_model    = ConfigItem("LLM", "OpenAI_Model", "gpt-4o-mini")
    # DeepSeek
    deepseek_api_key  = ConfigItem("LLM", "DeepSeek_API_Key", "")
    deepseek_api_base = ConfigItem("LLM", "DeepSeek_API_Base", "https://api.deepseek.com/v1")
    deepseek_model    = ConfigItem("LLM", "DeepSeek_Model", "deepseek-chat")
    # SiliconCloud / Ollama / LmStudio / Gemini / ChatGLM  （结构同上，各自一组）
    # ...

    # ── 转录配置 ───────────────────────────────────────────────
    transcribe_model = OptionsConfigItem(
        "Transcribe", "TranscribeModel",
        TranscribeModelEnum.FASTER_WHISPER,
        OptionsValidator(TranscribeModelEnum),
        EnumSerializer(TranscribeModelEnum),
    )
    transcribe_language = OptionsConfigItem(
        "Transcribe", "Language", "auto",
        OptionsValidator(["auto", "zh", "en", "ja", "ko", ...]),
    )
    # FasterWhisper
    faster_whisper_model  = OptionsConfigItem("FasterWhisper", "Model", "base", ...)
    faster_whisper_device = OptionsConfigItem("FasterWhisper", "Device", "cuda", ...)
    faster_whisper_vad    = ConfigItem("FasterWhisper", "VadFilter", True, BoolValidator())
    faster_whisper_prompt = ConfigItem("FasterWhisper", "Prompt", "")
    # Whisper API
    whisper_api_key   = ConfigItem("WhisperAPI", "ApiKey", "")
    whisper_api_base  = ConfigItem("WhisperAPI", "ApiBase", "")
    whisper_api_model = ConfigItem("WhisperAPI", "Model", "whisper-1")

    # ── 总结配置（YuNote 新增）────────────────────────────────
    default_scene = OptionsConfigItem(
        "Summary", "DefaultScene",
        NoteSceneEnum.MEETING,
        OptionsValidator(NoteSceneEnum),
        EnumSerializer(NoteSceneEnum),
    )
    summary_chunk_size = RangeConfigItem(
        "Summary", "ChunkSize", 4000, RangeValidator(1000, 10000)
    )
    summary_custom_prompt = ConfigItem("Summary", "CustomPrompt", "")
    auto_summary = ConfigItem("Summary", "AutoSummary", True, BoolValidator())

    # ── 笔记配置（YuNote 新增）────────────────────────────────
    notes_dir  = ConfigItem("Notes", "NotesDir",  NOTES_PATH,  FolderValidator())
    export_dir = ConfigItem("Notes", "ExportDir", EXPORT_PATH, FolderValidator())
    default_export_format = OptionsConfigItem(
        "Notes", "ExportFormat", "markdown",
        OptionsValidator(["markdown", "txt", "docx"]),
    )
    keep_work_files = ConfigItem("Notes", "KeepWorkFiles", False, BoolValidator())

    # ── 界面配置 ───────────────────────────────────────────────
    micaEnabled = ConfigItem("MainWindow", "MicaEnabled", False, BoolValidator())
    dpiScale    = OptionsConfigItem(
        "MainWindow", "DpiScale", "Auto",
        OptionsValidator([1, 1.25, 1.5, 1.75, 2, "Auto"]), restart=True,
    )
    language = OptionsConfigItem(
        "MainWindow", "Language", Language.AUTO,
        OptionsValidator(Language), LanguageSerializer(), restart=True,
    )
    checkUpdateAtStartUp = ConfigItem("Update", "CheckUpdateAtStartUp", True, BoolValidator())
```

---

## 8. UI 界面规划

### 8.1 主窗口导航 `main_window.py`

```
FluentWindow
├── 主页（HomeInterface）          ← 默认落地页
├── 笔记（NoteInterface）          ← 处理完成后自动跳转
├── 历史（HistoryInterface）
├── 请求日志（LLMLogsInterface）
└── 设置（SettingInterface）       ← NavigationItemPosition.BOTTOM
```

### 8.2 主页 `HomeInterface`

```
┌───────────────────────────────────────────────────────┐
│                                                       │
│   ┌─────────────────────────────────────────────┐    │
│   │                                             │    │
│   │     拖拽音频文件到此处，或点击选择            │    │
│   │                                             │    │
│   │         🎵  支持 mp3 / wav / m4a / ...      │    │
│   │                                             │    │
│   └─────────────────────────────────────────────┘    │
│                                                       │
│   已选择：产品周会录音.mp3   时长：45:32               │
│                                                       │
│   场景：  [会议 ▼]                                     │
│                                                       │
│   ────────────────────────────────────────────────   │
│                                                       │
│   [ 开始处理 ]                                         │
│                                                       │
│   ── 处理进度 ─────────────────────────────────────   │
│   转录中（分块 3/8）  [████████░░░░░░░░]   45%        │
│   预计剩余：约 3 分钟                                  │
│                                                       │
└───────────────────────────────────────────────────────┘
```

**状态机**：`空闲` → `预处理（格式转换）` → `转录中` → `总结中` → `完成 / 失败`，每个阶段更新进度条文字和百分比。

### 8.3 笔记详情 `NoteInterface`

```
┌───────────────────────────────────────────────────────┐
│  产品周会 2026-03-25   [场景: 会议]  [编辑标题]  [导出▼]│
│                                                       │
│  ┌─────────────────┐   ┌─────────────────────────┐   │
│  │                 │   │  # 会议总结              │   │
│  │   转录原文       │   │  ## 核心议题             │   │
│  │                 │   │  - Q2 产品规划            │   │
│  │  逐字稿滚动区域  │   │  - 技术债务清理           │   │
│  │  （只读 / 可选  │   │  ## 关键决策             │   │
│  │   开启编辑）    │   │  ...                    │   │
│  │                 │   │                         │   │
│  │                 │   │  [ ✏️ 编辑总结 ]         │   │
│  └─────────────────┘   └─────────────────────────┘   │
│      转录原文（左）           AI 总结（右）              │
│                                                       │
│  来源文件：产品周会录音.mp3   时长：45:32               │
│  转录引擎：FasterWhisper base   LLM：gpt-4o-mini       │
└───────────────────────────────────────────────────────┘
```

### 8.4 历史列表 `HistoryInterface`

```
┌───────────────────────────────────────────────────────┐
│  🔍 搜索笔记...         [全部场景▼]  [会议] [课程] [访谈]│
│                                                       │
│  2026-03-25  📋 产品周会              会议    45min   │
│  2026-03-24  📚 React 高级组件课程    课程    90min   │
│  2026-03-20  🎤 客户访谈-张总         访谈    32min   │
│  2026-03-18  📋 Q1 复盘会议           会议   120min   │
│                                                       │
│  （右键菜单：查看 / 导出 / 删除）                       │
└───────────────────────────────────────────────────────┘
```

### 8.5 设置页 `SettingInterface` 分组

| 分组 | 配置项 |
|------|--------|
| LLM 配置 | 服务商选择（下拉）、API Key、API Base、模型名 |
| 转录配置 | 引擎选择、语言、FasterWhisper 模型/设备/VAD、Whisper API 参数 |
| 总结配置 | 默认场景、分块大小、追加指令 |
| 笔记配置 | 笔记存储目录、导出目录、默认导出格式、是否保留中间文件 |
| 界面配置 | 主题色、DPI 缩放、语言、Mica 效果 |

---

## 9. 与 SmartVideo 的代码复用说明

### 核心原则

**YuNote 是独立 App，与 SmartVideo 没有任何运行时依赖。**

- 各自独立的 `.venv` 虚拟环境
- 各自独立的 `AppData/`（配置、日志、模型缓存）
- 各自独立的 `work-dir/`
- 用户只需安装 YuNote，无需安装 SmartVideo

### 复用方式：一次性代码拷贝

开发启动时，将下列模块从 SmartVideo **手动拷贝**到 YuNote，之后**独立维护**，两个项目不再互相影响：

| 拷贝来源（SmartVideo） | 拷贝目标（YuNote） | 拷贝策略 |
|---|---|---|
| `app/core/asr/` | `app/core/asr/` | 完整拷贝 |
| `app/core/llm/` | `app/core/llm/` | 完整拷贝 |
| `app/core/utils/logger.py` | `app/core/utils/logger.py` | 完整拷贝 |
| `app/core/utils/platform_utils.py` | `app/core/utils/platform_utils.py` | 按需裁剪 |
| `app/common/signal_bus.py` | `app/common/signal_bus.py` | 重写（信号不同） |
| `app/config.py` | `app/config.py` | 重写（路径/名称不同） |
| `app/common/config.py` | `app/common/config.py` | 重写（配置项不同） |
| `app/view/llm_logs_interface.py` | `app/view/llm_logs_interface.py` | 完整拷贝 |
| `main.py` | `main.py` | 参照改写 |

### 架构模式复用（思路沿用）

从 SmartVideo 继承的架构决策，在 YuNote 中保持一致：

| 模式 | 说明 |
|------|------|
| `TaskFactory` 组装任务 | 与 UI / 线程解耦，`cfg` 配置快照在工厂内一次性读取 |
| `QThread` + `pyqtSignal` 进度推送 | 转录、总结全部后台运行，不阻塞 UI |
| `QConfig` 配置持久化 | 统一用 `qconfig.load` / 自动保存，不手写 JSON |
| `SignalBus` 全局信号总线 | 跨界面通信不传递 parent 引用 |
| `FluentWindow` 侧边导航 | 相同的窗口结构和导航模式 |
| `InfoBar` 操作反馈 | 成功 / 警告 / 错误统一用 InfoBar，不用 QMessageBox |
| JSONL 格式 LLM 日志 | `llm_requests.jsonl` 格式与 SmartVideo 一致，界面可直接复用 |

---

## 10. 开发路线图

### Phase 1：MVP（核心流程跑通）

- [ ] 项目初始化：目录结构、`pyproject.toml`、`main.py`
- [ ] `app/config.py` + `app/common/config.py`（基础配置项）
- [ ] 从 SmartVideo 拷贝 `asr/` 和 `llm/` 模块并适配
- [ ] `app/core/utils/audio_utils.py`（格式检测 + pydub 转换）
- [ ] `app/core/summary/`（Map-Reduce 总结逻辑 + 4 套 Prompt 模板）
- [ ] `app/core/notes/note_manager.py`（笔记 CRUD）
- [ ] `app/core/task_factory.py`
- [ ] `app/thread/transcribe_thread.py` + `summary_thread.py`
- [ ] 主页 UI（导入 + 进度展示）
- [ ] 笔记详情 UI（转录 + 总结双栏）
- [ ] `FluentWindow` 主窗口 + 基础导航

### Phase 2：完整功能

- [ ] 历史列表 `HistoryInterface`（搜索、场景筛选、删除）
- [ ] 导出功能（Markdown / TXT / docx）
- [ ] 完整设置页（LLM / 转录 / 总结 / 笔记）
- [ ] LLM 请求日志页（从 SmartVideo 拷贝改写）
- [ ] 笔记标签管理
- [ ] 拖拽导入支持

### Phase 3：体验打磨

- [ ] 笔记总结支持重新生成（更换场景 / Prompt）
- [ ] 批量导入多个音频文件
- [ ] 国际化（中 / 英）
- [ ] 打包发布（PyInstaller，含 FasterWhisper 可执行文件）

---

## 附录：依赖清单（`pyproject.toml` 草稿）

```toml
[project]
name = "yunote"
version = "0.1.0"
description = "AI-powered meeting and lecture notes tool"
authors = [{ name = "" }]
requires-python = ">=3.10,<3.13"

dependencies = [
    # UI
    "PyQt5==5.15.11",
    "PyQt-Fluent-Widgets==1.8.4",
    # 音频处理（格式转换，不含录音）
    "pydub>=0.25.1",
    # LLM
    "openai>=1.0.0",
    "tenacity>=8.2.0",
    "httpx[socks]>=0.28.1",
    # ASR 相关
    "requests>=2.32.0",
    # 笔记导出
    "python-docx>=1.1.2",
    # 工具
    "psutil>=7.0.0",
    "json-repair>=0.49.0",
    "langdetect>=1.0.9",
]

[tool.uv]
environments = [
    "sys_platform == 'win32'",
    "sys_platform == 'darwin'",
    "sys_platform == 'linux'",
]
override-dependencies = [
    "PyQt5-Qt5==5.15.2; sys_platform == 'win32'",
    "PyQt5-Qt5>=5.15.11; sys_platform != 'win32'",
]
dev-dependencies = [
    "pyright>=1.1.0",
    "ruff>=0.4.0",
    "pytest>=8.0.0",
]
```

> **注**：FasterWhisper 通过预编译的独立可执行文件（`faster-whisper-xxl.exe`）调用，不作为 Python 包依赖，打包时随资源一起分发，与 SmartVideo 做法一致。
