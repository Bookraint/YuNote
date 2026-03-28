from app.core.asr.asr_data import ASRData
from app.core.asr.bcut import BcutASR
from app.core.asr.chunked_asr import ChunkedASR
from app.core.asr.faster_whisper import FasterWhisperASR
from app.core.asr.jianying import JianYingASR
from app.core.asr.elevenlabs import ElevenLabsASR
from app.core.asr.whisper_api import WhisperAPI
from app.core.asr.whisper_cpp import WhisperCppASR
from app.core.entities import TranscribeConfig, TranscribeModelEnum


def _chunked_kwargs_cloud(config: TranscribeConfig) -> dict:
    """云端 / 远程 API 分块参数（并发、限流、重试）。"""
    chunk_sec = max(60, config.transcribe_chunk_length_minutes * 60)
    conc = max(1, config.transcribe_max_concurrent_chunks)
    if not config.transcribe_enable_async:
        conc = 1
    return {
        "chunk_length": chunk_sec,
        "chunk_concurrency": conc,
        "enable_async": config.transcribe_enable_async,
        "max_retries": max(1, config.transcribe_chunk_max_retries),
        "rate_limit_per_minute": max(0, config.transcribe_api_rate_limit_per_minute),
        "split_threshold_minutes": config.transcribe_split_threshold_minutes,
    }


def _chunked_kwargs_local(config: TranscribeConfig) -> dict:
    """本地引擎：单块并发，不限流，其余与配置一致。"""
    kw = _chunked_kwargs_cloud(config)
    kw["chunk_concurrency"] = 1
    kw["rate_limit_per_minute"] = 0
    return kw


def transcribe(audio_path: str, config: TranscribeConfig, callback=None) -> ASRData:
    """Transcribe audio file using specified configuration.

    Args:
        audio_path: Path to audio file
        config: Transcription configuration
        callback: Progress callback function(progress: int, message: str)

    Returns:
        ASRData: Transcription result data
    """

    def _default_callback(x, y):
        pass

    if callback is None:
        callback = _default_callback

    if config.transcribe_model is None:
        raise ValueError("Transcription model not set")

    # Create ASR instance based on model type
    asr = _create_asr_instance(audio_path, config)

    # Run transcription
    asr_data = asr.run(callback=callback)

    # Optimize subtitle timing if not using word timestamps
    if not config.need_word_time_stamp:
        asr_data.optimize_timing()

    return asr_data


def _create_asr_instance(audio_path: str, config: TranscribeConfig) -> ChunkedASR:
    """Create appropriate ASR instance based on configuration.

    Args:
        audio_path: Path to audio file
        config: Transcription configuration

    Returns:
        ChunkedASR: Chunked ASR instance ready to run
    """
    model_type = config.transcribe_model

    if model_type == TranscribeModelEnum.JIANYING:
        return _create_jianying_asr(audio_path, config)

    elif model_type == TranscribeModelEnum.BIJIAN:
        return _create_bijian_asr(audio_path, config)

    elif model_type == TranscribeModelEnum.WHISPER_CPP:
        return _create_whisper_cpp_asr(audio_path, config)

    elif model_type == TranscribeModelEnum.WHISPER_API:
        return _create_whisper_api_asr(audio_path, config)

    elif model_type == TranscribeModelEnum.ELEVENLABS:
        return _create_elevenlabs_asr(audio_path, config)

    elif model_type == TranscribeModelEnum.FASTER_WHISPER:
        return _create_faster_whisper_asr(audio_path, config)

    else:
        raise ValueError(f"Invalid transcription model: {model_type}")


def _create_jianying_asr(audio_path: str, config: TranscribeConfig) -> ChunkedASR:
    """Create JianYing ASR instance with chunking support."""
    asr_kwargs = {
        "use_cache": True,
        "need_word_time_stamp": config.need_word_time_stamp,
    }
    return ChunkedASR(
        asr_class=JianYingASR,
        audio_path=audio_path,
        asr_kwargs=asr_kwargs,
        **_chunked_kwargs_cloud(config),
    )


def _create_bijian_asr(audio_path: str, config: TranscribeConfig) -> ChunkedASR:
    """Create Bijian ASR instance with chunking support."""
    asr_kwargs = {
        "use_cache": True,
        "need_word_time_stamp": config.need_word_time_stamp,
    }
    return ChunkedASR(
        asr_class=BcutASR,
        audio_path=audio_path,
        asr_kwargs=asr_kwargs,
        **_chunked_kwargs_cloud(config),
    )


def _create_whisper_cpp_asr(audio_path: str, config: TranscribeConfig) -> ChunkedASR:
    """Create WhisperCpp ASR instance with chunking support."""
    asr_kwargs = {
        "use_cache": True,
        "need_word_time_stamp": config.need_word_time_stamp,
        "language": config.transcribe_language,
        "whisper_model": config.whisper_model.value if config.whisper_model else None,
    }
    return ChunkedASR(
        asr_class=WhisperCppASR,
        audio_path=audio_path,
        asr_kwargs=asr_kwargs,
        **_chunked_kwargs_local(config),
    )


def _create_whisper_api_asr(audio_path: str, config: TranscribeConfig) -> ChunkedASR:
    """Create Whisper API ASR instance with chunking support."""
    asr_kwargs = {
        "use_cache": True,
        "need_word_time_stamp": config.need_word_time_stamp,
        "language": config.transcribe_language,
        "whisper_model": config.whisper_api_model or "whisper-1",
        "api_key": config.whisper_api_key or "",
        "base_url": config.whisper_api_base or "",
        "prompt": config.whisper_api_prompt or "",
    }
    return ChunkedASR(
        asr_class=WhisperAPI,
        audio_path=audio_path,
        asr_kwargs=asr_kwargs,
        **_chunked_kwargs_cloud(config),
    )


def _create_elevenlabs_asr(audio_path: str, config: TranscribeConfig) -> ChunkedASR:
    """Create ElevenLabs Scribe ASR instance with chunking support."""
    asr_kwargs = {
        "use_cache": True,
        "need_word_time_stamp": config.need_word_time_stamp,
        "language": config.transcribe_language,
        "model_id": config.elevenlabs_model_id or "scribe_v1",
        "diarize": config.elevenlabs_diarize,
        "tag_audio_events": config.elevenlabs_tag_audio_events,
    }
    return ChunkedASR(
        asr_class=ElevenLabsASR,
        audio_path=audio_path,
        asr_kwargs=asr_kwargs,
        **_chunked_kwargs_cloud(config),
    )


def _create_faster_whisper_asr(audio_path: str, config: TranscribeConfig) -> ChunkedASR:
    """Create FasterWhisper ASR instance with chunking support."""
    asr_kwargs = {
        "use_cache": True,
        "need_word_time_stamp": config.need_word_time_stamp,
        "faster_whisper_program": config.faster_whisper_program or "",
        "language": config.transcribe_language,
        "whisper_model": (
            config.faster_whisper_model.value if config.faster_whisper_model else "base"
        ),
        "model_dir": config.faster_whisper_model_dir or "",
        "device": config.faster_whisper_device,
        "vad_filter": config.faster_whisper_vad_filter,
        "vad_threshold": config.faster_whisper_vad_threshold,
        "vad_method": (
            config.faster_whisper_vad_method.value
            if config.faster_whisper_vad_method
            else ""
        ),
        "ff_mdx_kim2": config.faster_whisper_ff_mdx_kim2,
        "one_word": config.faster_whisper_one_word,
        "prompt": config.faster_whisper_prompt,
    }
    return ChunkedASR(
        asr_class=FasterWhisperASR,
        audio_path=audio_path,
        asr_kwargs=asr_kwargs,
        **_chunked_kwargs_local(config),
    )


if __name__ == "__main__":
    # 示例用法
    from app.core.entities import WhisperModelEnum

    # 创建配置
    config = TranscribeConfig(
        transcribe_model=TranscribeModelEnum.WHISPER_CPP,
        transcribe_language="zh",
        whisper_model=WhisperModelEnum.MEDIUM,
    )

    # 转录音频
    audio_file = "test.wav"

    def progress_callback(progress: int, message: str):
        print(f"Progress: {progress}%, Message: {message}")

    result = transcribe(audio_file, config, callback=progress_callback)
    print(result)
