import datetime
from pathlib import Path
from typing import Optional

from app.common.config import cfg
from app.core.utils.note_id import allocate_note_folder_id
from app.config import MODEL_PATH, NOTES_PATH, PROMPTS_PATH
from app.core.entities import (
    LANGUAGES,
    FasterWhisperModelEnum,
    LLMServiceEnum,
    NoteSceneEnum,
    Note,
    SummaryConfig,
    SummaryTask,
    TranscribeConfig,
    TranscribeModelEnum,
    TranscribeOutputFormatEnum,
    TranscribeTask,
)


class TaskFactory:

    @staticmethod
    def _get_note_dir(note_id: str) -> Path:
        return Path(cfg.notes_dir.value) / note_id

    @staticmethod
    def _get_llm_config() -> tuple[str, str, str]:
        """根据当前 LLM 服务返回 (base_url, api_key, model)"""
        svc = cfg.llm_service.value
        if svc == LLMServiceEnum.OPENAI:
            return cfg.openai_api_base.value, cfg.openai_api_key.value, cfg.openai_model.value
        elif svc == LLMServiceEnum.SILICON_CLOUD:
            return cfg.silicon_cloud_api_base.value, cfg.silicon_cloud_api_key.value, cfg.silicon_cloud_model.value
        elif svc == LLMServiceEnum.DEEPSEEK:
            return cfg.deepseek_api_base.value, cfg.deepseek_api_key.value, cfg.deepseek_model.value
        elif svc == LLMServiceEnum.OLLAMA:
            return cfg.ollama_api_base.value, cfg.ollama_api_key.value, cfg.ollama_model.value
        elif svc == LLMServiceEnum.LM_STUDIO:
            return cfg.lm_studio_api_base.value, cfg.lm_studio_api_key.value, cfg.lm_studio_model.value
        elif svc == LLMServiceEnum.GEMINI:
            return cfg.gemini_api_base.value, cfg.gemini_api_key.value, cfg.gemini_model.value
        elif svc == LLMServiceEnum.CHATGLM:
            return cfg.chatglm_api_base.value, cfg.chatglm_api_key.value, cfg.chatglm_model.value
        return "", "", ""

    @staticmethod
    def create_transcribe_task(
        audio_path: str,
        note_id: str,
        need_next_task: bool = True,
    ) -> TranscribeTask:
        note_dir = TaskFactory._get_note_dir(note_id)
        note_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(note_dir / "transcript.txt")

        config = TranscribeConfig(
            transcribe_model=cfg.transcribe_model.value,
            transcribe_language=LANGUAGES.get(cfg.transcribe_language.value.value, ""),
            need_word_time_stamp=False,
            output_format=TranscribeOutputFormatEnum.TXT,
            # Whisper Cpp
            whisper_model=cfg.whisper_model.value,
            # Whisper API
            whisper_api_key=cfg.whisper_api_key.value,
            whisper_api_base=cfg.whisper_api_base.value,
            whisper_api_model=cfg.whisper_api_model.value,
            whisper_api_prompt=cfg.whisper_api_prompt.value,
            # ElevenLabs
            elevenlabs_model_id=cfg.elevenlabs_model_id.value,
            elevenlabs_diarize=cfg.elevenlabs_diarize.value,
            elevenlabs_tag_audio_events=cfg.elevenlabs_tag_audio_events.value,
            # FasterWhisper
            faster_whisper_program="faster-whisper-xxl.exe",
            faster_whisper_model=cfg.faster_whisper_model.value,
            faster_whisper_model_dir=str(MODEL_PATH),
            faster_whisper_device=cfg.faster_whisper_device.value,
            faster_whisper_vad_filter=cfg.faster_whisper_vad_filter.value,
            faster_whisper_vad_threshold=cfg.faster_whisper_vad_threshold.value,
            faster_whisper_vad_method=cfg.faster_whisper_vad_method.value,
            faster_whisper_ff_mdx_kim2=False,
            faster_whisper_one_word=cfg.faster_whisper_one_word.value,
            faster_whisper_prompt=cfg.faster_whisper_prompt.value,
            transcribe_enable_async=cfg.transcribe_enable_async.value,
            transcribe_max_concurrent_chunks=cfg.transcribe_max_concurrent_chunks.value,
            transcribe_chunk_max_retries=cfg.transcribe_chunk_max_retries.value,
            transcribe_api_rate_limit_per_minute=cfg.transcribe_api_rate_limit_per_minute.value,
            transcribe_split_threshold_minutes=cfg.transcribe_split_threshold_minutes.value,
            transcribe_chunk_length_minutes=cfg.transcribe_chunk_length_minutes.value,
        )

        return TranscribeTask(
            queued_at=datetime.datetime.now(),
            file_path=audio_path,
            output_path=output_path,
            need_next_task=need_next_task,
            note_id=note_id,
            transcribe_config=config,
        )

    @staticmethod
    def create_summary_task(
        transcript_path: str,
        note_id: str,
        scene: Optional[NoteSceneEnum] = None,
    ) -> SummaryTask:
        note_dir = TaskFactory._get_note_dir(note_id)
        output_path = str(note_dir / "summary.md")
        base_url, api_key, model = TaskFactory._get_llm_config()
        actual_scene = scene or cfg.default_scene.value

        config = SummaryConfig(
            scene=actual_scene,
            llm_service=cfg.llm_service.value,
            llm_base_url=base_url,
            llm_api_key=api_key,
            llm_model=model,
            custom_prompt=cfg.summary_custom_prompt.value,
            prompt_template_meeting=cfg.summary_prompt_template_meeting.value,
            prompt_template_lecture=cfg.summary_prompt_template_lecture.value,
            prompt_template_interview=cfg.summary_prompt_template_interview.value,
            prompt_template_general=cfg.summary_prompt_template_general.value,
            chunk_size=cfg.summary_chunk_size.value,
            map_concurrency=cfg.summary_map_concurrency.value,
            map_rpm=cfg.summary_map_rpm.value,
            prompts_path=str(PROMPTS_PATH),
        )

        return SummaryTask(
            queued_at=datetime.datetime.now(),
            transcript_path=transcript_path,
            output_summary_path=output_path,
            note_id=note_id,
            summary_config=config,
        )

    @staticmethod
    def create_note(
        title: str,
        scene: NoteSceneEnum,
        source_audio_name: str,
        duration_seconds: float = 0.0,
    ) -> Note:
        """创建 Note 元数据对象（不含持久化，由 NoteManager 负责写盘）"""
        base_url, api_key, model = TaskFactory._get_llm_config()
        transcribe_model = cfg.transcribe_model.value
        notes_root = Path(cfg.notes_dir.value)
        note_id = allocate_note_folder_id(notes_root, source_audio_name)
        return Note(
            note_id=note_id,
            title=title,
            scene=scene,
            source_audio_name=source_audio_name,
            duration_seconds=duration_seconds,
            transcribe_model=transcribe_model.value if transcribe_model else "",
            llm_model=model,
        )
