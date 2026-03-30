"""与主窗口配合的轻量提示（状态栏 / 对话框），避免依赖 Fluent InfoBar。"""

from PyQt5.QtWidgets import QMessageBox, QWidget

from app.view.mac_styles import message_box_stylesheet


def apply_message_box_style(box: QMessageBox) -> None:
    """供主窗口等直接使用 QMessageBox 实例时统一套深色样式。"""
    box.setStyleSheet(message_box_stylesheet())


def status_message(parent: QWidget, text: str, timeout_ms: int = 4000) -> None:
    w = parent.window()
    if hasattr(w, "show_status_message"):
        w.show_status_message(text, timeout_ms)


def warning_dialog(parent: QWidget, title: str, text: str) -> None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Ok)
    apply_message_box_style(box)
    box.exec_()


def info_dialog(parent: QWidget, title: str, text: str) -> None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Information)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Ok)
    apply_message_box_style(box)
    box.exec_()


def question_dialog(
    parent: QWidget,
    title: str,
    text: str,
    *,
    accept_text: str = "是",
    reject_text: str = "否",
) -> bool:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Question)
    box.setWindowTitle(title)
    box.setText(text)
    yes_btn = box.addButton(accept_text, QMessageBox.AcceptRole)
    box.addButton(reject_text, QMessageBox.RejectRole)
    apply_message_box_style(box)
    box.exec_()
    return box.clickedButton() == yes_btn
