"""
可嵌入转录页 / 笔记页的 Fluent 设置卡片块（与全局设置页共享同一份 cfg）。
"""
from __future__ import annotations

from typing import Callable

from PyQt5.QtWidgets import QApplication, QWidget
from qfluentwidgets import (
    ComboBoxSettingCard,
    ExpandLayout,
    PushSettingCard,
    RangeSettingCard,
    SettingCardGroup,
    SwitchSettingCard,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from app.common.config import cfg
from app.components.LineEditSettingCard import LineEditSettingCard
from app.components.PromptTemplateEditDialog import PromptTemplateEditDialog
from app.components.SpinBoxSettingCard import SpinBoxSettingCard
from app.config import PROMPTS_PATH
from app.core.entities import NoteSceneEnum, TranscribeModelEnum


def _dialog_parent(widget: QWidget) -> QWidget:
    w = widget.window()
    return w if w is not None else widget


class TranscribeSettingsBlock(QWidget):
    """转录引擎相关设置（原设置页「转录引擎」分组）。"""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        on_layout_changed: Callable[[], None] | None = None,
    ):
        super().__init__(parent)
        self._on_layout_changed = on_layout_changed or (lambda: None)

        from app.components.ChunkConcurrencySettingDialog import (
            ChunkConcurrencySettingDialog,
        )
        from app.components.TranscriptionSettingDialog import TranscriptionSettingDialog

        layout = ExpandLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group = SettingCardGroup("转录引擎", self)

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
            texts=[lang.value for lang in cfg.transcribe_language.options],
            parent=group,
        )
        group.addSettingCard(self._transcribe_lang_card)

        self._chunk_concurrency_card = PushSettingCard(
            "打开",
            FIF.SYNC,
            "并发与分块（长音频）",
            "并发数、重试、API 限流、整段阈值等，避免请求过多导致失败",
            group,
        )
        group.addSettingCard(self._chunk_concurrency_card)
        self._chunk_concurrency_card.clicked.connect(
            lambda: ChunkConcurrencySettingDialog(_dialog_parent(self)).exec_()
        )

        self._whisper_api_setting_card = PushSettingCard(
            "打开",
            FIF.SETTING,
            "Whisper API 设置",
            "打开弹窗编辑 Base URL / Key / 模型 / VAD 等参数",
            group,
        )
        group.addSettingCard(self._whisper_api_setting_card)
        self._whisper_api_setting_card.clicked.connect(
            lambda: TranscriptionSettingDialog(_dialog_parent(self)).exec_()
        )

        self._elevenlabs_model_card = LineEditSettingCard(
            cfg.elevenlabs_model_id,
            FIF.LABEL,
            "ElevenLabs 模型 ID",
            content="一般为 scribe_v1",
            placeholder="scribe_v1",
            parent=group,
        )
        group.addSettingCard(self._elevenlabs_model_card)

        self._elevenlabs_diarize_card = SwitchSettingCard(
            FIF.PEOPLE,
            "ElevenLabs 说话人分离",
            "开启后对转录文本按说话人标注 [speaker_n]",
            cfg.elevenlabs_diarize,
            group,
        )
        group.addSettingCard(self._elevenlabs_diarize_card)

        self._elevenlabs_tag_events_card = SwitchSettingCard(
            FIF.MUSIC,
            "标记非语音事件",
            "在结果中标注笑声、掌声等（英文等语言效果更明显）",
            cfg.elevenlabs_tag_audio_events,
            group,
        )
        group.addSettingCard(self._elevenlabs_tag_events_card)

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
            el = model == TranscribeModelEnum.ELEVENLABS
            self._elevenlabs_model_card.setVisible(el)
            self._elevenlabs_diarize_card.setVisible(el)
            self._elevenlabs_tag_events_card.setVisible(el)
            group.adjustSize()
            self._on_layout_changed()

        _update_transcribe_engine_visibility()
        cfg.transcribe_model.valueChanged.connect(
            lambda *_: _update_transcribe_engine_visibility()
        )
        self._transcribe_model_card.comboBox.currentTextChanged.connect(  # type: ignore[attr-defined]
            lambda *_: _update_transcribe_engine_visibility()
        )

        layout.addWidget(group)


class SummarySettingsBlock(QWidget):
    """AI 总结相关设置（原设置页「AI 总结」分组）。"""

    _SCENE_PROMPT_FILES = {
        NoteSceneEnum.MEETING: "summary_meeting.md",
        NoteSceneEnum.LECTURE: "summary_lecture.md",
        NoteSceneEnum.INTERVIEW: "summary_interview.md",
        NoteSceneEnum.GENERAL: "summary_general.md",
    }

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        on_layout_changed: Callable[[], None] | None = None,
    ):
        super().__init__(parent)
        self._on_layout_changed = on_layout_changed or (lambda: None)

        self._scene_override_cfg = {
            NoteSceneEnum.MEETING: cfg.summary_prompt_template_meeting,
            NoteSceneEnum.LECTURE: cfg.summary_prompt_template_lecture,
            NoteSceneEnum.INTERVIEW: cfg.summary_prompt_template_interview,
            NoteSceneEnum.GENERAL: cfg.summary_prompt_template_general,
        }

        layout = ExpandLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group = SettingCardGroup("AI 总结", self)

        self._default_scene_card = ComboBoxSettingCard(
            cfg.default_scene,
            FIF.DOCUMENT,
            "默认场景",
            "新建笔记时预选的总结场景",
            texts=[s.value for s in cfg.default_scene.options],
            parent=group,
        )
        group.addSettingCard(self._default_scene_card)

        self._scene_template_edit_card = PushSettingCard(
            "编辑",
            FIF.EDIT,
            "场景模板",
            self._preview_text(self._load_template_text(cfg.default_scene.value)),
            parent=group,
        )
        group.addSettingCard(self._scene_template_edit_card)
        self._scene_template_edit_card.clicked.connect(self._on_scene_template_clicked)

        cfg.default_scene.valueChanged.connect(self._on_summary_scene_changed)

        self._custom_prompt_card = LineEditSettingCard(
            cfg.summary_custom_prompt,
            FIF.EDIT,
            "追加指令",
            content="",
            placeholder="附加在 Prompt 末尾的自定义要求（留空则不追加）",
            parent=group,
        )
        group.addSettingCard(self._custom_prompt_card)

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

        self._summary_map_concurrency_card = SpinBoxSettingCard(
            cfg.summary_map_concurrency,
            FIF.SYNC,
            "总结 Map 并发数",
            "长文分多块并行提取要点时，同时发起的 LLM 请求数（1=顺序）",
            minimum=1,
            maximum=16,
            parent=group,
        )
        group.addSettingCard(self._summary_map_concurrency_card)

        self._summary_map_rpm_card = SpinBoxSettingCard(
            cfg.summary_map_rpm,
            FIF.WIFI,
            "总结 Map API 限速 (RPM)",
            "每分钟最多请求次数，避免触发服务商限流；0 表示不限制",
            minimum=0,
            maximum=500,
            parent=group,
        )
        group.addSettingCard(self._summary_map_rpm_card)

        layout.addWidget(group)

    def _load_template_text(self, scene: NoteSceneEnum) -> str:
        override_item = self._scene_override_cfg.get(scene)
        if override_item is not None and override_item.value:
            return override_item.value

        filename = self._SCENE_PROMPT_FILES.get(scene, "summary_general.md")
        template_path = PROMPTS_PATH / filename
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
        return ""

    @staticmethod
    def _preview_text(text: str) -> str:
        lines = text.strip().splitlines()
        first = lines[0] if lines else ""
        first = first.strip()
        if not first:
            return "（内置模板）"
        return first[:60] + ("…" if len(first) > 60 else "")

    def _on_summary_scene_changed(self, *_args) -> None:
        try:
            self._scene_template_edit_card.setContent(
                self._preview_text(self._load_template_text(cfg.default_scene.value))
            )
        except RuntimeError:
            return
        self._on_layout_changed()

    def disconnect_summary_signals(self) -> None:
        try:
            cfg.default_scene.valueChanged.disconnect(self._on_summary_scene_changed)
        except TypeError:
            pass

    def _on_scene_template_clicked(self) -> None:
        scene = cfg.default_scene.value
        override_item = self._scene_override_cfg.get(scene)
        initial_text = self._load_template_text(scene)

        def _save(text: str) -> None:
            if override_item is not None:
                cfg.set(override_item, text)
            try:
                self._scene_template_edit_card.setContent(self._preview_text(text))
            except RuntimeError:
                pass

        # 使用当前前台窗口作父级，避免嵌套在「总结参数」模态弹窗内时子对话框无法置顶
        aw = QApplication.activeWindow()
        parent = aw if aw is not None else _dialog_parent(self)
        dialog = PromptTemplateEditDialog(
            initial_text=initial_text,
            on_save=_save,
            parent=parent,
        )
        dialog.exec_()
