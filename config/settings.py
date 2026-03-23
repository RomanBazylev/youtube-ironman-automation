import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT_DIR / "build"
TEMP_DIR = BUILD_DIR / "temp"
OUTPUT_DIR = BUILD_DIR / "output"
THUMB_DIR = BUILD_DIR / "thumb"
MUSIC_DIR = ROOT_DIR / "assets" / "music"


@dataclass
class VideoSpec:
    video_type: str
    width: int
    height: int
    fps: int
    min_duration_s: int
    max_duration_s: int
    min_words: int
    max_words: int


VIDEO_SPECS = {
    "short": VideoSpec(
        video_type="short",
        width=1080,
        height=1920,
        fps=30,
        min_duration_s=24,
        max_duration_s=45,
        min_words=65,
        max_words=80,
    ),
    "normal": VideoSpec(
        video_type="normal",
        width=1280,
        height=720,
        fps=30,
        min_duration_s=60,
        max_duration_s=180,
        min_words=120,
        max_words=250,
    ),
    "longform": VideoSpec(
        video_type="longform",
        width=1280,
        height=720,
        fps=30,
        min_duration_s=480,
        max_duration_s=720,
        min_words=1500,
        max_words=2200,
    ),
}

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-specdec")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")

YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")
YOUTUBE_REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN", "")

DEFAULT_LANGUAGE = "en"
DEFAULT_TIMEZONE = "UTC"

# Quality balance: 'fast' gives visibly better quality than 'veryfast' with +~30% encode time.
FFMPEG_PRESET = "fast"
FFMPEG_CRF = "20"
AUDIO_BITRATE = "192k"


def ensure_build_dirs() -> None:
    for d in [BUILD_DIR, TEMP_DIR, OUTPUT_DIR, THUMB_DIR]:
        d.mkdir(parents=True, exist_ok=True)
