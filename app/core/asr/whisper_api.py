from typing import Any, Callable, List, Optional, Union

from openai import OpenAI

from app.core.llm.client import normalize_base_url

from ..utils.logger import setup_logger
from .asr_data import ASRDataSeg
from .base import BaseASR

logger = setup_logger("whisper_api")


class WhisperAPI(BaseASR):
    """OpenAI-compatible Whisper API implementation.

    Supports any OpenAI-compatible ASR API endpoint.
    """

    def __init__(
        self,
        audio_input: Union[str, bytes],
        whisper_model: str,
        need_word_time_stamp: bool = False,
        language: str = "zh",
        prompt: str = "",
        base_url: str = "",
        api_key: str = "",
        use_cache: bool = False,
    ):
        """Initialize Whisper API.

        Args:
            audio_input: Path to audio file or raw audio bytes
            whisper_model: Model name
            need_word_time_stamp: Return word-level timestamps
            language: Language code (default: zh)
            prompt: Initial prompt for model
            base_url: API base URL
            api_key: API key
            use_cache: Enable caching
        """
        super().__init__(audio_input, use_cache)

        self.base_url = normalize_base_url(base_url)
        self.api_key = api_key.strip()

        if not self.base_url or not self.api_key:
            raise ValueError("Whisper BASE_URL and API_KEY must be set")

        self.model = whisper_model
        self.language = language
        self.prompt = prompt
        self.need_word_time_stamp = need_word_time_stamp

        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    def _run(
        self, callback: Optional[Callable[[int, str], None]] = None, **kwargs: Any
    ) -> dict:
        """Execute ASR via API."""
        return self._submit()

    def _make_segments(self, resp_data: dict) -> List[ASRDataSeg]:
        """Convert API response to segments."""
        # OpenAI SDK 在 words 为 null 时仍会在 to_dict() 里带上 "words": None；
        # 仅当存在非空列表时才走词级，否则应回退到 segments（兼容未返回词级时间戳的服务端）。
        words = resp_data.get("words")
        if self.need_word_time_stamp and isinstance(words, list) and len(words) > 0:
            return [
                ASRDataSeg(
                    text=word["word"],
                    start_time=int(float(word["start"]) * 1000),
                    end_time=int(float(word["end"]) * 1000),
                )
                for word in words
            ]
        segments = resp_data.get("segments") or []
        return [
            ASRDataSeg(
                text=seg["text"].strip(),
                start_time=int(float(seg["start"]) * 1000),
                end_time=int(float(seg["end"]) * 1000),
            )
            for seg in segments
        ]

    def _get_vad_params(self) -> dict[str, Any]:
        """从 cfg 读取 VAD 参数，值为 0 时不传（使用服务端默认）。"""
        from app.common.config import cfg  # 延迟导入，避免循环依赖
        params: dict[str, Any] = {}
        threshold = cfg.get(cfg.whisper_api_vad_threshold)
        min_silence = cfg.get(cfg.whisper_api_vad_min_silence_ms)
        speech_pad = cfg.get(cfg.whisper_api_vad_speech_pad_ms)
        if threshold:
            params["vad_threshold"] = threshold / 100.0
        if min_silence:
            params["vad_min_silence_ms"] = min_silence
        if speech_pad:
            params["vad_speech_pad_ms"] = speech_pad
        return params

    def _get_key(self) -> str:
        """Get cache key including model, language and VAD params."""
        vad = self._get_vad_params()
        vad_suffix = "-".join(f"{k}={v}" for k, v in sorted(vad.items()))
        return (
            f"{self.crc32_hex}-{self.model}-{self.language}-{self.prompt}-"
            f"{int(self.need_word_time_stamp)}-v3-{vad_suffix}"
        )

    def _submit(self) -> dict:
        """Submit audio for transcription."""
        try:
            if self.language == "zh" and not self.prompt:
                self.prompt = "你好，我们需要使用简体中文，以下是普通话的句子"

            if not self.base_url:
                raise ValueError("Whisper BASE_URL must be set")

            api_kwargs: dict[str, Any] = {
                "model": self.model,
                "response_format": "verbose_json",
                "file": ("audio.mp3", self.file_binary or b"", "audio/mp3"),
                "prompt": self.prompt,
                "timestamp_granularities": ["word", "segment"],
            }
            # 空字符串表示自动检测，不传 language 参数让 API 自行判断
            if self.language:
                api_kwargs["language"] = self.language

            vad_params = self._get_vad_params()
            if vad_params:
                api_kwargs["extra_query"] = vad_params

            completion = self.client.audio.transcriptions.create(**api_kwargs)
            if isinstance(completion, str):
                raise ValueError(
                    "WhisperAPI returned type error, please check your base URL."
                )
            return completion.to_dict()
        except Exception as e:
            logger.exception(f"WhisperAPI failed: {str(e)}")
            raise e
