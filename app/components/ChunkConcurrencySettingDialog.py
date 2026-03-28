# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QFrame
from qfluentwidgets import BodyLabel, MessageBoxBase, SwitchSettingCard
from qfluentwidgets import FluentIcon as FIF

from app.common.config import cfg
from app.components.SpinBoxSettingCard import SpinBoxSettingCard


class ChunkConcurrencySettingDialog(MessageBoxBase):
    """并发处理与音频切分（长音频转录防 API 过载）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.titleLabel = BodyLabel(self.tr("并发处理设置"), self)

        self.enable_async_card = SwitchSettingCard(
            FIF.SYNC,
            self.tr("启用异步并发处理"),
            self.tr("关闭后按顺序逐块转录，更稳但更慢"),
            cfg.transcribe_enable_async,
            self,
        )
        self.max_concurrent_card = SpinBoxSettingCard(
            cfg.transcribe_max_concurrent_chunks,
            FIF.LAYOUT,
            self.tr("最大并发片段数"),
            self.tr("同时处理的音频块数量（仅在网络与 API 允许时调高）"),
            minimum=1,
            maximum=16,
            parent=self,
        )
        self.retries_card = SpinBoxSettingCard(
            cfg.transcribe_chunk_max_retries,
            FIF.SYNC,
            self.tr("失败重试次数"),
            self.tr("单块请求失败时的最大重试次数（指数退避）"),
            minimum=1,
            maximum=10,
            parent=self,
        )
        self.rate_limit_card = SpinBoxSettingCard(
            cfg.transcribe_api_rate_limit_per_minute,
            FIF.WIFI,
            self.tr("API 速率限制"),
            self.tr("每分钟最多请求数；0 表示不限制（本地引擎通常可设 0）"),
            minimum=0,
            maximum=120,
            parent=self,
        )
        self.split_threshold_card = SpinBoxSettingCard(
            cfg.transcribe_split_threshold_minutes,
            FIF.ALIGNMENT,
            self.tr("长文件自动切分阈值（分钟）"),
            self.tr("总时长不超过该值时整段转录、不再按块切开；0 表示不按此规则整段"),
            minimum=0,
            maximum=600,
            parent=self,
        )
        self.chunk_len_card = SpinBoxSettingCard(
            cfg.transcribe_chunk_length_minutes,
            FIF.PLAY,
            self.tr("每块时长（分钟）"),
            self.tr("超过阈值需分块时，每块的大致长度"),
            minimum=5,
            maximum=120,
            parent=self,
        )

        sep = QFrame(self)
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)

        hint = BodyLabel(
            self.tr(
                "异步并发可明显加快长音频处理；并发越高对 API 压力越大。\n"
                "请结合网络与服务商限制调整；若异常可关闭异步改为顺序模式。"
            ),
            self,
        )
        hint.setWordWrap(True)

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.enable_async_card)
        self.viewLayout.addWidget(self.max_concurrent_card)
        self.viewLayout.addWidget(self.retries_card)
        self.viewLayout.addWidget(self.rate_limit_card)
        self.viewLayout.addWidget(self.split_threshold_card)
        self.viewLayout.addWidget(self.chunk_len_card)
        self.viewLayout.addWidget(sep)
        self.viewLayout.addWidget(hint)
        self.viewLayout.setSpacing(6)

        self.setWindowTitle(self.tr("并发与分块"))
        self.widget.setMinimumWidth(520)

        self.yesButton.hide()
        self.cancelButton.setText(self.tr("关闭"))
