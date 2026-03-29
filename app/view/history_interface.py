"""
历史笔记列表页：搜索 / 场景筛选 / 查看 / 删除。
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.common.signal_bus import signalBus
from app.config import NOTES_PATH
from app.core.entities import Note, NoteSceneEnum, TaskStatusEnum
from app.core.notes import NoteManager
from app.core.utils.audio_utils import format_duration
from app.view.ui_helpers import question_dialog, status_message


class NoteCard(QFrame):
    """单条笔记卡片。"""

    def __init__(self, note: Note, parent=None):
        super().__init__(parent)
        self.note = note
        self.setObjectName("macCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(80)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        scene_icon = {
            NoteSceneEnum.MEETING:   "📋",
            NoteSceneEnum.LECTURE:   "📚",
            NoteSceneEnum.INTERVIEW: "🎤",
            NoteSceneEnum.GENERAL:   "📝",
        }.get(note.scene, "📝")
        icon_label = QLabel(scene_icon)
        icon_label.setStyleSheet("font-size: 24px;")
        icon_label.setFixedWidth(36)
        layout.addWidget(icon_label)

        content = QVBoxLayout()
        content.setSpacing(2)
        title_label = QLabel(note.title or "未命名笔记")
        f = title_label.font()
        f.setBold(True)
        f.setPointSize(13)
        title_label.setFont(f)
        title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        content.addWidget(title_label)

        dur_str = format_duration(note.duration_seconds)
        date_str = note.created_at.strftime("%Y-%m-%d %H:%M")
        meta_label = QLabel(f"{note.scene.value}  ·  {date_str}  ·  {dur_str}")
        meta_label.setObjectName("macSecondary")
        content.addWidget(meta_label)
        layout.addLayout(content, stretch=1)

        if note.status == TaskStatusEnum.FAILED:
            status_label = QLabel("❌ 处理失败")
        elif note.status == TaskStatusEnum.RUNNING:
            status_label = QLabel("⏳ 处理中")
        else:
            status_label = QLabel("")
        layout.addWidget(status_label)

        del_btn = QToolButton(self)
        del_btn.setText("🗑")
        del_btn.setToolTip("删除此笔记")
        del_btn.clicked.connect(lambda: self._request_delete())
        layout.addWidget(del_btn)

    def _request_delete(self):
        self.window().historyInterface._delete_note(self.note.note_id)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            signalBus.open_note.emit(self.note.note_id)
        super().mousePressEvent(event)


class HistoryInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("historyInterface")
        self.setWindowTitle("历史")

        self._note_manager = NoteManager(NOTES_PATH)
        self._all_notes: list[Note] = []

        self._init_ui()
        self._load_notes()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 28, 36, 28)
        root.setSpacing(16)

        title_row = QHBoxLayout()
        title_label = QLabel("历史笔记")
        title_label.setObjectName("macTitle")
        title_row.addWidget(title_label)
        title_row.addStretch()
        refresh_btn = QToolButton(self)
        refresh_btn.setText("↻")
        refresh_btn.setToolTip("刷新列表")
        refresh_btn.clicked.connect(self._load_notes)
        title_row.addWidget(refresh_btn)
        root.addLayout(title_row)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)

        self._search_box = QLineEdit(self)
        self._search_box.setPlaceholderText("搜索笔记标题…")
        self._search_box.setClearButtonEnabled(True)
        self._search_box.textChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self._search_box, stretch=1)

        self._scene_filter = QComboBox(self)
        self._scene_filter.addItem("全部场景", userData=None)
        for s in NoteSceneEnum:
            self._scene_filter.addItem(s.value, userData=s)
        self._scene_filter.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self._scene_filter)
        root.addLayout(filter_row)

        self._count_label = QLabel("")
        self._count_label.setObjectName("macSecondary")
        root.addWidget(self._count_label)

        self._list_layout = QVBoxLayout()
        self._list_layout.setSpacing(8)

        scroll_container = QWidget()
        scroll_container.setObjectName("macScrollInner")
        scroll_container.setLayout(self._list_layout)

        self._scroll = QScrollArea(self)
        self._scroll.setObjectName("macScroll")
        self._scroll.setWidget(scroll_container)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        root.addWidget(self._scroll, stretch=1)

    def _load_notes(self):
        self._all_notes = self._note_manager.list_all()
        self._refresh_list()

    def _on_filter_changed(self):
        self._refresh_list()

    def _refresh_list(self):
        query = self._search_box.text().strip()
        scene: NoteSceneEnum | None = self._scene_filter.currentData()

        notes = [n for n in self._all_notes if self._matches(n, query, scene)]
        self._count_label.setText(f"共 {len(notes)} 条笔记")

        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not notes:
            empty = QLabel("暂无笔记，去转录页导入音频吧～")
            empty.setAlignment(Qt.AlignCenter)
            empty.setObjectName("macSecondary")
            self._list_layout.addWidget(empty)
            return

        for note in notes:
            card = NoteCard(note, self)
            self._list_layout.addWidget(card)
        self._list_layout.addStretch()

    def _matches(self, note: Note, query: str, scene: NoteSceneEnum | None) -> bool:
        if scene and note.scene != scene:
            return False
        if query:
            q = query.lower()
            if q not in (note.title or "").lower() and q not in note.source_audio_name.lower():
                return False
        return True

    def _delete_note(self, note_id: str):
        note = self._note_manager.get(note_id)
        title = note.title if note else note_id
        if not question_dialog(
            self.window(),
            "删除确认",
            f"确定删除笔记「{title}」吗？\n此操作不可撤销，转录文本和总结将一并删除。",
            accept_text="删除",
            reject_text="取消",
        ):
            return
        self._note_manager.delete(note_id)
        self._all_notes = [n for n in self._all_notes if n.note_id != note_id]
        self._refresh_list()
        status_message(self, f"笔记「{title}」已删除", 3000)
