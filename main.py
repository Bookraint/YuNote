import os
import platform
import sys
import traceback

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# PyInstaller：随包自带的 ffmpeg/ffprobe（见 YuNote.spec 中 resource/bin/ffmpeg）
if getattr(sys, "frozen", False):
    _meipass = getattr(sys, "_MEIPASS", None)
    if _meipass:
        _ffmpeg_bin = os.path.join(_meipass, "resource", "bin", "ffmpeg")
        if os.path.isdir(_ffmpeg_bin):
            os.environ["PATH"] = _ffmpeg_bin + os.pathsep + os.environ.get("PATH", "")

lib_folder = "Lib" if platform.system() == "Windows" else "lib"
plugin_path = os.path.join(
    sys.prefix, lib_folder, "site-packages", "PyQt5", "Qt5", "plugins"
)
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path

for file in os.listdir():
    if file.startswith("app") and file.endswith(".pyd"):
        os.remove(file)

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtGui import QIcon  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402
from qfluentwidgets import FluentTranslator  # noqa: E402

from app.common.config import cfg  # noqa: E402
from app.config import ASSETS_PATH  # noqa: E402
from app.core.utils.logger import setup_logger  # noqa: E402
from app.view.main_window import MainWindow  # noqa: E402

logger_instance = setup_logger("YuNote")


def exception_hook(exctype, value, tb):
    logger_instance.error("".join(traceback.format_exception(exctype, value, tb)))
    sys.__excepthook__(exctype, value, tb)


sys.excepthook = exception_hook

if cfg.get(cfg.dpiScale) == "Auto":
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough  # type: ignore
    )
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)  # type: ignore
else:
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
    os.environ["QT_SCALE_FACTOR"] = str(cfg.get(cfg.dpiScale))
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)  # type: ignore

app = QApplication(sys.argv)
app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings, True)  # type: ignore

_logo = ASSETS_PATH / "logo.png"
if _logo.exists():
    app.setWindowIcon(QIcon(str(_logo)))

# 使用 Fusion，避免 macintosh 与自定义深色 QSS 混用导致标签/标题字色异常
try:
    app.setStyle("Fusion")
except Exception:
    pass

locale = cfg.get(cfg.language).value
translator = FluentTranslator(locale)
app.installTranslator(translator)


def main():
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
