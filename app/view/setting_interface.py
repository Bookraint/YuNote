"""
设置页：LLM / 转录 / 总结 / 笔记 / 界面
"""
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QFileDialog, QWidget
from qfluentwidgets import (
    BoolValidator,
    ComboBoxSettingCard,
    ExpandLayout,
    InfoBar,
    InfoBarPosition,
    OptionsSettingCard,
    PrimaryPushSettingCard,
    PushSettingCard,
    RangeSettingCard,
    ScrollArea,
    SettingCardGroup,
    SwitchSettingCard,
    setTheme,
    setThemeColor,
    FluentIcon as FIF,
)

from app.common.config import cfg
from app.components.EditComboBoxSettingCard import EditComboBoxSettingCard
from app.components.LineEditSettingCard import LineEditSettingCard
from app.config import APPDATA_PATH, VERSION
from app.core.entities import LLMServiceEnum
from app.core.llm.check_llm import check_llm_connection, get_available_models


class LLMCheckThread(QThread):
    result = pyqtSignal(bool, str)

    def __init__(self, base_url, api_key, model):
        super().__init__()
        self._base_url = base_url
        self._api_key = api_key
        self._model = model

    def run(self):
        ok, msg = check_llm_connection(self._base_url, self._api_key, self._model)
        self.result.emit(ok, msg)


class SettingInterface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingInterface")
        self.setWindowTitle("设置")

        self._scroll_widget = QWidget()
        self._expand_layout = ExpandLayout(self._scroll_widget)
        self._expand_layout.setContentsMargins(36, 10, 36, 0)

        self._init_llm_group()
        self._init_transcribe_group()
        self._init_summary_group()
        self._init_notes_group()
        self._init_ui_group()

        self.setWidget(self._scroll_widget)
        self.setWidgetResizable(True)
        self.enableTransparentBackground()

        self._llm_check_thread: LLMCheckThread | None = None

    # ── LLM 配置 ──────────────────────────────────────────────

    def _init_llm_group(self):
        group = SettingCardGroup("LLM 大模型", self._scroll_widget)

        self._llm_service_card = ComboBoxSettingCard(
            cfg.llm_service,
            FIF.ROBOT,
            "服务商",
            "选择 LLM API 服务商",
            texts=[s.value for s in LLMServiceEnum],
            parent=group,
        )
        group.addSettingCard(self._llm_service_card)

        # OpenAI
        self._openai_key_card = LineEditSettingCard(
            cfg.openai_api_key, FIF.CERTIFICATE, "OpenAI API Key", "", group
        )
        self._openai_base_card = EditComboBoxSettingCard(
            cfg.openai_api_base, FIF.LINK, "OpenAI API Base", "",
            ["https://api.openai.com/v1"], group
        )
        self._openai_model_card = EditComboBoxSettingCard(
            cfg.openai_model, FIF.LABEL, "OpenAI 模型", "",
            ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"], group
        )
        group.addSettingCard(self._openai_key_card)
        group.addSettingCard(self._openai_base_card)
        group.addSettingCard(self._openai_model_card)

        # DeepSeek
        self._deepseek_key_card = LineEditSettingCard(
            cfg.deepseek_api_key, FIF.CERTIFICATE, "DeepSeek API Key", "", group
        )
        self._deepseek_model_card = EditComboBoxSettingCard(
            cfg.deepseek_model, FIF.LABEL, "DeepSeek 模型", "",
            ["deepseek-chat", "deepseek-reasoner"], group
        )
        group.addSettingCard(self._deepseek_key_card)
        group.addSettingCard(self._deepseek_model_card)

        # SiliconCloud
        self._sc_key_card = LineEditSettingCard(
            cfg.silicon_cloud_api_key, FIF.CERTIFICATE, "SiliconCloud API Key", "", group
        )
        self._sc_model_card = EditComboBoxSettingCard(
            cfg.silicon_cloud_model, FIF.LABEL, "SiliconCloud 模型", "",
            ["Qwen/Qwen2.5-7B-Instruct", "Qwen/Qwen2.5-72B-Instruct",
             "deepseek-ai/DeepSeek-V3"], group
        )
        group.addSettingCard(self._sc_key_card)
        group.addSettingCard(self._sc_model_card)

        # Ollama
        self._ollama_base_card = EditComboBoxSettingCard(
            cfg.ollama_api_base, FIF.LINK, "Ollama API Base", "",
            ["http://localhost:11434/v1"], group
        )
        self._ollama_model_card = EditComboBoxSettingCard(
            cfg.ollama_model, FIF.LABEL, "Ollama 模型", "",
            ["qwen2.5:7b", "llama3.1:8b", "mistral:7b"], group
        )
        group.addSettingCard(self._ollama_base_card)
        group.addSettingCard(self._ollama_model_card)

        # Gemini
        self._gemini_key_card = LineEditSettingCard(
            cfg.gemini_api_key, FIF.CERTIFICATE, "Gemini API Key", "", group
        )
        self._gemini_model_card = EditComboBoxSettingCard(
            cfg.gemini_model, FIF.LABEL, "Gemini 模型", "",
            ["gemini-2.0-flash", "gemini-1.5-pro"], group
        )
        group.addSettingCard(self._gemini_key_card)
        group.addSettingCard(self._gemini_model_card)

        # 测试连接
        self._test_llm_card = PrimaryPushSettingCard(
            "测试连接", FIF.WIFI, "测试 LLM 连接", "验证当前服务商配置是否可用",
            parent=group
        )
        self._test_llm_card.clicked.connect(self._test_llm)
        group.addSettingCard(self._test_llm_card)

        self._expand_layout.addWidget(group)

    # ── 转录配置 ──────────────────────────────────────────────

    def _init_transcribe_group(self):
        from app.components.FasterWhisperSettingWidget import FasterWhisperSettingWidget
        from app.components.WhisperAPISettingWidget import WhisperAPISettingWidget

        group = SettingCardGroup("转录引擎", self._scroll_widget)

        self._transcribe_model_card = ComboBoxSettingCard(
            cfg.transcribe_model,
            FIF.MICROPHONE,
            "转录引擎",
            "选择语音转录引擎",
            texts=[m.value for m in cfg.transcribe_model.options],
            parent=group,
        )
        group.addSettingCard(self._transcribe_model_card)

        self._transcribe_lang_card = ComboBoxSettingCard(
            cfg.transcribe_language,
            FIF.LANGUAGE,
            "转录语言",
            "音频内容的语言（自动检测可能不准确时手动指定）",
            texts=[l.value for l in cfg.transcribe_language.options],
            parent=group,
        )
        group.addSettingCard(self._transcribe_lang_card)

        self._faster_whisper_widget = FasterWhisperSettingWidget(group)
        group.addSettingCard(self._faster_whisper_widget)

        self._whisper_api_widget = WhisperAPISettingWidget(group)
        group.addSettingCard(self._whisper_api_widget)

        self._expand_layout.addWidget(group)

    # ── 总结配置 ──────────────────────────────────────────────

    def _init_summary_group(self):
        group = SettingCardGroup("AI 总结", self._scroll_widget)

        self._default_scene_card = ComboBoxSettingCard(
            cfg.default_scene,
            FIF.DOCUMENT,
            "默认场景",
            "新建笔记时预选的总结场景",
            texts=[s.value for s in cfg.default_scene.options],
            parent=group,
        )
        group.addSettingCard(self._default_scene_card)

        self._auto_summary_card = SwitchSettingCard(
            FIF.ROBOT,
            "自动总结",
            "转录完成后自动调用 LLM 生成总结",
            cfg.auto_summary,
            group,
        )
        group.addSettingCard(self._auto_summary_card)

        self._chunk_size_card = RangeSettingCard(
            cfg.summary_chunk_size,
            FIF.LAYOUT,
            "分块大小",
            "长文本分块处理时每块的最大字符数",
            group,
        )
        group.addSettingCard(self._chunk_size_card)

        self._custom_prompt_card = LineEditSettingCard(
            cfg.summary_custom_prompt,
            FIF.EDIT,
            "追加指令",
            "附加在 Prompt 末尾的自定义要求（留空则不追加）",
            group,
        )
        group.addSettingCard(self._custom_prompt_card)

        self._expand_layout.addWidget(group)

    # ── 笔记配置 ──────────────────────────────────────────────

    def _init_notes_group(self):
        group = SettingCardGroup("笔记存储", self._scroll_widget)

        self._notes_dir_card = PushSettingCard(
            "选择目录",
            FIF.FOLDER,
            "笔记存储目录",
            str(cfg.notes_dir.value),
            group,
        )
        self._notes_dir_card.clicked.connect(self._choose_notes_dir)
        group.addSettingCard(self._notes_dir_card)

        self._export_dir_card = PushSettingCard(
            "选择目录",
            FIF.FOLDER,
            "导出目录",
            str(cfg.export_dir.value),
            group,
        )
        self._export_dir_card.clicked.connect(self._choose_export_dir)
        group.addSettingCard(self._export_dir_card)

        self._export_fmt_card = ComboBoxSettingCard(
            cfg.default_export_format,
            FIF.DOCUMENT,
            "默认导出格式",
            "",
            texts=["markdown", "txt", "docx"],
            parent=group,
        )
        group.addSettingCard(self._export_fmt_card)

        self._keep_work_card = SwitchSettingCard(
            FIF.SAVE,
            "保留中间文件",
            "保留处理过程中生成的临时 WAV 文件",
            cfg.keep_work_files,
            group,
        )
        group.addSettingCard(self._keep_work_card)

        self._expand_layout.addWidget(group)

    # ── 界面配置 ──────────────────────────────────────────────

    def _init_ui_group(self):
        group = SettingCardGroup("界面", self._scroll_widget)

        self._mica_card = SwitchSettingCard(
            FIF.TRANSPARENT,
            "Mica 效果",
            "窗口背景启用云母半透明效果（仅 Windows 11）",
            cfg.micaEnabled,
            group,
        )
        self._mica_card.checkedChanged.connect(
            lambda checked: self.window().setMicaEffectEnabled(checked)
        )
        group.addSettingCard(self._mica_card)

        self._dpi_card = ComboBoxSettingCard(
            cfg.dpiScale,
            FIF.ZOOM,
            "缩放比例",
            "修改后重启生效",
            texts=["1x", "1.25x", "1.5x", "1.75x", "2x", "Auto"],
            parent=group,
        )
        group.addSettingCard(self._dpi_card)

        self._version_card = PushSettingCard(
            "",
            FIF.INFO,
            f"版本  {VERSION}",
            "小宇笔记助手 YuNote",
            group,
        )
        group.addSettingCard(self._version_card)

        self._expand_layout.addWidget(group)

    # ── 事件处理 ──────────────────────────────────────────────

    def _test_llm(self):
        svc = cfg.llm_service.value
        if svc == LLMServiceEnum.OPENAI:
            base, key, model = cfg.openai_api_base.value, cfg.openai_api_key.value, cfg.openai_model.value
        elif svc == LLMServiceEnum.DEEPSEEK:
            base, key, model = cfg.deepseek_api_base.value, cfg.deepseek_api_key.value, cfg.deepseek_model.value
        elif svc == LLMServiceEnum.SILICON_CLOUD:
            base, key, model = cfg.silicon_cloud_api_base.value, cfg.silicon_cloud_api_key.value, cfg.silicon_cloud_model.value
        elif svc == LLMServiceEnum.OLLAMA:
            base, key, model = cfg.ollama_api_base.value, cfg.ollama_api_key.value, cfg.ollama_model.value
        elif svc == LLMServiceEnum.GEMINI:
            base, key, model = cfg.gemini_api_base.value, cfg.gemini_api_key.value, cfg.gemini_model.value
        else:
            base, key, model = "", "", ""

        self._llm_check_thread = LLMCheckThread(base, key, model)
        self._llm_check_thread.result.connect(self._on_llm_check_result)
        self._llm_check_thread.start()
        InfoBar.info("连接测试中…", "", duration=2000, position=InfoBarPosition.TOP, parent=self)

    def _on_llm_check_result(self, ok: bool, msg: str):
        if ok:
            InfoBar.success("连接成功", msg, duration=4000, position=InfoBarPosition.TOP, parent=self)
        else:
            InfoBar.error("连接失败", msg, duration=6000, position=InfoBarPosition.TOP, parent=self)

    def _choose_notes_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择笔记存储目录", str(cfg.notes_dir.value))
        if path:
            cfg.set(cfg.notes_dir, path)
            self._notes_dir_card.setContent(path)

    def _choose_export_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择导出目录", str(cfg.export_dir.value))
        if path:
            cfg.set(cfg.export_dir, path)
            self._export_dir_card.setContent(path)
