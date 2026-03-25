from typing import Callable

from qfluentwidgets import BodyLabel, MessageBoxBase, PlainTextEdit


class PromptTemplateEditDialog(MessageBoxBase):
    """场景模板编辑对话框（独立弹出，避免主页面滚动不畅）。"""

    def __init__(
        self,
        initial_text: str,
        on_save: Callable[[str], None],
        parent=None,
    ):
        super().__init__(parent)
        self._on_save = on_save
        self.editor = PlainTextEdit()
        self.editor.setTabChangesFocus(True)
        self.editor.setMinimumHeight(420)
        self.editor.setPlainText(initial_text)

        self.titleLabel = BodyLabel(self.tr("编辑场景模板"), self)
        self.hintLabel = BodyLabel(
            self.tr("提示：保留 `{{transcript}}` 变量；空白将回退到内置模板。"),
            self,
        )

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.hintLabel)
        self.viewLayout.addWidget(self.editor)

        self.widget.setMinimumWidth(700)

        self.yesButton.setText(self.tr("保存"))
        self.cancelButton.setText(self.tr("取消"))

        self.yesButton.clicked.connect(self._save_and_accept)

    def _save_and_accept(self):
        text = self.editor.toPlainText()
        self._on_save(text)
        self.accept()

