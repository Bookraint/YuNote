"""
笔记详情页：左栏转录原文（富文本区分时间戳/说话人），右栏 AI 总结（Markdown 渲染 / 编辑）。
"""
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPlainTextEdit,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
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
from app.config import EXPORT_PATH, NOTES_PATH
from app.core.entities import Note
from app.core.notes import NoteExporter, NoteManager
from app.view.note_formatting import transcript_plain_to_html

# Qt 富文本子集：与左侧转录区对齐的阅读宽度感，段落两端对齐减少右侧「大块留白」
_SUMMARY_MARKDOWN_DOC_STYLE = """
    body { color: #e8edf4; }
    h1 { font-size: 1.35em; font-weight: 600; margin: 0.35em 0 0.3em 0; }
    h2 { font-size: 1.15em; font-weight: 600; margin: 0.45em 0 0.28em 0; }
    h3 { font-size: 1.05em; font-weight: 600; margin: 0.4em 0 0.25em 0; }
    p { margin: 0.32em 0; text-align: justify; }
    li { margin: 0.18em 0; text-align: justify; }
    ul, ol { margin: 0.35em 0; padding-left: 1.15em; }
    blockquote { margin: 0.4em 0 0.4em 0.6em; padding-left: 0.5em; border-left: 2px solid #4a5568; }
    code { background: rgba(255,255,255,0.06); padding: 0.1em 0.35em; border-radius: 3px; }
    pre { background: rgba(0,0,0,0.35); padding: 0.5em; border-radius: 6px; }
"""


class NoteInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("noteInterface")
        self.setWindowTitle("笔记")

        self._note_manager = NoteManager(NOTES_PATH)
        self._exporter = NoteExporter(self._note_manager, EXPORT_PATH)
        self._current_note: Note | None = None
        self._transcript_plain: str = ""
        self._summary_raw_md: str = ""

        self._init_ui()
        self._show_empty_state()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        # 顶部信息条
        top_wrap = QFrame(self)
        top_wrap.setObjectName("noteTopBar")
        top_row = QHBoxLayout(top_wrap)
        top_row.setContentsMargins(18, 14, 18, 14)
        top_row.setSpacing(16)

        self._title_label = TitleLabel("笔记详情")
        self._title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        top_row.addWidget(self._title_label)

        self._meta_label = CaptionLabel("")
        self._meta_label.setObjectName("noteMetaCaption")
        top_row.addWidget(self._meta_label)

        self._export_btn = PushButton(FIF.SAVE_AS, "导出")
        self._export_btn.clicked.connect(self._show_export_menu)
        top_row.addWidget(self._export_btn)

        self._open_folder_btn = ToolButton(FIF.FOLDER_ADD, self)
        self._open_folder_btn.setToolTip("在访达中打开笔记目录")
        self._open_folder_btn.clicked.connect(self._open_note_folder)
        top_row.addWidget(self._open_folder_btn)

        root.addWidget(top_wrap)

        # 主体：左右分栏
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)

        # 左栏：转录原文
        left_card = CardWidget()
        left_card.setObjectName("noteSideCard")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(18, 14, 18, 16)
        left_layout.setSpacing(10)

        left_header = QHBoxLayout()
        left_header.addWidget(SubtitleLabel("转录原文"))
        left_header.addStretch()
        self._copy_transcript_btn = ToolButton(FIF.COPY, left_card)
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

        # 右栏：AI 总结（浏览 Markdown / 编辑源码）
        right_card = CardWidget()
        right_card.setObjectName("noteSideCard")
        right_layout = QVBoxLayout(right_card)
        # 与左侧转录栏同一套边距，避免左右视觉不一致
        right_layout.setContentsMargins(18, 14, 18, 16)
        right_layout.setSpacing(10)

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
        self._copy_summary_btn.setToolTip("复制 Markdown 原文")
        self._copy_summary_btn.clicked.connect(self._copy_summary)
        right_header.addWidget(self._copy_summary_btn)
        right_layout.addLayout(right_header)

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
        right_layout.addWidget(self._summary_stack)
        splitter.addWidget(right_card)

        splitter.setSizes([400, 640])
        root.addWidget(splitter, stretch=1)

        # 底部
        bottom_bar = QHBoxLayout()
        self._source_label = BodyLabel("")
        self._source_label.setObjectName("noteFootnote")
        bottom_bar.addWidget(self._source_label)
        bottom_bar.addStretch()
        self._model_label = BodyLabel("")
        self._model_label.setObjectName("noteFootnote")
        bottom_bar.addWidget(self._model_label)
        root.addLayout(bottom_bar)

        self._apply_styles()

    def _apply_styles(self):
        """与默认 Fluent 区分的局部配色与圆角（深色主题下可读）。"""
        self.setStyleSheet(
            """
            #noteTopBar {
                background-color: rgba(40, 210, 160, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 12px;
            }
            #noteSideCard {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 14px;
            }
            #noteTranscriptView {
                background-color: rgba(0, 0, 0, 0.18);
                border: none;
                border-radius: 10px;
                padding: 6px 10px;
                font-size: 14px;
            }
            #noteSummaryView {
                background-color: rgba(0, 0, 0, 0.18);
                border: none;
                border-radius: 10px;
                padding: 6px 10px;
                font-size: 14px;
                line-height: 1.65;
            }
            #noteSummaryEditor {
                background-color: rgba(0, 0, 0, 0.22);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 8px 10px;
                font-size: 13px;
                font-family: Consolas, "SF Mono", "Menlo", monospace;
            }
            #noteFootnote {
                color: rgba(255, 255, 255, 0.45);
                font-size: 12px;
            }
            #noteMetaCaption {
                color: rgba(255, 255, 255, 0.55);
            }
            """
        )

    def _set_summary_markdown(self, md: str) -> None:
        self._summary_raw_md = md
        self._summary_browser.setMarkdown(md)
        doc = self._summary_browser.document()
        doc.setDocumentMargin(14)
        doc.setDefaultStyleSheet(_SUMMARY_MARKDOWN_DOC_STYLE)

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

    def _show_empty_state(self):
        self._title_label.setText("笔记详情")
        self._meta_label.setText("")
        self._transcript_plain = ""
        self._summary_raw_md = ""
        self._transcript_view.setHtml(transcript_plain_to_html(""))
        self._set_summary_markdown("")
        self._summary_editor.clear()
        self._summary_stack.setCurrentIndex(0)
        self._source_label.setText("")
        self._model_label.setText("")

    # ── 编辑总结 ──────────────────────────────────────────────

    def _toggle_edit(self):
        if self._summary_stack.currentIndex() == 0:
            self._summary_editor.setPlainText(self._summary_raw_md)
            self._summary_stack.setCurrentIndex(1)
            self._edit_toggle_btn.setText("取消")
            self._save_btn.show()
        else:
            if self._current_note:
                original = self._note_manager.get_summary(self._current_note.note_id)
                self._summary_editor.setPlainText(original)
                self._set_summary_markdown(original)
            self._summary_stack.setCurrentIndex(0)
            self._edit_toggle_btn.setText("编辑")
            self._save_btn.hide()

    def _save_summary(self):
        if not self._current_note:
            return
        text = self._summary_editor.toPlainText()
        self._note_manager.save_summary(self._current_note.note_id, text)
        self._set_summary_markdown(text)
        self._summary_stack.setCurrentIndex(0)
        self._edit_toggle_btn.setText("编辑")
        self._save_btn.hide()
        InfoBar.success("已保存", "", duration=2000, position=InfoBarPosition.TOP, parent=self)

    # ── 复制 ──────────────────────────────────────────────────

    def _copy_transcript(self):
        from PyQt5.QtWidgets import QApplication

        QApplication.clipboard().setText(self._transcript_plain)
        InfoBar.success("已复制", "转录文本已复制到剪贴板", duration=2000, position=InfoBarPosition.TOP, parent=self)

    def _copy_summary(self):
        from PyQt5.QtWidgets import QApplication

        if self._summary_stack.currentIndex() == 1:
            QApplication.clipboard().setText(self._summary_editor.toPlainText())
        else:
            QApplication.clipboard().setText(self._summary_raw_md)
        InfoBar.success("已复制", "总结 Markdown 已复制到剪贴板", duration=2000, position=InfoBarPosition.TOP, parent=self)

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
