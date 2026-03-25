import datetime
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

from app.core.entities import SummaryTask
from app.core.summary import Summarizer
from app.core.utils.logger import setup_logger

logger = setup_logger("summary_thread")


class SummaryThread(QThread):
    finished = pyqtSignal(SummaryTask)
    progress = pyqtSignal(int, str)    # (percent, status_text)
    error = pyqtSignal(str)

    def __init__(self, task: SummaryTask):
        super().__init__()
        self.task = task

    def run(self):
        try:
            self.task.started_at = datetime.datetime.now()
            logger.info(self.task.summary_config.print_config())

            transcript_path = Path(self.task.transcript_path)
            if not transcript_path.exists():
                raise FileNotFoundError(f"转录文件不存在: {transcript_path}")

            transcript = transcript_path.read_text(encoding="utf-8").strip()
            if not transcript:
                raise ValueError("转录文本为空，无法生成总结")

            output_path = Path(self.task.output_summary_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            summarizer = Summarizer(self.task.summary_config)
            summary = summarizer.summarize(
                transcript,
                progress_callback=self._progress_callback,
            )

            output_path.write_text(summary, encoding="utf-8")
            self.task.completed_at = datetime.datetime.now()
            self.finished.emit(self.task)

        except Exception as e:
            logger.exception("总结失败: %s", e)
            self.error.emit(str(e))
            self.progress.emit(100, f"总结失败: {e}")

    def _progress_callback(self, value: int, message: str):
        self.progress.emit(value, message)
