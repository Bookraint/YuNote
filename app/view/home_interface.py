"""
转录页：音频 / 视频导入、转录与（可选）自动总结。
场景由全局「总结参数」中的默认场景决定，本页不单独选场景。
流程：导入音频 → 预处理 → 转录 → 总结 → 跳转笔记页
"""
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, pyqtSlot
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from PyQt5.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.common.config import cfg
from app.common.signal_bus import signalBus
from app.core.entities import TaskStatusEnum
from app.core.notes import NoteManager
from app.core.task_factory import TaskFactory
from app.core.utils.audio_utils import (
    SUPPORTED_EXTS,
    format_duration,
    get_duration,
    is_supported,
    prepare_audio,
)
from app.thread.summary_thread import SummaryThread
from app.thread.transcribe_thread import TranscribeThread
from app.view.fluent_setting_blocks import TranscribeSettingsBlock
from app.view.ui_helpers import status_message, warning_dialog


class DropZone(QFrame):
    """支持拖拽的文件导入区域；选中文件后切换为「已选文件」样式。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("macDropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(160)

        self._layout = QVBoxLayout(self)
        self._layout.setAlignment(Qt.AlignCenter)
        self._layout.setSpacing(12)

        self._icon_label = QLabel("🎵")
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setStyleSheet("font-size: 40px;")
        self._layout.addWidget(self._icon_label)

        self._primary_label = QLabel("拖拽音频 / 视频文件到此处，或点击选择")
        self._primary_label.setAlignment(Qt.AlignCenter)
        self._primary_label.setWordWrap(True)
        self._layout.addWidget(self._primary_label)

        self._detail_label = QLabel("支持 mp3 / wav / m4a / aac / flac / ogg / mp4 / mkv …")
        self._detail_label.setAlignment(Qt.AlignCenter)
        self._detail_label.setWordWrap(True)
        self._detail_label.setObjectName("macSecondary")
        self._layout.addWidget(self._detail_label)

    def set_empty(self) -> None:
        self.setObjectName("macDropZone")
        self._icon_label.setText("🎵")
        self._icon_label.setStyleSheet("font-size: 40px;")
        self._primary_label.setText("拖拽音频 / 视频文件到此处，或点击选择")
        self._primary_label.setObjectName("")
        self._detail_label.setText("支持 mp3 / wav / m4a / aac / flac / ogg / mp4 / mkv …")
        self._detail_label.setObjectName("macSecondary")
        self._detail_label.show()
        self._polish_state()

    def set_file(self, filename: str, duration_text: str) -> None:
        self.setObjectName("macDropZoneFilled")
        self._icon_label.setText("✓")
        self._icon_label.setStyleSheet("font-size: 34px; color: #30d158;")
        self._primary_label.setText(filename)
        self._primary_label.setObjectName("macDropZoneFileName")
        self._detail_label.setText(
            f"时长：{duration_text}  ·  点击或拖入其他文件可替换"
        )
        self._detail_label.setObjectName("macSecondary")
        self._detail_label.show()
        self._polish_state()

    def _polish_state(self) -> None:
        self.style().unpolish(self)
        self.style().polish(self)
        self._primary_label.style().unpolish(self._primary_label)
        self._primary_label.style().polish(self._primary_label)
        self._detail_label.style().unpolish(self._detail_label)
        self._detail_label.style().polish(self._detail_label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if is_supported(file_path):
                self.window().transcribeInterface._on_file_selected(file_path)
            else:
                warning_dialog(
                    self.window(),
                    "格式不支持",
                    f"不支持的文件格式，请使用：{', '.join(sorted(SUPPORTED_EXTS))}",
                )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.window().transcribeInterface._browse_file()


class HomeInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("transcribeInterface")
        self.setWindowTitle("")

        self._audio_path: str = ""
        self._note_id: str = ""
        self._transcribe_thread: QThread | None = None
        self._summary_thread: QThread | None = None
        self._note_manager = NoteManager()

        self._init_ui()

    def _on_transcribe_settings_layout(self) -> None:
        if getattr(self, "_home_scroll_inner", None) is not None:
            self._home_scroll_inner.adjustSize()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._home_scroll = QScrollArea(self)
        self._home_scroll.setObjectName("macScroll")
        self._home_scroll.setWidgetResizable(True)
        self._home_scroll.setFrameShape(QFrame.NoFrame)

        self._home_scroll_inner = QWidget()
        self._home_scroll_inner.setObjectName("macScrollInner")
        root = QVBoxLayout(self._home_scroll_inner)
        root.setContentsMargins(36, 32, 36, 32)
        root.setSpacing(24)

        title = QLabel("转录")
        title.setObjectName("macTitle")
        root.addWidget(title)

        scope_hint = QLabel("总结所用场景与模板请在「笔记 → 总结参数…」或设置中配置；此处仅负责转录与生成笔记。")
        scope_hint.setObjectName("macSecondary")
        scope_hint.setWordWrap(True)
        root.addWidget(scope_hint)

        self._drop_zone = DropZone(self)
        root.addWidget(self._drop_zone)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        self._browse_btn = QPushButton("📁  选择文件")
        self._browse_btn.clicked.connect(self._browse_file)
        self._start_btn = QPushButton("▶  开始处理")
        self._start_btn.setDefault(True)
        self._start_btn.clicked.connect(self._start_processing)
        self._start_btn.setEnabled(False)
        btn_row.addWidget(self._browse_btn)
        btn_row.addWidget(self._start_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        root.addSpacing(8)

        self._progress_card = QFrame(self)
        self._progress_card.setObjectName("macCard")
        progress_layout = QVBoxLayout(self._progress_card)
        progress_layout.setContentsMargins(20, 16, 20, 16)
        progress_layout.setSpacing(10)

        self._stage_label = QLabel("等待开始…")
        progress_layout.addWidget(self._stage_label)

        self._progress_bar = QProgressBar(self)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        progress_layout.addWidget(self._progress_bar)

        self._progress_card.hide()
        root.addWidget(self._progress_card)

        root.addSpacing(16)
        hint = QLabel("转录引擎（本次任务将使用以下配置）")
        hint.setObjectName("macSecondary")
        root.addWidget(hint)
        self._transcribe_settings = TranscribeSettingsBlock(
            self._home_scroll_inner,
            on_layout_changed=self._on_transcribe_settings_layout,
        )
        root.addWidget(self._transcribe_settings)

        root.addStretch()

        self._home_scroll.setWidget(self._home_scroll_inner)
        outer.addWidget(self._home_scroll)

    def _browse_file(self):
        exts = " ".join(f"*{e}" for e in sorted(SUPPORTED_EXTS))
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择音频 / 视频文件",
            "",
            f"音频/视频文件 ({exts});;所有文件 (*.*)",
        )
        if path:
            self._on_file_selected(path)

    def _on_file_selected(self, path: str):
        self._audio_path = path
        duration = get_duration(path)
        filename = Path(path).name
        dur_str = format_duration(duration) if duration > 0 else "未知"
        self._drop_zone.set_file(filename, dur_str)
        self._start_btn.setEnabled(True)

    def _start_processing(self):
        if not self._audio_path:
            return

        self._start_btn.setEnabled(False)
        self._browse_btn.setEnabled(False)
        self._progress_card.show()
        self._progress_bar.setValue(0)
        self._stage_label.setText("准备中…")

        scene = cfg.default_scene.value
        duration = get_duration(self._audio_path)
        note = TaskFactory.create_note(
            title=Path(self._audio_path).stem,
            scene=scene,
            source_audio_name=Path(self._audio_path).name,
            duration_seconds=duration,
        )
        self._note_manager.create(note)
        self._note_id = note.note_id

        self._stage_label.setText("音频预处理中…")
        note_dir = Path(cfg.notes_dir.value) / self._note_id
        wav_path = prepare_audio(self._audio_path, str(note_dir))
        if not wav_path:
            self._on_error("音频预处理失败，请确认文件完整且已安装 ffmpeg")
            return

        task = TaskFactory.create_transcribe_task(
            audio_path=wav_path,
            note_id=self._note_id,
            need_next_task=True,
        )
        self._transcribe_thread = TranscribeThread(task)
        self._transcribe_thread.progress.connect(self._on_transcribe_progress)
        self._transcribe_thread.finished.connect(self._on_transcribe_done)
        self._transcribe_thread.error.connect(self._on_error)
        self._transcribe_thread.start()

    @pyqtSlot(int, str)
    def _on_transcribe_progress(self, pct: int, msg: str):
        self._progress_bar.setValue(pct // 2)
        self._stage_label.setText(f"转录中…  {msg}")

    @pyqtSlot(object)
    def _on_transcribe_done(self, task):
        self._note_manager.save_transcript(
            self._note_id,
            Path(task.output_path).read_text(encoding="utf-8") if Path(task.output_path).exists() else "",
        )

        if not cfg.auto_summary.value:
            self._finish_processing()
            return

        summary_task = TaskFactory.create_summary_task(
            transcript_path=task.output_path,
            note_id=self._note_id,
            scene=cfg.default_scene.value,
        )
        self._summary_thread = SummaryThread(summary_task)
        self._summary_thread.progress.connect(self._on_summary_progress)
        self._summary_thread.finished.connect(self._on_summary_done)
        self._summary_thread.error.connect(self._on_error)
        self._summary_thread.start()

    @pyqtSlot(int, str)
    def _on_summary_progress(self, pct: int, msg: str):
        self._progress_bar.setValue(50 + pct // 2)
        self._stage_label.setText(f"生成总结…  {msg}")

    @pyqtSlot(object)
    def _on_summary_done(self, task):
        summary_text = (
            Path(task.output_summary_path).read_text(encoding="utf-8")
            if Path(task.output_summary_path).exists() else ""
        )
        self._note_manager.save_summary(self._note_id, summary_text)

        note = self._note_manager.get(self._note_id)
        if note:
            note.status = TaskStatusEnum.DONE
            note.llm_model = task.summary_config.llm_model if task.summary_config else ""
            if task.summary_config:
                note.scene = task.summary_config.scene
            self._note_manager.update(note)

        self._finish_processing()

    def _finish_processing(self):
        self._progress_bar.setValue(100)
        self._stage_label.setText("处理完成！")
        self._browse_btn.setEnabled(True)

        if not cfg.keep_work_files.value:
            wav = Path(cfg.notes_dir.value) / self._note_id / "audio.wav"
            if wav.exists():
                wav.unlink(missing_ok=True)

        status_message(self, "处理完成，正在打开笔记…", 2500)
        signalBus.note_ready.emit(self._note_id)
        self._reset_ui()

    @pyqtSlot(str)
    def _on_error(self, msg: str):
        self._progress_bar.setValue(0)
        self._stage_label.setText("处理失败")
        self._start_btn.setEnabled(bool(self._audio_path))
        self._browse_btn.setEnabled(True)

        note = self._note_manager.get(self._note_id)
        if note:
            note.status = TaskStatusEnum.FAILED
            self._note_manager.update(note)

        warning_dialog(self, "处理失败", msg)

    def _reset_ui(self):
        self._audio_path = ""
        self._note_id = ""
        self._drop_zone.set_empty()
        self._start_btn.setEnabled(False)
        self._progress_card.hide()
        self._progress_bar.setValue(0)
