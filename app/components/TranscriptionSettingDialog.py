# -*- coding: utf-8 -*-
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QFrame
from qfluentwidgets import (
    BodyLabel,
    ComboBoxSettingCard,
    InfoBar,
    MessageBoxBase,
    PushSettingCard,
)
from qfluentwidgets import FluentIcon as FIF

from app.common.config import cfg
from app.components.EditComboBoxSettingCard import EditComboBoxSettingCard
from app.components.LineEditSettingCard import LineEditSettingCard
from app.components.ChunkConcurrencySettingDialog import ChunkConcurrencySettingDialog
from app.components.SpinBoxSettingCard import SpinBoxSettingCard
from app.core.constant import INFOBAR_DURATION_ERROR, INFOBAR_DURATION_SUCCESS
from app.core.entities import TranscribeModelEnum, TranscribeOutputFormatEnum
from app.core.llm import check_whisper_connection


class WhisperConnectionThread(QThread):
    """Whisper API 连接测试线程"""

    finished = pyqtSignal(bool, str)
    error = pyqtSignal(str)

    def __init__(self, base_url, api_key, model):
        super().__init__()
        self.base_url = base_url
        self.api_key = api_key
        self.model = model

    def run(self):
        try:
            success, result = check_whisper_connection(
                self.base_url, self.api_key, self.model
            )
            self.finished.emit(success, result)
        except Exception as e:
            self.error.emit(str(e))


class TranscriptionSettingDialog(MessageBoxBase):
    """转录设置对话框（输出格式 + Whisper API 完整配置）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.titleLabel = BodyLabel(self.tr("转录设置"), self)

        # 输出格式
        self.output_format_card = ComboBoxSettingCard(
            cfg.transcribe_output_format,
            FIF.SAVE,
            self.tr("输出格式"),
            self.tr("选择转录字幕的输出格式"),
            texts=[fmt.value for fmt in TranscribeOutputFormatEnum],
            parent=self,
        )

        # ── Whisper API 专属配置 ──
        self.whisperApiBaseCard = LineEditSettingCard(
            cfg.whisper_api_base,
            FIF.LINK,
            self.tr("API Base URL"),
            self.tr("输入 Whisper API Base URL"),
            "https://api.openai.com/v1",
            self,
        )
        self.whisperApiKeyCard = LineEditSettingCard(
            cfg.whisper_api_key,
            FIF.FINGERPRINT,
            self.tr("API Key"),
            self.tr("输入 Whisper API Key"),
            "sk-",
            self,
        )
        self.whisperApiModelCard = EditComboBoxSettingCard(
            cfg.whisper_api_model,
            FIF.ROBOT,  # type: ignore
            self.tr("Whisper 模型"),
            self.tr("选择或输入模型名称"),
            [
                "whisper-1",
                "whisper-large-v3-turbo",
                "Systran/faster-whisper-large-v3",
            ],
            self,
        )
        self.checkWhisperConnectionCard = PushSettingCard(
            self.tr("测试连接"),
            FIF.CONNECT,
            self.tr("测试 Whisper API 连接"),
            self.tr("点击检测 API 是否可用"),
            self,
        )

        # VAD 参数（0 = 使用服务端默认）
        self.whisperVadThresholdCard = SpinBoxSettingCard(
            cfg.whisper_api_vad_threshold,
            FIF.FILTER,
            self.tr("VAD 灵敏度阈值"),
            self.tr("1-100，越小越灵敏；0 = 服务端默认"),
            minimum=0,
            maximum=100,
            parent=self,
        )
        self.whisperVadMinSilenceCard = SpinBoxSettingCard(
            cfg.whisper_api_vad_min_silence_ms,
            FIF.PAUSE,
            self.tr("VAD 最小静音时长 (ms)"),
            self.tr("静音多久才切断；0 = 服务端默认"),
            minimum=0,
            maximum=5000,
            parent=self,
        )
        self.whisperVadSpeechPadCard = SpinBoxSettingCard(
            cfg.whisper_api_vad_speech_pad_ms,
            FIF.ALIGNMENT,
            self.tr("VAD 语音边界扩展 (ms)"),
            self.tr("每段前后额外保留时长；0 = 服务端默认"),
            minimum=0,
            maximum=2000,
            parent=self,
        )

        # 组装布局
        # 用一条细横线作为分隔
        separator = QFrame(self)
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)

        self.chunk_concurrency_card = PushSettingCard(
            self.tr("打开"),
            FIF.SYNC,
            self.tr("并发与分块（长音频）"),
            self.tr("并发、重试、限流、切分阈值；减轻 API 压力"),
            self,
        )
        self.chunk_concurrency_card.clicked.connect(
            lambda: ChunkConcurrencySettingDialog(self.window()).exec_()
        )

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.output_format_card)
        self.viewLayout.addWidget(self.chunk_concurrency_card)
        self.viewLayout.addWidget(separator)
        self.viewLayout.addWidget(self.whisperApiBaseCard)
        self.viewLayout.addWidget(self.whisperApiKeyCard)
        self.viewLayout.addWidget(self.whisperApiModelCard)
        self.viewLayout.addWidget(self.checkWhisperConnectionCard)
        self.viewLayout.addWidget(self.whisperVadThresholdCard)
        self.viewLayout.addWidget(self.whisperVadMinSilenceCard)
        self.viewLayout.addWidget(self.whisperVadSpeechPadCard)
        self.viewLayout.setSpacing(6)

        self.setWindowTitle(self.tr("转录设置"))
        self.widget.setMinimumWidth(480)

        self.yesButton.hide()
        self.cancelButton.setText(self.tr("关闭"))

        # 根据当前模型决定是否展示 Whisper API 配置
        self._update_whisper_visibility()
        self.checkWhisperConnectionCard.clicked.connect(self._check_whisper_connection)

    # ── Whisper API 配置的显示/隐藏 ──────────────────────────────────────
    def _update_whisper_visibility(self):
        is_whisper = cfg.get(cfg.transcribe_model) == TranscribeModelEnum.WHISPER_API
        whisper_cards = [
            self.whisperApiBaseCard,
            self.whisperApiKeyCard,
            self.whisperApiModelCard,
            self.checkWhisperConnectionCard,
            self.whisperVadThresholdCard,
            self.whisperVadMinSilenceCard,
            self.whisperVadSpeechPadCard,
        ]
        for card in whisper_cards:
            card.setVisible(is_whisper)

    # ── 连接测试 ──────────────────────────────────────────────────────────
    def _check_whisper_connection(self):
        base_url = self.whisperApiBaseCard.lineEdit.text().strip()
        api_key = self.whisperApiKeyCard.lineEdit.text().strip()
        model = self.whisperApiModelCard.comboBox.currentText().strip()

        if not base_url:
            InfoBar.warning(self.tr("配置不完整"), self.tr("请输入 API Base URL"),
                            duration=3000, parent=self)
            return
        if not api_key:
            InfoBar.warning(self.tr("配置不完整"), self.tr("请输入 API Key"),
                            duration=3000, parent=self)
            return
        if not model:
            InfoBar.warning(self.tr("配置不完整"), self.tr("请输入模型名称"),
                            duration=3000, parent=self)
            return

        self.checkWhisperConnectionCard.button.setEnabled(False)
        self.checkWhisperConnectionCard.button.setText(self.tr("测试中..."))

        self._conn_thread = WhisperConnectionThread(base_url, api_key, model)
        self._conn_thread.finished.connect(self._on_connection_finished)
        self._conn_thread.error.connect(self._on_connection_error)
        self._conn_thread.start()

    def _on_connection_finished(self, success: bool, result: str):
        self.checkWhisperConnectionCard.button.setEnabled(True)
        self.checkWhisperConnectionCard.button.setText(self.tr("测试连接"))
        if success:
            InfoBar.success(self.tr("连接成功"),
                            self.tr("Whisper API 连接成功！转录结果: ") + result,
                            duration=INFOBAR_DURATION_SUCCESS, parent=self)
        else:
            InfoBar.error(self.tr("连接失败"),
                          self.tr(f"Whisper API 连接失败！\n{result}"),
                          duration=INFOBAR_DURATION_ERROR, parent=self)

    def _on_connection_error(self, message: str):
        self.checkWhisperConnectionCard.button.setEnabled(True)
        self.checkWhisperConnectionCard.button.setText(self.tr("测试连接"))
        InfoBar.error(self.tr("测试错误"), message,
                      duration=INFOBAR_DURATION_ERROR, parent=self)
