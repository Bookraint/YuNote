from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QPlainTextEdit
from qfluentwidgets import SettingCard


class PromptTemplateEditorCard(SettingCard):
    """多行 Prompt 模板编辑卡片。"""

    textChanged = pyqtSignal(str)

    def __init__(
        self,
        config_icon: object,
        title: str,
        content: Optional[str] = None,
        placeholder: str = "",
        initial_text: str = "",
        parent=None,
    ):
        # qfluentwidgets 的 SettingCard 构造参数是 (icon, title, content, parent)
        super().__init__(config_icon, title, content, parent)

        self._suppress_signal = False

        self.text_edit = QPlainTextEdit(self)
        self.text_edit.setPlaceholderText(placeholder)
        self.text_edit.setPlainText(initial_text)

        # 让多行编辑区更舒适
        font = self.text_edit.font()
        font.setFamily("Menlo")
        font.setPointSize(11)
        self.text_edit.setFont(font)

        self.text_edit.setMinimumHeight(180)

        # SettingCard 内部通常是 hBoxLayout；直接塞进去即可
        self.hBoxLayout.addWidget(self.text_edit, 1, Qt.AlignTop)  # type: ignore
        self.hBoxLayout.addSpacing(16)

        self.text_edit.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self):
        if self._suppress_signal:
            return
        self.textChanged.emit(self.text_edit.toPlainText())

    def set_text(self, text: str, *, suppress_signal: bool = True) -> None:
        """设置编辑区内容。默认抑制信号，避免写回覆盖。"""
        self._suppress_signal = suppress_signal
        self.text_edit.setPlainText(text)
        self._suppress_signal = False

