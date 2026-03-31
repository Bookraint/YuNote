import os
import platform
import subprocess
import sys
import traceback


def _patch_subprocess_popen_for_frozen_windows() -> None:
    """
    PyInstaller --windowed 下主进程无控制台；pydub 等库会 ``from subprocess import Popen``。
    必须用 **Popen 的子类** 替换（不能换成普通函数），否则 importlib/部分依赖会把 Popen
    当类型用，触发 ``function() argument 'code' must be code, not str`` 等异常。
    """
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return
    if not hasattr(subprocess, "CREATE_NO_WINDOW"):
        return
    _Base = subprocess.Popen

    class _PopenNoConsole(_Base):
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            if "creationflags" not in kwargs:
                kwargs = {**kwargs, "creationflags": subprocess.CREATE_NO_WINDOW}
            super().__init__(*args, **kwargs)

    subprocess.Popen = _PopenNoConsole  # type: ignore[method-assign]


_patch_subprocess_popen_for_frozen_windows()

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
