from PyQt5.QtCore import QObject, pyqtSignal


class SignalBus(QObject):
    # 转录进度 (note_id, progress 0-100, status_text)
    transcribe_progress = pyqtSignal(str, int, str)
    # 总结进度 (note_id, progress 0-100, status_text)
    summary_progress = pyqtSignal(str, int, str)

    # 笔记处理完成 (note_id)
    note_ready = pyqtSignal(str)
    # 任务失败 (note_id, error_message)
    task_failed = pyqtSignal(str, str)

    # 从历史页跳转到笔记详情 (note_id)
    open_note = pyqtSignal(str)


signalBus = SignalBus()
