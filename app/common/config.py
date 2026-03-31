# coding:utf-8
from enum import Enum

from PyQt5.QtCore import QLocale
from PyQt5.QtGui import QColor
from qfluentwidgets import (
    BoolValidator,
    ConfigItem,
    ConfigSerializer,
    EnumSerializer,
    FolderValidator,
    OptionsConfigItem,
    OptionsValidator,
    QConfig,
    RangeConfigItem,
    RangeValidator,
    Theme,
    qconfig,
)

from app.config import NOTES_PATH, SETTINGS_PATH
from app.core.utils.platform_utils import get_available_transcribe_models

from ..core.entities import (
    FasterWhisperModelEnum,
    LLMServiceEnum,
    NoteSceneEnum,
    TranscribeLanguageEnum,
    TranscribeModelEnum,
    TranscribeOutputFormatEnum,
    VadMethodEnum,
    WhisperModelEnum,
)


class Language(Enum):
    CHINESE_SIMPLIFIED = QLocale(QLocale.Chinese, QLocale.China)
    CHINESE_TRADITIONAL = QLocale(QLocale.Chinese, QLocale.HongKong)
    ENGLISH = QLocale(QLocale.English)
    AUTO = QLocale()


class LanguageSerializer(ConfigSerializer):
    def serialize(self, language):
        return language.value.name() if language != Language.AUTO else "Auto"

    def deserialize(self, value: str):
        return Language(QLocale(value)) if value != "Auto" else Language.AUTO


class PlatformAwareTranscribeModelValidator(OptionsValidator):
    """在 macOS 上自动过滤掉 FasterWhisper"""

    def __init__(self):
        self._options = get_available_transcribe_models()

    @property
    def options(self):
        return self._options

    def validate(self, value):
        return value in self._options

    def correct(self, value):
        return value if self.validate(value) else self._options[0]


class Config(QConfig):
    """YuNote 应用配置"""

    # ── LLM 配置 ──────────────────────────────────────────────
    llm_service = OptionsConfigItem(
        "LLM", "LLMService",
        LLMServiceEnum.OPENAI,
        OptionsValidator(LLMServiceEnum),
        EnumSerializer(LLMServiceEnum),
    )
    openai_model = ConfigItem("LLM", "OpenAI_Model", "gpt-4o-mini")
    openai_api_key = ConfigItem("LLM", "OpenAI_API_Key", "")
    openai_api_base = ConfigItem("LLM", "OpenAI_API_Base", "https://api.openai.com/v1")

    silicon_cloud_model = ConfigItem("LLM", "SiliconCloud_Model", "Qwen/Qwen2.5-7B-Instruct")
    silicon_cloud_api_key = ConfigItem("LLM", "SiliconCloud_API_Key", "")
    silicon_cloud_api_base = ConfigItem("LLM", "SiliconCloud_API_Base", "https://api.siliconflow.cn/v1")

    deepseek_model = ConfigItem("LLM", "DeepSeek_Model", "deepseek-chat")
    deepseek_api_key = ConfigItem("LLM", "DeepSeek_API_Key", "")
    deepseek_api_base = ConfigItem("LLM", "DeepSeek_API_Base", "https://api.deepseek.com/v1")

    ollama_model = ConfigItem("LLM", "Ollama_Model", "qwen2.5:7b")
    ollama_api_key = ConfigItem("LLM", "Ollama_API_Key", "ollama")
    ollama_api_base = ConfigItem("LLM", "Ollama_API_Base", "http://localhost:11434/v1")

    lm_studio_model = ConfigItem("LLM", "LmStudio_Model", "qwen2.5:7b")
    lm_studio_api_key = ConfigItem("LLM", "LmStudio_API_Key", "lmstudio")
    lm_studio_api_base = ConfigItem("LLM", "LmStudio_API_Base", "http://localhost:1234/v1")

    gemini_model = ConfigItem("LLM", "Gemini_Model", "gemini-2.0-flash")
    gemini_api_key = ConfigItem("LLM", "Gemini_API_Key", "")
    gemini_api_base = ConfigItem(
        "LLM", "Gemini_API_Base",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    chatglm_model = ConfigItem("LLM", "ChatGLM_Model", "glm-4-flash")
    chatglm_api_key = ConfigItem("LLM", "ChatGLM_API_Key", "")
    chatglm_api_base = ConfigItem("LLM", "ChatGLM_API_Base", "https://open.bigmodel.cn/api/paas/v4")

    # ── 转录配置 ───────────────────────────────────────────────
    transcribe_model = OptionsConfigItem(
        "Transcribe", "TranscribeModel",
        TranscribeModelEnum.BIJIAN,
        PlatformAwareTranscribeModelValidator(),
        EnumSerializer(TranscribeModelEnum),
    )
    transcribe_language = OptionsConfigItem(
        "Transcribe", "TranscribeLanguage",
        TranscribeLanguageEnum.AUTO,
        OptionsValidator(TranscribeLanguageEnum),
        EnumSerializer(TranscribeLanguageEnum),
    )

    # FasterWhisper
    faster_whisper_model = OptionsConfigItem(
        "FasterWhisper", "Model",
        FasterWhisperModelEnum.TINY,
        OptionsValidator(FasterWhisperModelEnum),
        EnumSerializer(FasterWhisperModelEnum),
    )
    faster_whisper_model_dir = ConfigItem("FasterWhisper", "ModelDir", "")
    faster_whisper_device = OptionsConfigItem(
        "FasterWhisper", "Device", "cuda", OptionsValidator(["cuda", "cpu"])
    )
    faster_whisper_vad_filter = ConfigItem("FasterWhisper", "VadFilter", True, BoolValidator())
    faster_whisper_vad_threshold = RangeConfigItem(
        "FasterWhisper", "VadThreshold", 0.4, RangeValidator(0, 1)
    )
    faster_whisper_vad_method = OptionsConfigItem(
        "FasterWhisper", "VadMethod",
        VadMethodEnum.SILERO_V4,
        OptionsValidator(VadMethodEnum),
        EnumSerializer(VadMethodEnum),
    )
    faster_whisper_ff_mdx_kim2 = ConfigItem("FasterWhisper", "FfMdxKim2", False, BoolValidator())
    faster_whisper_one_word = ConfigItem("FasterWhisper", "OneWord", True, BoolValidator())
    faster_whisper_prompt = ConfigItem("FasterWhisper", "Prompt", "")

    # WhisperCpp
    whisper_model = OptionsConfigItem(
        "Whisper", "WhisperModel",
        WhisperModelEnum.TINY,
        OptionsValidator(WhisperModelEnum),
        EnumSerializer(WhisperModelEnum),
    )

    # Whisper API
    whisper_api_base = ConfigItem("WhisperAPI", "WhisperApiBase", "")
    whisper_api_key = ConfigItem("WhisperAPI", "WhisperApiKey", "")
    whisper_api_model = ConfigItem("WhisperAPI", "WhisperApiModel", "whisper-1")
    whisper_api_prompt = ConfigItem("WhisperAPI", "WhisperApiPrompt", "")
    whisper_api_vad_threshold = RangeConfigItem(
        "WhisperAPI", "VadThreshold", 30, RangeValidator(0, 100)
    )
    whisper_api_vad_min_silence_ms = RangeConfigItem(
        "WhisperAPI", "VadMinSilenceMs", 500, RangeValidator(0, 5000)
    )
    whisper_api_vad_speech_pad_ms = RangeConfigItem(
        "WhisperAPI", "VadSpeechPadMs", 600, RangeValidator(0, 2000)
    )

    # ElevenLabs Scribe（无 Key，allow_unauthenticated）
    elevenlabs_model_id = ConfigItem("ElevenLabs", "ModelId", "scribe_v1")
    elevenlabs_diarize = ConfigItem("ElevenLabs", "Diarize", True, BoolValidator())
    elevenlabs_tag_audio_events = ConfigItem(
        "ElevenLabs", "TagAudioEvents", False, BoolValidator()
    )

    # 转录输出格式（供 WhisperAPI / TranscriptionSettingDialog 使用）
    transcribe_output_format = OptionsConfigItem(
        "Transcribe", "OutputFormat",
        TranscribeOutputFormatEnum.TXT,
        OptionsValidator(TranscribeOutputFormatEnum),
        EnumSerializer(TranscribeOutputFormatEnum),
    )
    # 长音频分块 / 并发（对齐 scribe2srt，减轻 API 压力）
    transcribe_enable_async = ConfigItem(
        "Transcribe", "EnableAsyncChunk", True, BoolValidator()
    )
    transcribe_max_concurrent_chunks = RangeConfigItem(
        "Transcribe", "MaxConcurrentChunks", 3, RangeValidator(1, 16)
    )
    transcribe_chunk_max_retries = RangeConfigItem(
        "Transcribe", "ChunkMaxRetries", 3, RangeValidator(1, 10)
    )
    transcribe_api_rate_limit_per_minute = RangeConfigItem(
        "Transcribe", "ApiRateLimitPerMinute", 30, RangeValidator(0, 120)
    )
    # 0 = 不启用「短于该时长则整段转录」；大于 0 时，总时长不超过该分钟数则只发一块
    transcribe_split_threshold_minutes = RangeConfigItem(
        "Transcribe", "SplitThresholdMinutes", 90, RangeValidator(0, 600)
    )
    transcribe_chunk_length_minutes = RangeConfigItem(
        "Transcribe", "ChunkLengthMinutes", 20, RangeValidator(5, 120)
    )

    # ── 总结配置 ───────────────────────────────────────────────
    default_scene = OptionsConfigItem(
        "Summary", "DefaultScene",
        NoteSceneEnum.MEETING,
        OptionsValidator(NoteSceneEnum),
        EnumSerializer(NoteSceneEnum),
    )
    summary_chunk_size = RangeConfigItem(
        "Summary", "ChunkSize", 4000, RangeValidator(1000, 10000)
    )
    # Map 阶段：多片段并行调用 LLM；0 表示不限制 RPM
    summary_map_concurrency = RangeConfigItem(
        "Summary", "MapConcurrency", 3, RangeValidator(1, 16)
    )
    summary_map_rpm = RangeConfigItem(
        "Summary", "MapRpm", 60, RangeValidator(0, 500)
    )
    summary_custom_prompt = ConfigItem("Summary", "CustomPrompt", "")
    summary_prompt_template_meeting = ConfigItem("Summary", "PromptTemplateMeeting", "")
    summary_prompt_template_lecture = ConfigItem("Summary", "PromptTemplateLecture", "")
    summary_prompt_template_interview = ConfigItem("Summary", "PromptTemplateInterview", "")
    summary_prompt_template_general = ConfigItem("Summary", "PromptTemplateGeneral", "")
    auto_summary = ConfigItem("Summary", "AutoSummary", True, BoolValidator())

    # ── 笔记配置 ───────────────────────────────────────────────
    notes_dir = ConfigItem("Notes", "NotesDir", NOTES_PATH, FolderValidator())
    keep_work_files = ConfigItem("Notes", "KeepWorkFiles", False, BoolValidator())

    # ── 界面配置 ───────────────────────────────────────────────
    micaEnabled = ConfigItem("MainWindow", "MicaEnabled", False, BoolValidator())
    dpiScale = OptionsConfigItem(
        "MainWindow", "DpiScale", 1,
        OptionsValidator([1, 1.25, 1.5, 1.75, 2]),
        restart=True,
    )
    language = OptionsConfigItem(
        "MainWindow", "Language",
        Language.AUTO,
        OptionsValidator(Language),
        LanguageSerializer(),
        restart=True,
    )
    checkUpdateAtStartUp = ConfigItem("Update", "CheckUpdateAtStartUp", True, BoolValidator())
    cache_enabled = ConfigItem("Cache", "CacheEnabled", True, BoolValidator())


cfg = Config()
cfg.themeMode.value = Theme.DARK
cfg.themeColor.value = QColor("#ff28f08b")
qconfig.load(SETTINGS_PATH, cfg)
