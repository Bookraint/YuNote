import atexit
import os
import shutil

import psutil
from PyQt5.QtCore import QSize, QThread
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import (
    FluentWindow,
    InfoBar,
    InfoBarPosition,
    NavigationItemPosition,
    SplashScreen,
)

from app.common.config import cfg
from app.common.signal_bus import signalBus
from app.config import ASSETS_PATH, APP_NAME
from app.core.constant import INFOBAR_DURATION_FOREVER
from app.thread.version_checker_thread import VersionChecker
from app.view.history_interface import HistoryInterface
from app.view.home_interface import HomeInterface
from app.view.note_interface import NoteInterface
from app.view.setting_interface import SettingInterface

LOGO_PATH = ASSETS_PATH / "logo.png"


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.initWindow()

        self.homeInterface = HomeInterface(self)
        self.noteInterface = NoteInterface(self)
        self.historyInterface = HistoryInterface(self)
        self.settingInterface = SettingInterface(self)

        # 版本检查
        self.versionChecker = VersionChecker()
        self.versionChecker.newVersionAvailable.connect(self._on_new_version)
        self.versionThread = QThread()
        self.versionChecker.moveToThread(self.versionThread)
        self.versionThread.started.connect(self.versionChecker.perform_check)
        self.versionThread.start()

        self.initNavigation()
        self.splashScreen.finish()
        self._check_ffmpeg()
        atexit.register(self._stop)

        # 笔记就绪后自动跳转到笔记详情页
        signalBus.note_ready.connect(self._on_note_ready)
        # 从历史页打开笔记
        signalBus.open_note.connect(self._open_note)

    def initNavigation(self):
        self.addSubInterface(self.homeInterface,    FIF.HOME,      "主页")
        self.addSubInterface(self.noteInterface,    FIF.DOCUMENT,  "笔记")
        self.addSubInterface(self.historyInterface, FIF.HISTORY,   "历史")

        self.navigationInterface.addSeparator()

        self.addSubInterface(
            self.settingInterface,
            FIF.SETTING,
            "设置",
            NavigationItemPosition.BOTTOM,
        )
        self.switchTo(self.homeInterface)

    def switchTo(self, interface):
        self.setWindowTitle(
            interface.windowTitle() if interface.windowTitle() else APP_NAME
        )
        self.stackedWidget.setCurrentWidget(interface, popOut=False)

    def initWindow(self):
        self.resize(1100, 820)
        self.setMinimumWidth(760)
        icon_path = str(LOGO_PATH) if LOGO_PATH.exists() else ""
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
        self.setWindowTitle(APP_NAME)
        self.setMicaEffectEnabled(cfg.get(cfg.micaEnabled))

        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(106, 106))
        self.splashScreen.raise_()

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

        self.show()
        QApplication.processEvents()

    def _on_note_ready(self, note_id: str):
        self.noteInterface.load_note(note_id)
        self.switchTo(self.noteInterface)

    def _open_note(self, note_id: str):
        self.noteInterface.load_note(note_id)
        self.switchTo(self.noteInterface)

    def _on_new_version(self, version, update_required, update_info, download_url):
        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QDesktopServices
        from qfluentwidgets import MessageBox

        content = f"发现新版本 {version}\n\n{update_info}"
        w = MessageBox("发现新版本", content, self)
        w.yesButton.setText("立即更新")
        w.cancelButton.setText("稍后再说")
        if w.exec():
            QDesktopServices.openUrl(QUrl(download_url))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "splashScreen"):
            self.splashScreen.resize(self.size())

    def closeEvent(self, event):
        super().closeEvent(event)
        QApplication.quit()

    def _stop(self):
        process = psutil.Process(os.getpid())
        for child in process.children(recursive=True):
            child.kill()

    def _check_ffmpeg(self):
        if shutil.which("ffmpeg") is None:
            InfoBar.warning(
                "FFmpeg 未安装",
                "处理音频文件需要 FFmpeg，请先安装并加入 PATH",
                duration=INFOBAR_DURATION_FOREVER,
                position=InfoBarPosition.BOTTOM,
                parent=self,
            )
