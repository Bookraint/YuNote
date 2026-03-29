"""深色内容区 + 高对比文字（与侧栏搭配，避免系统样式把字色弄成浅灰看不清）。"""


def application_stylesheet() -> str:
    return """
    QMainWindow {
        background-color: #1c1c1e;
    }
    QFrame#macTopBar {
        background-color: #2c2c2e;
        border: none;
        border-bottom: 1px solid #3a3a3c;
        min-height: 52px;
    }
    QLabel#macTopBarLogo {
        background-color: transparent;
    }
    QLabel#macTopBarSection {
        color: #f2f2f7;
        font-size: 15px;
        font-weight: 600;
    }
    QStackedWidget {
        background-color: #1c1c1e;
    }
    QWidget#transcribeInterface,
    QWidget#noteInterface,
    QWidget#historyInterface {
        background-color: #1c1c1e;
        color: #f2f2f7;
    }

    QWidget#macSidebarWrap {
        background-color: #2c2c2e;
        border: none;
        border-right: 1px solid #3a3a3c;
    }
    QListWidget#macSidebar {
        background-color: #2c2c2e;
        border: none;
        outline: none;
        font-size: 13px;
        color: #ebebf5;
    }
    QListWidget#macSidebar::item {
        padding: 8px 14px;
        margin: 2px 8px;
        border-radius: 6px;
        min-height: 22px;
        color: #ebebf5;
    }
    QListWidget#macSidebar::item:selected {
        background-color: #3a3a3c;
        color: #ffffff;
    }
    QListWidget#macSidebar::item:hover:!selected {
        background-color: #48484a;
    }

    QLabel {
        color: #f2f2f7;
    }
    QLabel#macTitle {
        font-size: 22px;
        font-weight: 600;
        color: #ffffff;
    }
    QLabel#macSecondary {
        color: #aeaeb2;
        font-size: 12px;
    }

    QFrame#macCard {
        background-color: #2c2c2e;
        border: 1px solid #48484a;
        border-radius: 10px;
    }
    QFrame#macDropZone {
        background-color: #252528;
        border: 2px dashed #636366;
        border-radius: 10px;
    }
    QFrame#macDropZone:hover {
        border-color: #0a84ff;
        background-color: #2a2a32;
    }
    QFrame#macDropZone QLabel {
        color: #d1d1d6;
    }
    QFrame#macDropZoneFilled {
        background-color: rgba(10, 132, 255, 0.12);
        border: 2px solid #0a84ff;
        border-radius: 10px;
    }
    QFrame#macDropZoneFilled:hover {
        background-color: rgba(10, 132, 255, 0.18);
        border-color: #409cff;
    }
    QLabel#macDropZoneFileName {
        color: #f2f2f7;
        font-size: 16px;
        font-weight: 600;
    }
    QFrame#macDropZoneFilled QLabel#macSecondary {
        color: #aeaeb2;
        font-size: 12px;
    }

    QLineEdit {
        background-color: #2c2c2e;
        border: 1px solid #48484a;
        border-radius: 6px;
        padding: 6px 10px;
        color: #f2f2f7;
        selection-background-color: #0a84ff;
    }
    QLineEdit:focus {
        border-color: #0a84ff;
    }

    QComboBox {
        background-color: #2c2c2e;
        border: 1px solid #48484a;
        border-radius: 6px;
        padding: 5px 10px;
        min-height: 22px;
        color: #f2f2f7;
    }
    QComboBox:hover {
        border-color: #636366;
    }
    QComboBox::drop-down {
        border: none;
        width: 22px;
    }
    QComboBox QAbstractItemView {
        background-color: #2c2c2e;
        color: #f2f2f7;
        selection-background-color: #0a84ff;
        border: 1px solid #48484a;
    }

    QPushButton {
        background-color: #3a3a3c;
        color: #f2f2f7;
        border: 1px solid #48484a;
        border-radius: 6px;
        padding: 6px 14px;
        min-height: 22px;
    }
    QPushButton:hover {
        background-color: #48484a;
    }
    QPushButton:pressed {
        background-color: #2c2c2e;
    }
    QPushButton:default {
        background-color: #0a84ff;
        color: #ffffff;
        border-color: #0a84ff;
    }
    QPushButton:default:hover {
        background-color: #409cff;
    }

    QToolButton {
        background-color: transparent;
        color: #f2f2f7;
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 4px 8px;
    }
    QToolButton:hover {
        background-color: #3a3a3c;
        border-color: #48484a;
    }

    QProgressBar {
        border: none;
        border-radius: 4px;
        background-color: #3a3a3c;
        height: 8px;
    }
    QProgressBar::chunk {
        background-color: #0a84ff;
        border-radius: 4px;
    }

    QScrollArea#macScroll {
        background-color: #1c1c1e;
        border: none;
    }
    QWidget#macScrollInner {
        background-color: #1c1c1e;
    }

    QSplitter::handle {
        background-color: #3a3a3c;
    }
    QSplitter::handle:horizontal {
        width: 1px;
    }
    """
