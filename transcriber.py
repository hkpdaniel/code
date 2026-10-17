"""음성 파일을 텍스트로 변환하는 모듈 (faster-whisper 사용, 로컬에서 동작)."""
from dataclasses import dataclass
from functools import lru_cache

from faster_whisper import WhisperModel


@dataclass
class Segment:
    start: float  # 초
    end: float
    text: str


def format_time(seconds: float) -> str:
    """초를 mm:ss (1시간 이상이면 h:mm:ss) 형식으로 바꾼다."""
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


@lru_cache(maxsize=2)
def load_model(size: str = "small") -> WhisperModel:
    # CPU에서도 돌아가도록 int8 양자화 사용. 처음 실행 시 모델을 자동으로 내려받는다.
    return WhisperModel(size, device="auto", compute_type="int8")


def transcribe(audio_path: str, size: str = "small", language: str | None = "ko", on_progress=None):
    """오디오 파일을 받아 (구간 리스트, 감지된 언어)를 돌려준다.

    on_progress(진행률 0~1) 콜백으로 진행 상황을 알려준다.
    """
    model = load_model(size)
    segments_iter, info = model.transcribe(
        audio_path,
        language=language,
        vad_filter=True,  # 무음 구간 건너뛰기
        beam_size=5,
    )
    segments = []
    for seg in segments_iter:
        segments.append(Segment(seg.start, seg.end, seg.text.strip()))
        if on_progress and info.duration:
            on_progress(min(seg.end / info.duration, 1.0))
    return segments, info.language
