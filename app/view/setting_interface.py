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
from app.components.PromptTemplateEditDialog import PromptTemplateEditDialog
from app.config import APPDATA_PATH, VERSION, PROMPTS_PATH
from app.core.entities import LLMServiceEnum, NoteSceneEnum, TranscribeModelEnum
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

        allowed_services = [LLMServiceEnum.OPENAI, LLMServiceEnum.OLLAMA]
        if cfg.llm_service.value not in allowed_services:
            # 避免旧配置指向不再暴露的服务商导致 UI/校验异常
            cfg.set(cfg.llm_service, LLMServiceEnum.OPENAI)

        self._llm_service_card = ComboBoxSettingCard(
            cfg.llm_service,
            FIF.ROBOT,
            "服务商",
            "选择 LLM API 服务商",
            texts=[s.value for s in allowed_services],
            parent=group,
        )
        group.addSettingCard(self._llm_service_card)

        # OpenAI（兼容通用）
        self._openai_key_card = LineEditSettingCard(
            cfg.openai_api_key,
            FIF.CERTIFICATE,
            "OpenAI API Key",
            content="",
            placeholder="",
            parent=group,
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

        # Ollama（本地）
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

        # 测试连接
        self._test_llm_card = PrimaryPushSettingCard(
            "测试连接", FIF.WIFI, "测试 LLM 连接", "验证当前服务商配置是否可用",
            parent=group
        )
        self._test_llm_card.clicked.connect(self._test_llm)
        group.addSettingCard(self._test_llm_card)

        def _refresh_llm_cards():
            svc = cfg.llm_service.value
            is_openai = svc == LLMServiceEnum.OPENAI

            self._openai_key_card.setVisible(is_openai)
            self._openai_base_card.setVisible(is_openai)
            self._openai_model_card.setVisible(is_openai)

            self._ollama_base_card.setVisible(not is_openai)
            self._ollama_model_card.setVisible(not is_openai)

        _refresh_llm_cards()
        cfg.llm_service.valueChanged.connect(lambda *_: _refresh_llm_cards())

        self._expand_layout.addWidget(group)

    # ── 转录配置 ──────────────────────────────────────────────

    def _init_transcribe_group(self):
        from app.components.TranscriptionSettingDialog import TranscriptionSettingDialog

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

        self._whisper_api_setting_card = PushSettingCard(
            "打开",
            FIF.SETTING,
            "Whisper API 设置",
            "打开弹窗编辑 Base URL / Key / 模型 / VAD 等参数",
            group,
        )
        group.addSettingCard(self._whisper_api_setting_card)
        self._whisper_api_setting_card.clicked.connect(
            lambda: TranscriptionSettingDialog(self.window()).exec_()
        )

        # 仅在 Whisper API 模式下显示入口，避免 B 接口出现大空隙
        def _resolve_transcribe_model() -> TranscribeModelEnum | None:
            raw = cfg.transcribe_model.value
            if isinstance(raw, TranscribeModelEnum):
                return raw
            if isinstance(raw, str):
                for model in TranscribeModelEnum:
                    if raw == model.value or raw == model.name:
                        return model
            return None

        def _update_transcribe_engine_visibility():
            model = _resolve_transcribe_model()
            self._whisper_api_setting_card.setVisible(
                model == TranscribeModelEnum.WHISPER_API
            )
            group.adjustSize()
            self._scroll_widget.adjustSize()
            self.viewport().update()

        _update_transcribe_engine_visibility()
        cfg.transcribe_model.valueChanged.connect(
            lambda *_: _update_transcribe_engine_visibility()
        )
        # 某些情况下 ComboBox 改变先于 ConfigItem 更新，额外监听 UI 事件确保即时刷新
        self._transcribe_model_card.comboBox.currentTextChanged.connect(  # type: ignore[attr-defined]
            lambda *_: _update_transcribe_engine_visibility()
        )

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

        # 场景模板：点击编辑（避免主页面滚动卡住）
        scene_to_filename = {
            NoteSceneEnum.MEETING: "summary_meeting.md",
            NoteSceneEnum.LECTURE: "summary_lecture.md",
            NoteSceneEnum.INTERVIEW: "summary_interview.md",
            NoteSceneEnum.GENERAL: "summary_general.md",
        }
        scene_to_override_item = {
            NoteSceneEnum.MEETING: cfg.summary_prompt_template_meeting,
            NoteSceneEnum.LECTURE: cfg.summary_prompt_template_lecture,
            NoteSceneEnum.INTERVIEW: cfg.summary_prompt_template_interview,
            NoteSceneEnum.GENERAL: cfg.summary_prompt_template_general,
        }

        def _load_template_text(scene: NoteSceneEnum) -> str:
            # 优先使用用户覆盖内容（为空则回退到内置模板）
            override_item = scene_to_override_item.get(scene)
            if override_item is not None and override_item.value:
                return override_item.value

            filename = scene_to_filename.get(scene, "summary_general.md")
            template_path = PROMPTS_PATH / filename
            if template_path.exists():
                return template_path.read_text(encoding="utf-8")
            return ""

        def _preview(text: str) -> str:
            lines = text.strip().splitlines()
            first = lines[0] if lines else ""
            first = first.strip()
            if not first:
                return self.tr("（内置模板）")
            return first[:60] + ("…" if len(first) > 60 else "")

        self._scene_template_edit_card = PushSettingCard(
            self.tr("编辑"),
            FIF.EDIT,
            self.tr("场景模板"),
            _preview(_load_template_text(cfg.default_scene.value)),
            parent=group,
        )
        group.addSettingCard(self._scene_template_edit_card)

        def _on_scene_template_edit():
            scene = cfg.default_scene.value
            override_item = scene_to_override_item.get(scene)
            initial_text = _load_template_text(scene)

            def _save(text: str):
                if override_item is not None:
                    cfg.set(override_item, text)
                self._scene_template_edit_card.setContent(_preview(text))

            dialog = PromptTemplateEditDialog(
                initial_text=initial_text,
                on_save=_save,
                parent=self.window(),
            )
            dialog.exec_()

        self._scene_template_edit_card.clicked.connect(_on_scene_template_edit)

        def _on_summary_scene_changed(*_):
            self._scene_template_edit_card.setContent(
                _preview(_load_template_text(cfg.default_scene.value))
            )

        cfg.default_scene.valueChanged.connect(_on_summary_scene_changed)

        self._custom_prompt_card = LineEditSettingCard(
            cfg.summary_custom_prompt,
            FIF.EDIT,
            "追加指令",
            content="",
            placeholder="附加在 Prompt 末尾的自定义要求（留空则不追加）",
            parent=group,
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

        self._dpi_card = ComboBoxSettingCard(
            cfg.dpiScale,
            FIF.ZOOM,
            "缩放比例",
            "修改后重启生效",
            texts=["1x", "1.25x", "1.5x", "1.75x", "2x", "Auto"],
            parent=group,
        )
        group.addSettingCard(self._dpi_card)

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
