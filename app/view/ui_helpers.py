"""与主窗口配合的轻量提示（状态栏 / 对话框），避免依赖 Fluent InfoBar。"""

from PyQt5.QtWidgets import QMessageBox, QWidget


def status_message(parent: QWidget, text: str, timeout_ms: int = 4000) -> None:
    w = parent.window()
    if hasattr(w, "show_status_message"):
        w.show_status_message(text, timeout_ms)


def warning_dialog(parent: QWidget, title: str, text: str) -> None:
    QMessageBox.warning(parent, title, text)


def info_dialog(parent: QWidget, title: str, text: str) -> None:
    QMessageBox.information(parent, title, text)


def question_dialog(
    parent: QWidget,
    title: str,
    text: str,
    *,
    accept_text: str = "是",
    reject_text: str = "否",
) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    yes_btn = box.addButton(accept_text, QMessageBox.AcceptRole)
    box.addButton(reject_text, QMessageBox.RejectRole)
    box.exec_()
    return box.clickedButton() == yes_btn
