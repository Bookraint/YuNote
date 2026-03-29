import atexit
import os
import shutil

import psutil
from PyQt5.QtCore import Qt, QThread, QUrl
from PyQt5.QtGui import QDesktopServices, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.common.signal_bus import signalBus
from app.config import APP_NAME, ASSETS_PATH
from app.thread.version_checker_thread import VersionChecker
from app.view.history_interface import HistoryInterface
from app.view.home_interface import HomeInterface
from app.view.mac_styles import application_stylesheet
from app.view.note_interface import NoteInterface
from app.view.setting_interface import SettingInterface

LOGO_PATH = ASSETS_PATH / "logo.png"

# 与侧栏顺序一致，用于窗口标题与顶栏，避免 windowTitle 为空时退回成 APP_NAME 造成「小宇笔记助手 — 小宇笔记助手」
_NAV_SECTION_TITLES = ("转录", "笔记", "历史", "设置")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1100, 820)
        self.setMinimumWidth(760)

        icon_path = str(LOGO_PATH) if LOGO_PATH.exists() else ""
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

        self.statusBar().setStyleSheet(
            """
            QStatusBar {
                background-color: #2c2c2e;
                color: #d1d1d6;
                font-size: 12px;
                border-top: 1px solid #3a3a3c;
            }
            """
        )

        self.transcribeInterface = HomeInterface(self)
        self.noteInterface = NoteInterface(self)
        self.historyInterface = HistoryInterface(self)
        self.settingInterface = SettingInterface(self)

        self.versionChecker = VersionChecker()
        self.versionChecker.newVersionAvailable.connect(self._on_new_version)
        self.versionThread = QThread()
        self.versionChecker.moveToThread(self.versionThread)
        self.versionThread.started.connect(self.versionChecker.perform_check)
        self.versionThread.start()

        self._build_shell()
        self._apply_content_stylesheet()

        self._check_ffmpeg()
        atexit.register(self._stop)

        signalBus.note_ready.connect(self._on_note_ready)
        signalBus.open_note.connect(self._open_note)

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

    def _build_shell(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        top_bar = QFrame()
        top_bar.setObjectName("macTopBar")
        top_h = QHBoxLayout(top_bar)
        top_h.setContentsMargins(16, 8, 20, 8)
        top_h.setSpacing(12)

        top_logo = QLabel()
        top_logo.setObjectName("macTopBarLogo")
        if LOGO_PATH.exists():
            pix = QPixmap(str(LOGO_PATH))
            if not pix.isNull():
                top_logo.setPixmap(
                    pix.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
        top_h.addWidget(top_logo, 0, Qt.AlignVCenter)

        self._top_section_label = QLabel()
        self._top_section_label.setObjectName("macTopBarSection")
        top_h.addWidget(self._top_section_label, 0, Qt.AlignVCenter)
        top_h.addStretch()

        root.addWidget(top_bar)

        outer = QHBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._sidebar = QListWidget()
        self._sidebar.setObjectName("macSidebar")
        self._sidebar.setFrameShape(QFrame.NoFrame)

        side_wrap = QWidget()
        side_wrap.setObjectName("macSidebarWrap")
        side_wrap.setFixedWidth(196)
        side_v = QVBoxLayout(side_wrap)
        side_v.setContentsMargins(12, 12, 12, 10)
        side_v.setSpacing(8)

        nav = [
            ("🎙  转录", self.transcribeInterface),
            ("📄  笔记", self.noteInterface),
            ("🕐  历史", self.historyInterface),
            ("⚙️  设置", self.settingInterface),
        ]
        self._nav_interfaces = [w for _, w in nav]
        for label, _ in nav:
            QListWidgetItem(label, self._sidebar)

        self._stack = QStackedWidget()
        for _, iface in nav:
            self._stack.addWidget(iface)

        self._sidebar.currentRowChanged.connect(self._on_sidebar_row)
        self._sidebar.setCurrentRow(0)

        side_v.addWidget(self._sidebar, stretch=1)

        outer.addWidget(side_wrap)
        outer.addWidget(self._stack, stretch=1)
        root.addLayout(outer, stretch=1)

    def _on_sidebar_row(self, row: int):
        if row < 0:
            return
        self._stack.setCurrentIndex(row)
        section = (
            _NAV_SECTION_TITLES[row]
            if row < len(_NAV_SECTION_TITLES)
            else ""
        )
        self._top_section_label.setText(section)
        self.setWindowTitle(f"{section} — {APP_NAME}" if section else APP_NAME)

    def _apply_content_stylesheet(self):
        cw = self.centralWidget()
        if cw is not None:
            cw.setStyleSheet(application_stylesheet())
        self.setStyleSheet("QMainWindow { background-color: #1c1c1e; }")

    def show_status_message(self, message: str, timeout_ms: int = 4000) -> None:
        self.statusBar().showMessage(message, timeout_ms)

    def switchTo(self, interface: QWidget):
        try:
            idx = self._nav_interfaces.index(interface)
        except ValueError:
            return
        self._sidebar.setCurrentRow(idx)

    def _on_note_ready(self, note_id: str):
        self.noteInterface.load_note(note_id)
        self.switchTo(self.noteInterface)

    def _open_note(self, note_id: str):
        self.noteInterface.load_note(note_id)
        self.switchTo(self.noteInterface)

    def _on_new_version(self, version, update_required, update_info, download_url):
        content = f"发现新版本 {version}\n\n{update_info}"
        reply = QMessageBox.question(
            self,
            "发现新版本",
            content,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            QDesktopServices.openUrl(QUrl(download_url))

    def closeEvent(self, event):
        super().closeEvent(event)
        QApplication.quit()

    def _stop(self):
        process = psutil.Process(os.getpid())
        for child in process.children(recursive=True):
            child.kill()

    def _check_ffmpeg(self):
        if shutil.which("ffmpeg") is None:
            QMessageBox.warning(
                self,
                "FFmpeg 未安装",
                "处理音频文件需要 FFmpeg，请先安装并加入 PATH。",
            )
