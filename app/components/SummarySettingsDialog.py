"""AI 总结参数（Fluent 卡片），从笔记页以弹窗打开。"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.view.fluent_setting_blocks import SummarySettingsBlock


class SummarySettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 总结参数")
        self.setModal(True)
        self.resize(540, 620)
        self.setMinimumWidth(480)

        root = QVBoxLayout(self)
        root.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 8, 0)

        def _on_layout():
            inner.adjustSize()
            scroll.widget().updateGeometry()

        self._block = SummarySettingsBlock(inner, on_layout_changed=_on_layout)
        inner_layout.addWidget(self._block)

        scroll.setWidget(inner)
        root.addWidget(scroll, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        box = QDialogButtonBox(QDialogButtonBox.Ok)
        box.accepted.connect(self.accept)
        btn_row.addWidget(box)
        root.addLayout(btn_row)

    def done(self, r: int) -> None:
        self._disconnect_block_signals()
        super().done(r)

    def closeEvent(self, event) -> None:
        self._disconnect_block_signals()
        super().closeEvent(event)

    def _disconnect_block_signals(self) -> None:
        if getattr(self, "_block", None) is not None:
            self._block.disconnect_summary_signals()
