"""
主页：音频文件导入 + 处理进度展示
流程：导入音频 → 音频预处理 → 转录 → 总结 → 跳转笔记页
"""
import shutil
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, pyqtSlot
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
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
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    SubtitleLabel,
    TitleLabel,
    FluentIcon as FIF,
)

from app.common.config import cfg
from app.common.signal_bus import signalBus
from app.config import NOTES_PATH, WORK_PATH
from app.core.entities import NoteSceneEnum, TaskStatusEnum
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


class DropZone(CardWidget):
    """支持拖拽的文件导入区域。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(160)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        icon_label = QLabel("🎵")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 40px;")
        layout.addWidget(icon_label)

        hint = BodyLabel("拖拽音频 / 视频文件到此处，或点击选择")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        fmt = BodyLabel("支持 mp3 / wav / m4a / aac / flac / ogg / mp4 / mkv …")
        fmt.setAlignment(Qt.AlignCenter)
        fmt.setObjectName("hintSecondary")
        layout.addWidget(fmt)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if is_supported(file_path):
                self.window().homeInterface._on_file_selected(file_path)
            else:
                InfoBar.warning(
                    "格式不支持",
                    f"不支持的文件格式，请使用：{', '.join(sorted(SUPPORTED_EXTS))}",
                    duration=4000,
                    position=InfoBarPosition.TOP,
                    parent=self.window(),
                )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.window().homeInterface._browse_file()


class HomeInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("homeInterface")
        self.setWindowTitle("")

        self._audio_path: str = ""
        self._note_id: str = ""
        self._transcribe_thread: QThread | None = None
        self._summary_thread: QThread | None = None
        self._note_manager = NoteManager(NOTES_PATH)

        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 32, 36, 32)
        root.setSpacing(24)

        # 标题
        title = TitleLabel("新建笔记")
        root.addWidget(title)

        # 场景选择行
        scene_row = QHBoxLayout()
        scene_row.setSpacing(12)
        scene_label = BodyLabel("场景：")
        scene_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._scene_combo = ComboBox()
        for scene in NoteSceneEnum:
            self._scene_combo.addItem(scene.value, userData=scene)
        # 设置默认值
        default_scene = cfg.default_scene.value
        idx = next(
            (i for i in range(self._scene_combo.count())
             if self._scene_combo.itemData(i) == default_scene), 0
        )
        self._scene_combo.setCurrentIndex(idx)
        scene_row.addWidget(scene_label)
        scene_row.addWidget(self._scene_combo)
        scene_row.addStretch()
        root.addLayout(scene_row)

        # 拖拽区
        self._drop_zone = DropZone(self)
        root.addWidget(self._drop_zone)

        # 已选文件信息
        self._file_info_label = BodyLabel("")
        self._file_info_label.setObjectName("fileInfoLabel")
        self._file_info_label.hide()
        root.addWidget(self._file_info_label)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        self._browse_btn = PushButton(FIF.FOLDER, "选择文件")
        self._browse_btn.clicked.connect(self._browse_file)
        self._start_btn = PrimaryPushButton(FIF.PLAY, "开始处理")
        self._start_btn.clicked.connect(self._start_processing)
        self._start_btn.setEnabled(False)
        btn_row.addWidget(self._browse_btn)
        btn_row.addWidget(self._start_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # 分隔
        root.addSpacing(8)

        # 进度区
        self._progress_card = CardWidget(self)
        progress_layout = QVBoxLayout(self._progress_card)
        progress_layout.setContentsMargins(20, 16, 20, 16)
        progress_layout.setSpacing(10)

        self._stage_label = BodyLabel("等待开始…")
        progress_layout.addWidget(self._stage_label)

        self._progress_bar = ProgressBar(self)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        progress_layout.addWidget(self._progress_bar)

        self._progress_card.hide()
        root.addWidget(self._progress_card)

        root.addStretch()

    # ── 文件选择 ──────────────────────────────────────────────

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
        self._file_info_label.setText(f"已选择：{filename}   时长：{dur_str}")
        self._file_info_label.show()
        self._start_btn.setEnabled(True)

    # ── 处理流程 ──────────────────────────────────────────────

    def _start_processing(self):
        if not self._audio_path:
            return

        self._start_btn.setEnabled(False)
        self._browse_btn.setEnabled(False)
        self._progress_card.show()
        self._progress_bar.setValue(0)
        self._stage_label.setText("准备中…")

        # 创建笔记
        scene = self._scene_combo.currentData()
        duration = get_duration(self._audio_path)
        note = TaskFactory.create_note(
            title=Path(self._audio_path).stem,
            scene=scene,
            source_audio_name=Path(self._audio_path).name,
            duration_seconds=duration,
        )
        self._note_manager.create(note)
        self._note_id = note.note_id

        # 预处理音频
        self._stage_label.setText("音频预处理中…")
        wav_path = prepare_audio(self._audio_path, str(WORK_PATH), self._note_id)
        if not wav_path:
            self._on_error("音频预处理失败，请确认文件完整且已安装 ffmpeg")
            return

        # 启动转录
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
        # 转录阶段占总进度 0~50%
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

        # 启动总结
        scene = self._scene_combo.currentData()
        summary_task = TaskFactory.create_summary_task(
            transcript_path=task.output_path,
            note_id=self._note_id,
            scene=scene,
        )
        self._summary_thread = SummaryThread(summary_task)
        self._summary_thread.progress.connect(self._on_summary_progress)
        self._summary_thread.finished.connect(self._on_summary_done)
        self._summary_thread.error.connect(self._on_error)
        self._summary_thread.start()

    @pyqtSlot(int, str)
    def _on_summary_progress(self, pct: int, msg: str):
        # 总结阶段占总进度 50~100%
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
            self._note_manager.update(note)

        self._finish_processing()

    def _finish_processing(self):
        self._progress_bar.setValue(100)
        self._stage_label.setText("处理完成！")
        self._browse_btn.setEnabled(True)

        # 清理中间文件
        if not cfg.keep_work_files.value:
            work_note_dir = Path(WORK_PATH) / self._note_id
            if work_note_dir.exists():
                shutil.rmtree(work_note_dir, ignore_errors=True)

        InfoBar.success(
            "处理完成",
            "笔记已生成，正在跳转…",
            duration=2000,
            position=InfoBarPosition.TOP,
            parent=self,
        )
        signalBus.note_ready.emit(self._note_id)
        self._reset_ui()

    @pyqtSlot(str)
    def _on_error(self, msg: str):
        self._progress_bar.setValue(0)
        self._stage_label.setText(f"处理失败")
        self._start_btn.setEnabled(bool(self._audio_path))
        self._browse_btn.setEnabled(True)

        note = self._note_manager.get(self._note_id)
        if note:
            note.status = TaskStatusEnum.FAILED
            self._note_manager.update(note)

        InfoBar.error(
            "处理失败",
            msg,
            duration=6000,
            position=InfoBarPosition.TOP,
            parent=self,
        )

    def _reset_ui(self):
        self._audio_path = ""
        self._note_id = ""
        self._file_info_label.hide()
        self._start_btn.setEnabled(False)
        self._progress_card.hide()
        self._progress_bar.setValue(0)
