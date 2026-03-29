"""
笔记的 CRUD 操作。
每条笔记对应 AppData/notes/{note_id}/ 目录：

  meta.json        — 笔记索引（标题、场景、时间、状态、模型等）；列表/打开笔记依赖此文件
  transcript.txt   — 当前转录原文（主入口）
  summary.md       — 当前 AI 总结（主入口）
  versions/        — 可选；在覆盖转录/总结前将旧文件按时间戳归档至此
  audio.wav        — 可选；需格式转换时生成的中间文件，处理完默认删除
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.entities import Note, NoteSceneEnum, TaskStatusEnum
from app.core.utils.logger import setup_logger

logger = setup_logger("note_manager")


def _serialize_note(note: Note) -> dict:
    return {
        "note_id": note.note_id,
        "title": note.title,
        "created_at": note.created_at.isoformat(),
        "updated_at": note.updated_at.isoformat(),
        "scene": note.scene.value,
        "tags": note.tags,
        "source_audio_name": note.source_audio_name,
        "duration_seconds": note.duration_seconds,
        "transcript_file": note.transcript_file,
        "summary_file": note.summary_file,
        "transcribe_model": note.transcribe_model,
        "llm_model": note.llm_model,
        "status": note.status.value,
    }


def _deserialize_note(data: dict) -> Note:
    scene_map = {s.value: s for s in NoteSceneEnum}
    status_map = {s.value: s for s in TaskStatusEnum}
    return Note(
        note_id=data["note_id"],
        title=data.get("title", ""),
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data.get("updated_at", data["created_at"])),
        scene=scene_map.get(data.get("scene", ""), NoteSceneEnum.GENERAL),
        tags=data.get("tags", []),
        source_audio_name=data.get("source_audio_name", ""),
        duration_seconds=data.get("duration_seconds", 0.0),
        transcript_file=data.get("transcript_file", "transcript.txt"),
        summary_file=data.get("summary_file", "summary.md"),
        transcribe_model=data.get("transcribe_model", ""),
        llm_model=data.get("llm_model", ""),
        status=status_map.get(data.get("status", ""), TaskStatusEnum.DONE),
    )


class NoteManager:

    def __init__(self, notes_root: Path):
        self.notes_root = notes_root
        self.notes_root.mkdir(parents=True, exist_ok=True)

    def _note_dir(self, note_id: str) -> Path:
        return self.notes_root / note_id

    def _meta_path(self, note_id: str) -> Path:
        return self._note_dir(note_id) / "meta.json"

    # ── 写入 ──────────────────────────────────────────────────

    def create(self, note: Note) -> Note:
        d = self._note_dir(note.note_id)
        d.mkdir(parents=True, exist_ok=True)
        self._write_meta(note)
        logger.info("创建笔记: %s (%s)", note.note_id, note.title)
        return note

    def update(self, note: Note) -> Note:
        note.updated_at = datetime.now()
        self._write_meta(note)
        return note

    def _archive_previous_version(self, file_path: Path, name_prefix: str) -> None:
        """若文件存在且非空，复制到 versions/{name_prefix}_YYYYMMDD_HHMMSS.ext"""
        if not file_path.exists():
            return
        if not file_path.read_text(encoding="utf-8").strip():
            return
        versions = file_path.parent / "versions"
        versions.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = versions / f"{name_prefix}_{ts}{file_path.suffix}"
        shutil.copy2(file_path, dest)
        logger.info("已归档旧版本: %s", dest)

    def save_transcript(self, note_id: str, text: str, *, archive_previous: bool = False) -> Path:
        p = self._note_dir(note_id) / "transcript.txt"
        if archive_previous:
            self._archive_previous_version(p, "transcript")
        p.write_text(text, encoding="utf-8")
        logger.info("转录文本已保存: %s", p)
        return p

    def save_summary(self, note_id: str, markdown: str, *, archive_previous: bool = False) -> Path:
        p = self._note_dir(note_id) / "summary.md"
        if archive_previous:
            self._archive_previous_version(p, "summary")
        p.write_text(markdown, encoding="utf-8")
        logger.info("总结已保存: %s", p)
        return p

    # ── 读取 ──────────────────────────────────────────────────

    def get(self, note_id: str) -> Optional[Note]:
        meta = self._meta_path(note_id)
        if not meta.exists():
            return None
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
            return _deserialize_note(data)
        except Exception as e:
            logger.error("读取笔记元数据失败 %s: %s", note_id, e)
            return None

    def get_transcript(self, note_id: str) -> str:
        p = self._note_dir(note_id) / "transcript.txt"
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def get_summary(self, note_id: str) -> str:
        p = self._note_dir(note_id) / "summary.md"
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def list_all(
        self,
        scene: Optional[NoteSceneEnum] = None,
        search_query: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> list[Note]:
        notes: list[Note] = []
        for note_dir in sorted(self.notes_root.iterdir(), reverse=True):
            if not note_dir.is_dir():
                continue
            note = self.get(note_dir.name)
            if note is None:
                continue
            if scene and note.scene != scene:
                continue
            if tags and not any(t in note.tags for t in tags):
                continue
            if search_query:
                q = search_query.lower()
                if q not in note.title.lower() and q not in note.source_audio_name.lower():
                    continue
            notes.append(note)

        notes.sort(key=lambda n: n.created_at, reverse=True)
        return notes

    # ── 删除 ──────────────────────────────────────────────────

    def delete(self, note_id: str) -> bool:
        import shutil
        d = self._note_dir(note_id)
        if d.exists():
            shutil.rmtree(d)
            logger.info("笔记已删除: %s", note_id)
            return True
        return False

    # ── 内部工具 ──────────────────────────────────────────────

    def _write_meta(self, note: Note):
        meta = self._meta_path(note.note_id)
        meta.write_text(
            json.dumps(_serialize_note(note), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
