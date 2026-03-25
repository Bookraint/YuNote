"""
历史笔记列表页：搜索 / 场景筛选 / 查看 / 删除。
"""
from pathlib import Path

from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    ComboBox,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    MessageBox,
    PushButton,
    SubtitleLabel,
    TitleLabel,
    ToolButton,
    FluentIcon as FIF,
)

from app.common.signal_bus import signalBus
from app.config import NOTES_PATH
from app.core.entities import Note, NoteSceneEnum, TaskStatusEnum
from app.core.notes import NoteManager
from app.core.utils.audio_utils import format_duration


class NoteCard(CardWidget):
    """单条笔记卡片。"""

    def __init__(self, note: Note, parent=None):
        super().__init__(parent)
        self.note = note
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(80)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # 场景标签图标
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

        # 主内容
        content = QVBoxLayout()
        content.setSpacing(2)
        title_label = SubtitleLabel(note.title or "未命名笔记")
        title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        content.addWidget(title_label)

        dur_str = format_duration(note.duration_seconds)
        date_str = note.created_at.strftime("%Y-%m-%d %H:%M")
        meta_label = BodyLabel(f"{note.scene.value}  ·  {date_str}  ·  {dur_str}")
        meta_label.setObjectName("metaSecondary")
        content.addWidget(meta_label)
        layout.addLayout(content, stretch=1)

        # 状态标签
        if note.status == TaskStatusEnum.FAILED:
            status_label = BodyLabel("❌ 处理失败")
        elif note.status == TaskStatusEnum.RUNNING:
            status_label = BodyLabel("⏳ 处理中")
        else:
            status_label = BodyLabel("")
        layout.addWidget(status_label)

        # 删除按钮
        del_btn = ToolButton(FIF.DELETE, self)
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

        # 标题 + 刷新
        title_row = QHBoxLayout()
        title_row.addWidget(TitleLabel("历史笔记"))
        title_row.addStretch()
        refresh_btn = ToolButton(FIF.SYNC, self)
        refresh_btn.setToolTip("刷新列表")
        refresh_btn.clicked.connect(self._load_notes)
        title_row.addWidget(refresh_btn)
        root.addLayout(title_row)

        # 搜索 + 场景筛选
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)

        self._search_box = LineEdit(self)
        self._search_box.setPlaceholderText("搜索笔记标题…")
        self._search_box.setClearButtonEnabled(True)
        self._search_box.textChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self._search_box, stretch=1)

        self._scene_filter = ComboBox(self)
        self._scene_filter.addItem("全部场景", userData=None)
        for s in NoteSceneEnum:
            self._scene_filter.addItem(s.value, userData=s)
        self._scene_filter.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self._scene_filter)
        root.addLayout(filter_row)

        # 统计栏
        self._count_label = BodyLabel("")
        root.addWidget(self._count_label)

        # 列表
        self._list_layout = QVBoxLayout()
        self._list_layout.setSpacing(8)

        scroll_container = QWidget()
        scroll_container.setLayout(self._list_layout)

        from qfluentwidgets import ScrollArea
        self._scroll = ScrollArea(self)
        self._scroll.setWidget(scroll_container)
        self._scroll.setWidgetResizable(True)
        self._scroll.enableTransparentBackground()
        root.addWidget(self._scroll, stretch=1)

    # ── 数据加载与筛选 ─────────────────────────────────────────

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

        # 清空旧卡片
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not notes:
            empty = BodyLabel("暂无笔记，去主页导入音频吧～")
            empty.setAlignment(Qt.AlignCenter)
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

    # ── 删除 ──────────────────────────────────────────────────

    def _delete_note(self, note_id: str):
        note = self._note_manager.get(note_id)
        title = note.title if note else note_id
        dialog = MessageBox(
            "删除确认",
            f"确定删除笔记「{title}」吗？\n此操作不可撤销，转录文本和总结将一并删除。",
            self.window(),
        )
        dialog.yesButton.setText("删除")
        dialog.cancelButton.setText("取消")
        if dialog.exec():
            self._note_manager.delete(note_id)
            self._all_notes = [n for n in self._all_notes if n.note_id != note_id]
            self._refresh_list()
            InfoBar.success(
                "已删除",
                f"笔记「{title}」已删除",
                duration=3000,
                position=InfoBarPosition.TOP,
                parent=self,
            )
