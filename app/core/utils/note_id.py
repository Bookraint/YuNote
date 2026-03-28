"""笔记目录名（与 note_id 一致）：文件名安全 + 时间戳，避免难辨的随机 ID。"""

import datetime
import re
from pathlib import Path


def allocate_note_folder_id(notes_root: Path, source_audio_name: str) -> str:
    """
    生成笔记目录名，形如：「录音名_20260329_143052」。
    若目录已存在（同秒重复导入），自动追加 _1、_2 …
    """
    stem = Path(source_audio_name).stem
    safe = re.sub(r"[^\w\u4e00-\u9fff\-.]", "_", stem).strip("._")
    if not safe:
        safe = "note"
    if len(safe) > 80:
        safe = safe[:80]
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{safe}_{ts}"
    candidate = base
    n = 0
    while (notes_root / candidate).exists():
        n += 1
        candidate = f"{base}_{n}"
    return candidate
