"""
笔记详情页：左栏转录原文（富文本区分时间戳/说话人），右栏 AI 总结（Markdown 渲染 / 编辑）。
总结参数在弹窗中编辑；支持重新总结（结果写入笔记目录）。
"""
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, pyqtSlot
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.common.config import cfg
from app.components.SummarySettingsDialog import SummarySettingsDialog
from app.config import NOTES_PATH
from app.core.entities import Note
from app.core.notes import NoteManager
from app.core.task_factory import TaskFactory
from app.thread.summary_thread import SummaryThread
from app.view.note_formatting import transcript_plain_to_html
from app.view.ui_helpers import info_dialog, status_message, warning_dialog

# 深色内容区下的 Markdown 文档样式
_SUMMARY_MARKDOWN_DOC_STYLE = """
    body { color: #e8edf4; }
    h1 { font-size: 1.35em; font-weight: 600; margin: 0.35em 0 0.3em 0; }
    h2 { font-size: 1.15em; font-weight: 600; margin: 0.45em 0 0.28em 0; }
    h3 { font-size: 1.05em; font-weight: 600; margin: 0.4em 0 0.25em 0; }
    p { margin: 0.32em 0; text-align: justify; }
    li { margin: 0.18em 0; text-align: justify; }
    ul, ol { margin: 0.35em 0; padding-left: 1.15em; }
    blockquote { margin: 0.4em 0 0.4em 0.6em; padding-left: 0.5em; border-left: 2px solid #636366; }
    code { background: rgba(255,255,255,0.08); padding: 0.1em 0.35em; border-radius: 3px; }
    pre { background: rgba(0,0,0,0.45); padding: 0.5em; border-radius: 6px; }
"""


class NoteInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("noteInterface")
        self.setWindowTitle("笔记")

        self._note_manager = NoteManager(NOTES_PATH)
        self._current_note: Note | None = None
        self._transcript_plain: str = ""
        self._summary_raw_md: str = ""
        self._summary_thread: QThread | None = None

        self._init_ui()
        self._show_empty_state()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        top_wrap = QFrame(self)
        top_wrap.setObjectName("noteTopBar")
        top_row = QHBoxLayout(top_wrap)
        top_row.setContentsMargins(18, 14, 18, 14)
        top_row.setSpacing(16)

        self._title_label = QLabel("笔记详情")
        self._title_label.setObjectName("macTitle")
        self._title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        top_row.addWidget(self._title_label)

        self._meta_label = QLabel("")
        self._meta_label.setObjectName("macSecondary")
        top_row.addWidget(self._meta_label)

        self._open_folder_btn = QToolButton(self)
        self._open_folder_btn.setText("📂")
        self._open_folder_btn.setToolTip("在访达中打开笔记目录")
        self._open_folder_btn.clicked.connect(self._open_note_folder)
        top_row.addWidget(self._open_folder_btn)

        root.addWidget(top_wrap)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(5)

        left_card = QFrame()
        left_card.setObjectName("noteSideCard")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(18, 14, 18, 16)
        left_layout.setSpacing(10)

        left_header = QHBoxLayout()
        _lt = QLabel("转录原文")
        _lt.setObjectName("macSection")
        left_header.addWidget(_lt)
        left_header.addStretch()
        self._copy_transcript_btn = QToolButton(left_card)
        self._copy_transcript_btn.setText("📋")
        self._copy_transcript_btn.setToolTip("复制全文（纯文本）")
        self._copy_transcript_btn.clicked.connect(self._copy_transcript)
        left_header.addWidget(self._copy_transcript_btn)
        left_layout.addLayout(left_header)

        self._transcript_view = QTextBrowser()
        self._transcript_view.setObjectName("noteTranscriptView")
        self._transcript_view.setReadOnly(True)
        self._transcript_view.setOpenExternalLinks(False)
        self._transcript_view.setPlaceholderText("转录文本将显示在这里…")
        self._transcript_view.document().setDocumentMargin(14)
        left_layout.addWidget(self._transcript_view)
        splitter.addWidget(left_card)

        right_card = QFrame()
        right_card.setObjectName("noteSideCard")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(18, 14, 18, 16)
        right_layout.setSpacing(10)

        right_header = QHBoxLayout()
        _rs = QLabel("AI 总结")
        _rs.setObjectName("macSection")
        right_header.addWidget(_rs)
        right_header.addStretch()
        self._summary_params_btn = QPushButton("总结参数…")
        self._summary_params_btn.setToolTip("调整模板、分块、并发等与总结相关的选项")
        self._summary_params_btn.clicked.connect(self._open_summary_settings)
        right_header.addWidget(self._summary_params_btn)

        self._resummarize_btn = QPushButton("重新总结")
        self._resummarize_btn.setToolTip(
            "成功后笔记覆盖原 summary.md"
            "旧版 summary.md 会先归档到 versions/ 再写入。"
        )
        self._resummarize_btn.clicked.connect(self._resummarize)
        right_header.addWidget(self._resummarize_btn)

        self._edit_toggle_btn = QPushButton("编辑")
        self._edit_toggle_btn.clicked.connect(self._toggle_edit)
        right_header.addWidget(self._edit_toggle_btn)
        self._save_btn = QPushButton("保存")
        self._save_btn.setDefault(True)
        self._save_btn.clicked.connect(self._save_summary)
        self._save_btn.hide()
        right_header.addWidget(self._save_btn)
        self._copy_summary_btn = QToolButton(right_card)
        self._copy_summary_btn.setText("📋")
        self._copy_summary_btn.setToolTip("复制 Markdown 原文")
        self._copy_summary_btn.clicked.connect(self._copy_summary)
        right_header.addWidget(self._copy_summary_btn)
        right_layout.addLayout(right_header)

        self._summary_progress_wrap = QFrame()
        self._summary_progress_wrap.setObjectName("noteSummaryProgressWrap")
        _pr = QVBoxLayout(self._summary_progress_wrap)
        _pr.setContentsMargins(0, 0, 0, 0)
        _pr.setSpacing(6)
        self._summary_progress_label = QLabel("")
        self._summary_progress_label.setObjectName("macSecondary")
        self._summary_progress_label.setWordWrap(True)
        _pr.addWidget(self._summary_progress_label)
        self._summary_progress_bar = QProgressBar()
        self._summary_progress_bar.setRange(0, 100)
        self._summary_progress_bar.setTextVisible(True)
        _pr.addWidget(self._summary_progress_bar)
        self._summary_progress_wrap.hide()
        right_layout.addWidget(self._summary_progress_wrap)

        self._summary_stack = QStackedWidget()
        self._summary_browser = QTextBrowser()
        self._summary_browser.setObjectName("noteSummaryView")
        self._summary_browser.setReadOnly(True)
        self._summary_browser.setOpenExternalLinks(True)
        self._summary_browser.document().setDocumentMargin(14)
        self._summary_editor = QPlainTextEdit()
        self._summary_editor.setObjectName("noteSummaryEditor")
        self._summary_editor.setPlaceholderText("在此编辑 Markdown…")
        self._summary_stack.addWidget(self._summary_browser)
        self._summary_stack.addWidget(self._summary_editor)

        right_layout.addWidget(self._summary_stack, stretch=1)
        splitter.addWidget(right_card)

        splitter.setSizes([400, 640])
        root.addWidget(splitter, stretch=1)

        bottom_bar = QHBoxLayout()
        self._source_label = QLabel("")
        self._source_label.setObjectName("macSecondary")
        bottom_bar.addWidget(self._source_label)
        bottom_bar.addStretch()
        self._model_label = QLabel("")
        self._model_label.setObjectName("macSecondary")
        bottom_bar.addWidget(self._model_label)
        root.addLayout(bottom_bar)

        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet(
            """
            #noteInterface {
                background-color: #1c1c1e;
            }
            QLabel#macSection {
                color: #d1d1d6;
                font-size: 13px;
                font-weight: 600;
            }
            #noteTopBar {
                background-color: rgba(10, 132, 255, 0.15);
                border: 1px solid #48484a;
                border-radius: 10px;
            }
            #noteSideCard {
                background-color: #2c2c2e;
                border: 1px solid #48484a;
                border-radius: 10px;
            }
            #noteTranscriptView {
                background-color: #1c1c1e;
                border: 1px solid #3a3a3c;
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 14px;
                color: #e8edf4;
            }
            #noteSummaryView {
                background-color: #1c1c1e;
                border: 1px solid #3a3a3c;
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 14px;
                line-height: 1.65;
                color: #e8edf4;
            }
            #noteSummaryEditor {
                background-color: #1c1c1e;
                border: 1px solid #48484a;
                border-radius: 8px;
                padding: 8px 10px;
                font-size: 13px;
                color: #e8edf4;
                font-family: Menlo, "SF Mono", Consolas, monospace;
            }
            #noteSummaryProgressWrap QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #3a3a3c;
                height: 10px;
            }
            #noteSummaryProgressWrap QProgressBar::chunk {
                background-color: #0a84ff;
                border-radius: 4px;
            }
            """
        )

    def _set_summary_markdown(self, md: str) -> None:
        self._summary_raw_md = md
        self._summary_browser.setMarkdown(md)
        doc = self._summary_browser.document()
        doc.setDocumentMargin(14)
        doc.setDefaultStyleSheet(_SUMMARY_MARKDOWN_DOC_STYLE)

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
        self._transcript_plain = transcript
        self._transcript_view.setHtml(transcript_plain_to_html(transcript))

        summary = self._note_manager.get_summary(note_id)
        self._set_summary_markdown(summary)
        self._summary_editor.setPlainText(summary)
        self._summary_stack.setCurrentIndex(0)
        self._summary_editor.setReadOnly(True)
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
        self._update_chrome_state()

    def _show_empty_state(self):
        self._title_label.setText("笔记详情")
        self._meta_label.setText("")
        self._transcript_plain = ""
        self._summary_raw_md = ""
        self._transcript_view.setHtml(transcript_plain_to_html(""))
        self._set_summary_markdown("")
        self._summary_editor.clear()
        self._summary_editor.setReadOnly(True)
        self._summary_stack.setCurrentIndex(0)
        self._source_label.setText("")
        self._model_label.setText("")
        self._update_chrome_state()

    def _update_chrome_state(self) -> None:
        has_note = self._current_note is not None
        busy = self._summary_thread is not None
        self._open_folder_btn.setEnabled(has_note and not busy)
        # 重新总结期间会禁用编辑；结束后必须在此恢复，否则会一直灰掉
        self._edit_toggle_btn.setEnabled(has_note and not busy)
        transcript_ok = False
        if has_note and self._current_note is not None:
            transcript_ok = (
                Path(cfg.notes_dir.value) / self._current_note.note_id / "transcript.txt"
            ).exists()
        self._resummarize_btn.setEnabled(has_note and transcript_ok and not busy)
        self._summary_params_btn.setEnabled(not busy)

    def _open_summary_settings(self) -> None:
        dlg = SummarySettingsDialog(self.window())
        dlg.exec_()

    def _resummarize(self) -> None:
        if not self._current_note or self._summary_thread is not None:
            return
        tpath = Path(cfg.notes_dir.value) / self._current_note.note_id / "transcript.txt"
        if not tpath.exists():
            warning_dialog(self, "无法重新总结", "未找到转录文件 transcript.txt，请先完成转录。")
            return
        self._resummarize_btn.setEnabled(False)
        self._edit_toggle_btn.setEnabled(False)
        self._summary_params_btn.setEnabled(False)
        # 与弹窗「默认场景」一致：重新总结用当前 cfg，不用笔记 meta 里创建时的 scene
        task = TaskFactory.create_summary_task(
            str(tpath),
            self._current_note.note_id,
            scene=cfg.default_scene.value,
        )
        self._summary_thread = SummaryThread(task)
        self._summary_thread.finished.connect(self._on_resummarize_done)
        self._summary_thread.error.connect(self._on_resummarize_error)
        self._summary_thread.progress.connect(self._on_resummarize_progress)
        self._summary_thread.start()
        self._summary_progress_wrap.show()
        self._summary_progress_bar.setValue(0)
        self._summary_progress_label.setText("正在生成总结…")
        status_message(self, "开始重新总结…", 2000)

    @pyqtSlot(object)
    def _on_resummarize_done(self, task) -> None:
        try:
            self._summary_progress_wrap.hide()
            out = Path(task.output_summary_path)
            summary_text = out.read_text(encoding="utf-8") if out.exists() else ""
            if not self._current_note:
                return
            nid = self._current_note.note_id
            saved_path = self._note_manager.save_summary(
                nid, summary_text, archive_previous=True
            )
            note = self._note_manager.get(nid)
            if note:
                note.llm_model = task.summary_config.llm_model if task.summary_config else ""
                if task.summary_config:
                    note.scene = task.summary_config.scene
                self._note_manager.update(note)
                self._current_note = note
                self._meta_label.setText(
                    f"{note.scene.value}  ·  {note.updated_at.strftime('%Y-%m-%d %H:%M')}"
                )
            self._summary_raw_md = summary_text
            self._set_summary_markdown(summary_text)
            self._summary_editor.setPlainText(summary_text)
            self._summary_editor.setReadOnly(True)
            self._summary_stack.setCurrentIndex(0)
            self._edit_toggle_btn.setText("编辑")
            self._save_btn.hide()
            if note:
                self._model_label.setText(
                    f"转录：{note.transcribe_model or '-'}   LLM：{note.llm_model or '-'}"
                )
            info_dialog(
                self,
                "重新总结完成",
                f"总结已保存到：\n{saved_path.resolve()}",
            )
        finally:
            self._summary_thread = None
            self._update_chrome_state()

    @pyqtSlot(str)
    def _on_resummarize_error(self, msg: str) -> None:
        try:
            self._summary_progress_wrap.hide()
            warning_dialog(self, "重新总结失败", msg)
        finally:
            self._summary_thread = None
            self._update_chrome_state()

    @pyqtSlot(int, str)
    def _on_resummarize_progress(self, pct: int, msg: str) -> None:
        self._summary_progress_bar.setValue(max(0, min(100, pct)))
        self._summary_progress_label.setText(msg or "处理中…")
        status_message(self, f"总结中 {pct}%  {msg}", 5000)

    def _toggle_edit(self):
        if self._summary_stack.currentIndex() == 0:
            self._summary_editor.setPlainText(self._summary_raw_md)
            self._summary_editor.setReadOnly(False)
            self._summary_stack.setCurrentIndex(1)
            self._edit_toggle_btn.setText("取消")
            self._save_btn.show()
            self._summary_editor.setFocus(Qt.OtherFocusReason)
        else:
            if self._current_note:
                original = self._note_manager.get_summary(self._current_note.note_id)
                self._summary_editor.setPlainText(original)
                self._set_summary_markdown(original)
            self._summary_editor.setReadOnly(True)
            self._summary_stack.setCurrentIndex(0)
            self._edit_toggle_btn.setText("编辑")
            self._save_btn.hide()

    def _save_summary(self):
        if not self._current_note:
            return
        text = self._summary_editor.toPlainText()
        saved_path = self._note_manager.save_summary(self._current_note.note_id, text)
        self._set_summary_markdown(text)
        self._summary_editor.setReadOnly(True)
        self._summary_stack.setCurrentIndex(0)
        self._edit_toggle_btn.setText("编辑")
        self._save_btn.hide()
        info_dialog(self, "已保存", f"总结已保存到：\n{saved_path.resolve()}")

    def _copy_transcript(self):
        QApplication.clipboard().setText(self._transcript_plain)
        status_message(self, "转录文本已复制到剪贴板", 2000)

    def _copy_summary(self):
        if self._summary_stack.currentIndex() == 1:
            QApplication.clipboard().setText(self._summary_editor.toPlainText())
        else:
            QApplication.clipboard().setText(self._summary_raw_md)
        status_message(self, "总结 Markdown 已复制到剪贴板", 2000)

    def _open_note_folder(self):
        if not self._current_note:
            return
        folder = Path(cfg.notes_dir.value) / self._current_note.note_id
        if folder.exists():
            from app.core.utils.platform_utils import open_folder

            open_folder(str(folder))
