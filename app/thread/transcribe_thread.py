import datetime
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

from app.core.asr import transcribe
from app.core.entities import TranscribeTask
from app.core.utils.logger import setup_logger

logger = setup_logger("transcribe_thread")


class TranscribeThread(QThread):
    finished = pyqtSignal(TranscribeTask)
    progress = pyqtSignal(int, str)    # (percent, status_text)
    error = pyqtSignal(str)

    def __init__(self, task: TranscribeTask):
        super().__init__()
        self.task = task

    def run(self):
        try:
            self.task.started_at = datetime.datetime.now()
            logger.info(self.task.transcribe_config.print_config())

            audio_path = Path(self.task.file_path)
            if not audio_path.exists():
                raise FileNotFoundError(f"音频文件不存在: {audio_path}")

            if not self.task.transcribe_config:
                raise ValueError("转录配置为空")

            output_path = Path(self.task.output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            self.progress.emit(5, "语音转录中…")
            logger.info("开始转录: %s", audio_path)

            asr_data = transcribe(
                str(audio_path),
                self.task.transcribe_config,
                callback=self._progress_callback,
            )

            # 保存为纯文本（去除时间戳，只保留文字）
            text = asr_data.to_txt() if hasattr(asr_data, "to_txt") else str(asr_data)
            output_path.write_text(text, encoding="utf-8")
            # 同时保存一份 SRT 备用
            srt_path = output_path.with_suffix(".srt")
            asr_data.save(str(srt_path))

            self.task.completed_at = datetime.datetime.now()
            self.progress.emit(100, "转录完成")
            self.finished.emit(self.task)

        except Exception as e:
            logger.exception("转录失败: %s", e)
            self.error.emit(str(e))
            self.progress.emit(100, f"转录失败: {e}")

    def _progress_callback(self, value: int, message: str):
        pct = min(5 + int(value * 0.95), 99)
        self.progress.emit(pct, message)
