"""
设置页：全局设置（LLM、笔记存储、界面等）。
转录引擎见转录页；AI 总结参数见笔记详情页。
"""
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QFileDialog, QWidget
from qfluentwidgets import (
    ComboBoxSettingCard,
    ExpandLayout,
    InfoBar,
    InfoBarPosition,
    PrimaryPushSettingCard,
    PushSettingCard,
    ScrollArea,
    SettingCardGroup,
    SwitchSettingCard,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from app.common.config import cfg
from app.components.EditComboBoxSettingCard import EditComboBoxSettingCard
from app.components.LineEditSettingCard import LineEditSettingCard
from app.core.entities import LLMServiceEnum
from app.core.llm.check_llm import check_llm_connection


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

        self._keep_work_card = SwitchSettingCard(
            FIF.SAVE,
            "保留预处理音频",
            "关闭时处理完成后删除笔记目录内的 audio.wav（格式转换时生成）",
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
            texts=["1x", "1.25x", "1.5x", "1.75x", "2x"],
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
