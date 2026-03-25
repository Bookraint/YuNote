"""
笔记详情页：左栏转录原文，右栏 AI 总结（可编辑），顶部导出。
"""
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    InfoBar,
    InfoBarPosition,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
    TitleLabel,
    ToolButton,
    FluentIcon as FIF,
    RoundMenu,
    Action,
)

from app.common.config import cfg
from app.config import NOTES_PATH
from app.core.entities import Note
from app.core.notes import NoteExporter, NoteManager
from app.config import EXPORT_PATH


class NoteInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("noteInterface")
        self.setWindowTitle("笔记")

        self._note_manager = NoteManager(NOTES_PATH)
        self._exporter = NoteExporter(self._note_manager, EXPORT_PATH)
        self._current_note: Note | None = None

        self._init_ui()
        self._show_empty_state()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 28, 36, 28)
        root.setSpacing(16)

        # 顶部：标题 + 元信息 + 导出按钮
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        self._title_label = TitleLabel("笔记详情")
        self._title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        top_row.addWidget(self._title_label)

        self._meta_label = BodyLabel("")
        self._meta_label.setObjectName("metaLabel")
        top_row.addWidget(self._meta_label)

        self._export_btn = PushButton(FIF.SHARE, "导出")
        self._export_btn.clicked.connect(self._show_export_menu)
        top_row.addWidget(self._export_btn)

        self._open_folder_btn = ToolButton(FIF.FOLDER, self)
        self._open_folder_btn.setToolTip("打开笔记目录")
        self._open_folder_btn.clicked.connect(self._open_note_folder)
        top_row.addWidget(self._open_folder_btn)

        root.addLayout(top_row)

        # 主体：左右分栏
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # 左栏：转录原文
        left_card = CardWidget()
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(16, 12, 16, 12)
        left_layout.setSpacing(8)

        left_header = QHBoxLayout()
        left_header.addWidget(SubtitleLabel("转录原文"))
        left_header.addStretch()
        self._copy_transcript_btn = ToolButton(FIF.COPY, left_card)
        self._copy_transcript_btn.setToolTip("复制全文")
        self._copy_transcript_btn.clicked.connect(self._copy_transcript)
        left_header.addWidget(self._copy_transcript_btn)
        left_layout.addLayout(left_header)

        self._transcript_edit = QPlainTextEdit()
        self._transcript_edit.setReadOnly(True)
        self._transcript_edit.setPlaceholderText("转录文本将显示在这里…")
        self._transcript_edit.setStyleSheet(
            "QPlainTextEdit { background: transparent; border: none; font-size: 13px; line-height: 1.6; }"
        )
        left_layout.addWidget(self._transcript_edit)
        splitter.addWidget(left_card)

        # 右栏：AI 总结
        right_card = CardWidget()
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(16, 12, 16, 12)
        right_layout.setSpacing(8)

        right_header = QHBoxLayout()
        right_header.addWidget(SubtitleLabel("AI 总结"))
        right_header.addStretch()
        self._edit_toggle_btn = PushButton(FIF.EDIT, "编辑")
        self._edit_toggle_btn.setCheckable(False)
        self._edit_toggle_btn.clicked.connect(self._toggle_edit)
        right_header.addWidget(self._edit_toggle_btn)
        self._save_btn = PrimaryPushButton(FIF.SAVE, "保存")
        self._save_btn.clicked.connect(self._save_summary)
        self._save_btn.hide()
        right_header.addWidget(self._save_btn)
        self._copy_summary_btn = ToolButton(FIF.COPY, right_card)
        self._copy_summary_btn.setToolTip("复制总结")
        self._copy_summary_btn.clicked.connect(self._copy_summary)
        right_header.addWidget(self._copy_summary_btn)
        right_layout.addLayout(right_header)

        self._summary_edit = QPlainTextEdit()
        self._summary_edit.setReadOnly(True)
        self._summary_edit.setPlaceholderText("AI 总结将显示在这里…")
        self._summary_edit.setStyleSheet(
            "QPlainTextEdit { background: transparent; border: none; font-size: 13px; line-height: 1.6; }"
        )
        right_layout.addWidget(self._summary_edit)
        splitter.addWidget(right_card)

        splitter.setSizes([420, 580])
        root.addWidget(splitter, stretch=1)

        # 底部元信息栏
        bottom_bar = QHBoxLayout()
        self._source_label = BodyLabel("")
        self._source_label.setObjectName("sourceLabel")
        bottom_bar.addWidget(self._source_label)
        bottom_bar.addStretch()
        self._model_label = BodyLabel("")
        self._model_label.setObjectName("modelLabel")
        bottom_bar.addWidget(self._model_label)
        root.addLayout(bottom_bar)

    # ── 加载笔记 ──────────────────────────────────────────────

    def load_note(self, note_id: str):
        note = self._note_manager.get(note_id)
        if not note:
            return
        self._current_note = note

        self._title_label.setText(note.title or "未命名笔记")
        scene_str = note.scene.value
        date_str = note.created_at.strftime("%Y-%m-%d %H:%M")
        self._meta_label.setText(f"{scene_str}  ·  {date_str}")

        transcript = self._note_manager.get_transcript(note_id)
        self._transcript_edit.setPlainText(transcript)

        summary = self._note_manager.get_summary(note_id)
        self._summary_edit.setPlainText(summary)
        self._summary_edit.setReadOnly(True)
        self._edit_toggle_btn.setText("编辑")
        self._save_btn.hide()

        dur = note.duration_seconds
        h, r = divmod(int(dur), 3600)
        m, s = divmod(r, 60)
        dur_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
        self._source_label.setText(
            f"来源：{note.source_audio_name or '未知'}   时长：{dur_str}"
        )
        self._model_label.setText(
            f"转录：{note.transcribe_model or '-'}   LLM：{note.llm_model or '-'}"
        )

    def _show_empty_state(self):
        self._title_label.setText("笔记详情")
        self._meta_label.setText("")
        self._transcript_edit.setPlainText("")
        self._summary_edit.setPlainText("")
        self._source_label.setText("")
        self._model_label.setText("")

    # ── 编辑总结 ──────────────────────────────────────────────

    def _toggle_edit(self):
        if self._summary_edit.isReadOnly():
            self._summary_edit.setReadOnly(False)
            self._edit_toggle_btn.setText("取消")
            self._save_btn.show()
        else:
            if self._current_note:
                original = self._note_manager.get_summary(self._current_note.note_id)
                self._summary_edit.setPlainText(original)
            self._summary_edit.setReadOnly(True)
            self._edit_toggle_btn.setText("编辑")
            self._save_btn.hide()

    def _save_summary(self):
        if not self._current_note:
            return
        text = self._summary_edit.toPlainText()
        self._note_manager.save_summary(self._current_note.note_id, text)
        self._summary_edit.setReadOnly(True)
        self._edit_toggle_btn.setText("编辑")
        self._save_btn.hide()
        InfoBar.success("已保存", "", duration=2000, position=InfoBarPosition.TOP, parent=self)

    # ── 复制 ──────────────────────────────────────────────────

    def _copy_transcript(self):
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(self._transcript_edit.toPlainText())
        InfoBar.success("已复制", "转录文本已复制到剪贴板", duration=2000, position=InfoBarPosition.TOP, parent=self)

    def _copy_summary(self):
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(self._summary_edit.toPlainText())
        InfoBar.success("已复制", "总结内容已复制到剪贴板", duration=2000, position=InfoBarPosition.TOP, parent=self)

    # ── 导出 ──────────────────────────────────────────────────

    def _show_export_menu(self):
        if not self._current_note:
            return
        menu = RoundMenu(parent=self)
        menu.addAction(Action(FIF.DOCUMENT, "导出为 Markdown (.md)", triggered=self._export_md))
        menu.addAction(Action(FIF.DOCUMENT, "导出为纯文本 (.txt)", triggered=self._export_txt))
        menu.addAction(Action(FIF.DOCUMENT, "导出为 Word (.docx)", triggered=self._export_docx))
        menu.exec(self._export_btn.mapToGlobal(self._export_btn.rect().bottomLeft()))

    def _export_md(self):
        self._do_export("markdown")

    def _export_txt(self):
        self._do_export("txt")

    def _export_docx(self):
        self._do_export("docx")

    def _do_export(self, fmt: str):
        if not self._current_note:
            return
        try:
            if fmt == "markdown":
                dest = self._exporter.to_markdown(self._current_note.note_id)
            elif fmt == "txt":
                dest = self._exporter.to_txt(self._current_note.note_id)
            else:
                dest = self._exporter.to_docx(self._current_note.note_id)

            InfoBar.success(
                "导出成功",
                f"文件已保存至：{dest}",
                duration=4000,
                position=InfoBarPosition.TOP,
                parent=self,
            )
        except Exception as e:
            InfoBar.error("导出失败", str(e), duration=5000, position=InfoBarPosition.TOP, parent=self)

    def _open_note_folder(self):
        if not self._current_note:
            return
        folder = Path(cfg.notes_dir.value) / self._current_note.note_id
        if folder.exists():
            from app.core.utils.platform_utils import open_folder
            open_folder(str(folder))
